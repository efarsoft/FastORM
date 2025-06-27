"""
FastORM序列化器模块

提供各种类型的序列化器：
- 基础序列化器接口
- 模型序列化器
- 字段序列化器
- 关系序列化器
- 序列化器注册表和链
"""

import json
from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel

from .exceptions import FieldSerializationError
from .exceptions import RelationSerializationError
from .exceptions import SerializationError


class BaseSerializer(ABC):
    """序列化器基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    def serialize(self, value: Any, context: Any = None) -> Any:
        """序列化值"""
        pass

    @abstractmethod
    def can_serialize(self, value: Any) -> bool:
        """检查是否可以序列化此值"""
        pass

    def __call__(self, value: Any, context: Any = None) -> Any:
        """使序列化器可调用"""
        return self.serialize(value, context)


class FieldSerializer(BaseSerializer):
    """字段序列化器"""

    def __init__(
        self,
        name: str,
        field_type: type,
        serializer_func: Callable[[Any, Any], Any],
        description: str = "",
    ):
        super().__init__(name, description)
        self.field_type = field_type
        self.serializer_func = serializer_func

    def serialize(self, value: Any, context: Any = None) -> Any:
        """序列化字段值"""
        if value is None:
            return None

        try:
            return self.serializer_func(value, context)
        except Exception as e:
            raise FieldSerializationError(
                f"字段序列化失败: {e!s}",
                field=self.name,
                value=value,
                serializer_name=self.name,
                field_type=self.field_type.__name__,
            )

    def can_serialize(self, value: Any) -> bool:
        """检查是否可以序列化此值"""
        return isinstance(value, self.field_type)


class ModelSerializer(BaseSerializer):
    """模型序列化器"""

    def __init__(
        self,
        name: str,
        model_type: type,
        field_serializers: dict[str, FieldSerializer] | None = None,
        exclude_fields: list[str] | None = None,
        include_fields: list[str] | None = None,
        description: str = "",
    ):
        super().__init__(name, description)
        self.model_type = model_type
        self.field_serializers = field_serializers or {}
        self.exclude_fields = set(exclude_fields or [])
        self.include_fields = set(include_fields or []) if include_fields else None

    def serialize(self, model: Any, context: Any = None) -> dict[str, Any]:
        """序列化模型"""
        if model is None:
            return None

        if not isinstance(model, self.model_type):
            raise SerializationError(
                f"类型不匹配: 期望 {self.model_type.__name__}, "
                f"实际 {type(model).__name__}"
            )

        result = {}

        # 获取字段列表
        fields = self._get_model_fields(model)

        for field_name in fields:
            # 检查包含/排除规则
            if self.include_fields and field_name not in self.include_fields:
                continue
            if field_name in self.exclude_fields:
                continue

            try:
                value = getattr(model, field_name)

                # 使用自定义字段序列化器
                if field_name in self.field_serializers:
                    serialized_value = self.field_serializers[field_name].serialize(
                        value, context
                    )
                else:
                    # 使用默认序列化
                    serialized_value = self._serialize_field_value(
                        value, field_name, context
                    )

                result[field_name] = serialized_value

            except Exception as e:
                if isinstance(e, FieldSerializationError):
                    raise
                else:
                    raise FieldSerializationError(
                        f"字段序列化失败: {e!s}",
                        field=field_name,
                        value=getattr(model, field_name, None),
                        serializer_name=self.name,
                    )

        return result

    def can_serialize(self, value: Any) -> bool:
        """检查是否可以序列化此值"""
        return isinstance(value, self.model_type)

    def _get_model_fields(self, model: Any) -> list[str]:
        """获取模型字段列表"""

        # Pydantic模型
        if isinstance(model, BaseModel):
            return list(model.model_fields.keys())

        # SQLAlchemy模型
        if hasattr(model, "__table__"):
            return [column.name for column in model.__table__.columns]

        # 其他类型，使用__dict__
        return [key for key in model.__dict__.keys() if not key.startswith("_")]

    def _serialize_field_value(
        self, value: Any, field_name: str, context: Any = None
    ) -> Any:
        """序列化字段值"""

        if value is None:
            return None

        # 基础类型
        if isinstance(value, (str, int, float, bool)):
            return value

        # 日期时间类型
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat()

        # 数值类型
        if isinstance(value, Decimal):
            return float(value)

        # 枚举类型
        if isinstance(value, Enum):
            return value.value

        # 容器类型
        if isinstance(value, (list, tuple, set)):
            return [
                self._serialize_field_value(item, field_name, context) for item in value
            ]

        if isinstance(value, dict):
            return {
                k: self._serialize_field_value(v, field_name, context)
                for k, v in value.items()
            }

        # 模型类型（递归序列化）
        if hasattr(value, "__dict__"):
            # 避免无限递归，简单转换为字符串
            return str(value)

        return str(value)


class RelationSerializer(BaseSerializer):
    """关系序列化器"""

    def __init__(
        self,
        name: str,
        relation_type: str,  # "one_to_one", "one_to_many", "many_to_one", "many_to_many"
        target_serializer: BaseSerializer | None = None,
        lazy: bool = True,
        max_depth: int = 2,
        description: str = "",
    ):
        super().__init__(name, description)
        self.relation_type = relation_type
        self.target_serializer = target_serializer
        self.lazy = lazy
        self.max_depth = max_depth

    def serialize(self, value: Any, context: Any = None) -> Any:
        """序列化关系值"""
        if value is None:
            return None

        try:
            # 检查深度限制
            current_depth = getattr(context, "current_depth", 0) if context else 0
            if current_depth >= self.max_depth:
                return self._serialize_reference(value)

            # 根据关系类型序列化
            if self.relation_type in ["one_to_one", "many_to_one"]:
                return self._serialize_single_relation(value, context)
            elif self.relation_type in ["one_to_many", "many_to_many"]:
                return self._serialize_multiple_relation(value, context)
            else:
                raise RelationSerializationError(
                    f"不支持的关系类型: {self.relation_type}",
                    relation_name=self.name,
                    relation_type=self.relation_type,
                )

        except Exception as e:
            if isinstance(e, RelationSerializationError):
                raise
            else:
                raise RelationSerializationError(
                    f"关系序列化失败: {e!s}",
                    relation_name=self.name,
                    relation_type=self.relation_type,
                )

    def can_serialize(self, value: Any) -> bool:
        """检查是否可以序列化此值"""
        if value is None:
            return True

        if self.relation_type in ["one_to_one", "many_to_one"]:
            return hasattr(value, "__dict__")
        elif self.relation_type in ["one_to_many", "many_to_many"]:
            return hasattr(value, "__iter__")

        return False

    def _serialize_single_relation(
        self, value: Any, context: Any = None
    ) -> dict[str, Any]:
        """序列化单个关系对象"""

        if self.target_serializer:
            return self.target_serializer.serialize(value, context)
        else:
            # 使用默认序列化
            return self._default_serialize_object(value, context)

    def _serialize_multiple_relation(
        self, values: Any, context: Any = None
    ) -> list[dict[str, Any]]:
        """序列化多个关系对象"""

        result = []
        for value in values:
            if self.target_serializer:
                serialized = self.target_serializer.serialize(value, context)
            else:
                serialized = self._default_serialize_object(value, context)
            result.append(serialized)

        return result

    def _serialize_reference(self, value: Any) -> dict[str, Any]:
        """序列化为引用（避免深度过深）"""

        # 尝试获取ID或主键
        if hasattr(value, "id"):
            return {"__ref__": value.id, "__type__": type(value).__name__}
        elif hasattr(value, "__table__"):
            # SQLAlchemy模型，获取主键
            pk_columns = value.__table__.primary_key.columns
            if pk_columns:
                pk_name = list(pk_columns)[0].name
                pk_value = getattr(value, pk_name)
                return {"__ref__": pk_value, "__type__": type(value).__name__}

        return {"__ref__": id(value), "__type__": type(value).__name__}

    def _default_serialize_object(
        self, obj: Any, context: Any = None
    ) -> dict[str, Any]:
        """默认对象序列化"""

        if hasattr(obj, "__dict__"):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith("_"):
                    if isinstance(value, (str, int, float, bool, type(None))):
                        result[key] = value
                    else:
                        result[key] = str(value)
            return result
        else:
            return {"__value__": str(obj), "__type__": type(obj).__name__}


class SerializerRegistry:
    """序列化器注册表"""

    def __init__(self):
        self._field_serializers: dict[str, FieldSerializer] = {}
        self._model_serializers: dict[type, ModelSerializer] = {}
        self._relation_serializers: dict[str, RelationSerializer] = {}
        self._type_serializers: dict[type, BaseSerializer] = {}

    def register_field_serializer(
        self, field_name: str, serializer: FieldSerializer
    ) -> None:
        """注册字段序列化器"""
        self._field_serializers[field_name] = serializer

    def register_model_serializer(
        self, model_type: type, serializer: ModelSerializer
    ) -> None:
        """注册模型序列化器"""
        self._model_serializers[model_type] = serializer

    def register_relation_serializer(
        self, relation_name: str, serializer: RelationSerializer
    ) -> None:
        """注册关系序列化器"""
        self._relation_serializers[relation_name] = serializer

    def register_type_serializer(
        self, value_type: type, serializer: BaseSerializer
    ) -> None:
        """注册类型序列化器"""
        self._type_serializers[value_type] = serializer

    def get_field_serializer(self, field_name: str) -> FieldSerializer | None:
        """获取字段序列化器"""
        return self._field_serializers.get(field_name)

    def get_model_serializer(self, model_type: type) -> ModelSerializer | None:
        """获取模型序列化器"""
        return self._model_serializers.get(model_type)

    def get_relation_serializer(self, relation_name: str) -> RelationSerializer | None:
        """获取关系序列化器"""
        return self._relation_serializers.get(relation_name)

    def get_type_serializer(self, value_type: type) -> BaseSerializer | None:
        """获取类型序列化器"""
        return self._type_serializers.get(value_type)

    def list_serializers(self) -> dict[str, int]:
        """列出所有序列化器数量"""
        return {
            "field_serializers": len(self._field_serializers),
            "model_serializers": len(self._model_serializers),
            "relation_serializers": len(self._relation_serializers),
            "type_serializers": len(self._type_serializers),
        }

    def clear(self) -> None:
        """清空所有序列化器"""
        self._field_serializers.clear()
        self._model_serializers.clear()
        self._relation_serializers.clear()
        self._type_serializers.clear()


class SerializerChain:
    """序列化器链"""

    def __init__(self, name: str = "default"):
        self.name = name
        self._serializers: list[BaseSerializer] = []

    def add_serializer(self, serializer: BaseSerializer) -> "SerializerChain":
        """添加序列化器"""
        self._serializers.append(serializer)
        return self

    def serialize(self, value: Any, context: Any = None) -> Any:
        """使用序列化器链序列化值"""

        for serializer in self._serializers:
            if serializer.can_serialize(value):
                return serializer.serialize(value, context)

        # 如果没有序列化器可以处理，返回字符串表示
        return str(value) if value is not None else None

    def can_serialize(self, value: Any) -> bool:
        """检查是否可以序列化此值"""
        return any(serializer.can_serialize(value) for serializer in self._serializers)

    def get_serializers(self) -> list[BaseSerializer]:
        """获取序列化器列表"""
        return self._serializers.copy()

    def clear(self) -> None:
        """清空序列化器链"""
        self._serializers.clear()


# 内置序列化器工厂函数


def create_datetime_serializer(
    format_string: str = "%Y-%m-%d %H:%M:%S",
) -> FieldSerializer:
    """创建日期时间序列化器"""

    def serialize_datetime(value: datetime, context: Any = None) -> str:
        return value.strftime(format_string)

    return FieldSerializer(
        name="datetime_serializer",
        field_type=datetime,
        serializer_func=serialize_datetime,
        description=f"日期时间序列化器 (格式: {format_string})",
    )


def create_decimal_serializer(precision: int = 2) -> FieldSerializer:
    """创建小数序列化器"""

    def serialize_decimal(value: Decimal, context: Any = None) -> float:
        return round(float(value), precision)

    return FieldSerializer(
        name="decimal_serializer",
        field_type=Decimal,
        serializer_func=serialize_decimal,
        description=f"小数序列化器 (精度: {precision})",
    )


def create_enum_serializer() -> FieldSerializer:
    """创建枚举序列化器"""

    def serialize_enum(value: Enum, context: Any = None) -> Any:
        return value.value

    return FieldSerializer(
        name="enum_serializer",
        field_type=Enum,
        serializer_func=serialize_enum,
        description="枚举序列化器",
    )


def create_json_serializer() -> FieldSerializer:
    """创建JSON序列化器"""

    def serialize_json(value: Any, context: Any = None) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    return FieldSerializer(
        name="json_serializer",
        field_type=object,
        serializer_func=serialize_json,
        description="JSON序列化器",
    )
