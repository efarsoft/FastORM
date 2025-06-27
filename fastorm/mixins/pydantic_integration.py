"""
Pydantic V2 深度集成模块

提供SQLAlchemy模型与Pydantic V2的无缝集成，包括：
- 自动Schema生成
- 双向转换
- 验证功能
- 序列化功能
"""

import json
from datetime import date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import create_model
from sqlalchemy import inspect


class PydanticIntegrationMixin:
    """Pydantic V2 集成Mixin类

    为SQLAlchemy模型提供与Pydantic V2的深度集成功能
    """

    __hidden_fields__: list[str] | None = None
    __pydantic_schema__: type[BaseModel] | None = None

    @classmethod
    def _get_sqlalchemy_fields(cls) -> dict[str, Any]:
        """获取SQLAlchemy字段信息"""
        mapper = inspect(cls)
        fields = {}

        for column in mapper.columns:
            field_name = column.name
            python_type = column.type.python_type

            # 处理可选字段
            is_nullable = column.nullable
            if is_nullable and python_type is not type(None):
                python_type = Optional[python_type]

            # 设置默认值 - 修复ID字段问题
            default = None
            if field_name == "id":
                # ID字段默认为可选（创建时为None）
                default = None
                if not is_nullable:
                    python_type = Optional[python_type]
            elif column.default is not None:
                if hasattr(column.default, "arg"):
                    default = column.default.arg
                else:
                    default = ...
            elif not is_nullable:
                default = ...

            fields[field_name] = (python_type, default)

        return fields

    @classmethod
    def _create_pydantic_schema(
        cls,
        for_create: bool = False,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ) -> type[BaseModel]:
        """创建Pydantic Schema"""

        fields = cls._get_sqlalchemy_fields()

        # 处理隐藏字段
        hidden_fields = cls.__hidden_fields__ or []

        # 过滤字段
        filtered_fields = {}
        for field_name, field_info in fields.items():
            # 跳过隐藏字段
            if field_name in hidden_fields:
                continue

            # 包含字段过滤
            if include_fields and field_name not in include_fields:
                continue

            # 排除字段过滤
            if exclude_fields and field_name in exclude_fields:
                continue

            # 创建时排除自动生成字段
            if for_create:
                if field_name in ["id", "created_at", "updated_at"]:
                    continue

            filtered_fields[field_name] = field_info

        # 创建动态Schema
        schema_name = f"{cls.__name__}{'Create' if for_create else ''}Schema"

        return create_model(
            schema_name,
            __config__=ConfigDict(
                from_attributes=True,
                arbitrary_types_allowed=True,
                json_encoders={
                    datetime: lambda v: v.isoformat(),
                    date: lambda v: v.isoformat(),
                    Decimal: lambda v: float(v),
                    Enum: lambda v: v.value,
                },
            ),
            **filtered_fields,
        )

    @classmethod
    def get_pydantic_schema(
        cls,
        for_create: bool = False,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ) -> type[BaseModel]:
        """获取Pydantic Schema

        Args:
            for_create: 是否为创建模式（排除ID等自动字段）
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
        """
        cache_key = (
            for_create,
            tuple(include_fields) if include_fields else None,
            tuple(exclude_fields) if exclude_fields else None,
        )

        if not hasattr(cls, "_schema_cache"):
            cls._schema_cache = {}

        if cache_key not in cls._schema_cache:
            cls._schema_cache[cache_key] = cls._create_pydantic_schema(
                for_create=for_create,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
            )

        return cls._schema_cache[cache_key]

    def to_pydantic(
        self,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
    ) -> BaseModel:
        """转换为Pydantic模型实例

        Args:
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
        """
        schema = self.__class__.get_pydantic_schema(
            include_fields=include_fields, exclude_fields=exclude_fields
        )
        return schema.model_validate(self)

    @classmethod
    def from_pydantic(
        cls, pydantic_obj: BaseModel, validate: bool = True
    ) -> "PydanticIntegrationMixin":
        """从Pydantic模型创建SQLAlchemy实例

        Args:
            pydantic_obj: Pydantic模型实例
            validate: 是否进行验证
        """
        if validate:
            # 使用Pydantic验证
            pydantic_obj.model_validate(pydantic_obj.model_dump())

        # 转换为SQLAlchemy实例
        data = pydantic_obj.model_dump(exclude_unset=True)
        return cls(**data)

    @classmethod
    def create_from_pydantic(
        cls, pydantic_obj: BaseModel, validate: bool = True
    ) -> "PydanticIntegrationMixin":
        """创建模式：从Pydantic模型创建SQLAlchemy实例

        Args:
            pydantic_obj: Pydantic模型实例
            validate: 是否进行验证
        """
        if validate:
            # 使用创建Schema验证
            create_schema = cls.get_pydantic_schema(for_create=True)
            validated_data = create_schema.model_validate(pydantic_obj.model_dump())
            data = validated_data.model_dump(exclude_unset=True)
        else:
            data = pydantic_obj.model_dump(exclude_unset=True)

        return cls(**data)

    def validate_with_pydantic(self, raise_error: bool = True) -> bool | dict[str, Any]:
        """使用Pydantic验证当前实例

        Args:
            raise_error: 是否抛出验证错误

        Returns:
            验证通过返回True，失败时根据raise_error参数决定抛错或返回错误信息
        """
        try:
            schema = self.__class__.get_pydantic_schema()
            schema.model_validate(self)
            return True
        except Exception as e:
            if raise_error:
                raise e
            return {"valid": False, "errors": str(e)}

    def to_pydantic_dict(
        self,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """转换为字典（通过Pydantic，支持字段过滤和隐藏）

        Args:
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
            exclude_none: 是否排除None值
        """
        # 组合隐藏字段和排除字段
        hidden_fields = self.__class__.__hidden_fields__ or []
        all_exclude = list(hidden_fields)
        if exclude_fields:
            all_exclude.extend(exclude_fields)

        pydantic_obj = self.to_pydantic(
            include_fields=include_fields, exclude_fields=all_exclude
        )
        return pydantic_obj.model_dump(exclude_none=exclude_none)

    def to_json(
        self,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        exclude_none: bool = False,
        indent: int | None = None,
    ) -> str:
        """转换为JSON字符串

        Args:
            include_fields: 包含的字段列表
            exclude_fields: 排除的字段列表
            exclude_none: 是否排除None值
            indent: JSON缩进
        """
        data = self.to_pydantic_dict(
            include_fields=include_fields,
            exclude_fields=exclude_fields,
            exclude_none=exclude_none,
        )

        # 自定义JSON编码器处理特殊类型
        def json_encoder(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            raise TypeError(
                f"Object of type {obj.__class__.__name__} is not JSON serializable"
            )

        return json.dumps(data, indent=indent, ensure_ascii=False, default=json_encoder)

    @classmethod
    def from_json(
        cls, json_str: str, validate: bool = True, for_create: bool = False
    ) -> "PydanticIntegrationMixin":
        """从JSON字符串创建实例

        Args:
            json_str: JSON字符串
            validate: 是否验证
            for_create: 是否为创建模式
        """
        data = json.loads(json_str)

        if validate:
            schema = cls.get_pydantic_schema(for_create=for_create)
            validated_obj = schema.model_validate(data)
            return cls.from_pydantic(validated_obj, validate=False)
        else:
            return cls(**data)

    @classmethod
    def create_from_dict(
        cls, data: dict[str, Any], validate: bool = True
    ) -> "PydanticIntegrationMixin":
        """创建模式：从字典创建实例

        Args:
            data: 数据字典
            validate: 是否验证
        """
        if validate:
            schema = cls.get_pydantic_schema(for_create=True)
            validated_obj = schema.model_validate(data)
            return cls.from_pydantic(validated_obj, validate=False)
        else:
            return cls(**data)

    def update_from_pydantic(
        self, pydantic_obj: BaseModel, validate: bool = True, exclude_unset: bool = True
    ) -> None:
        """使用Pydantic对象更新当前实例

        Args:
            pydantic_obj: Pydantic模型实例
            validate: 是否验证
            exclude_unset: 是否排除未设置的字段
        """
        if validate:
            pydantic_obj.model_validate(pydantic_obj.model_dump())

        data = pydantic_obj.model_dump(exclude_unset=exclude_unset)
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_validation_errors(self) -> list[dict[str, Any]] | None:
        """获取验证错误（不抛出异常）

        Returns:
            验证错误列表，无错误返回None
        """
        try:
            self.validate_with_pydantic(raise_error=True)
            return None
        except Exception as e:
            if hasattr(e, "errors"):
                return e.errors()
            return [{"error": str(e)}]

    @classmethod
    def get_pydantic_json_schema(cls, for_create: bool = False) -> dict[str, Any]:
        """获取Pydantic JSON Schema

        Args:
            for_create: 是否为创建模式
        """
        schema = cls.get_pydantic_schema(for_create=for_create)
        return schema.model_json_schema()
