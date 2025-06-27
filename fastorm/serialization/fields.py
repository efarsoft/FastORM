"""
FastORM序列化字段处理模块

提供字段级别的序列化配置和处理：
- 字段配置管理
- 字段映射和别名
- 字段转换器
- 字段映射注册表
"""

import re
from typing import Any, Dict, List, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import FieldSerializationError


class FieldType(Enum):
    """字段类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    DECIMAL = "decimal"
    JSON = "json"
    ENUM = "enum"
    LIST = "list"
    DICT = "dict"
    RELATION = "relation"
    CUSTOM = "custom"


@dataclass
class FieldConfig:
    """字段配置"""
    
    # 基础配置
    name: str
    alias: Optional[str] = None
    field_type: FieldType = FieldType.STRING
    required: bool = True
    default: Any = None
    
    # 序列化配置
    serialize: bool = True
    exclude_none: bool = True
    exclude_empty: bool = False
    
    # 格式化配置
    format_string: Optional[str] = None
    precision: Optional[int] = None
    
    # 验证配置
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    
    # 转换配置
    transformer: Optional[Callable[[Any], Any]] = None
    case_transform: Optional[str] = None  # "lower", "upper", "title", "camel", "snake"
    
    # 关系配置
    relation_type: Optional[str] = None
    target_model: Optional[str] = None
    lazy_loading: bool = True
    
    # 描述
    description: str = ""
    
    def copy(self, **kwargs) -> 'FieldConfig':
        """创建配置副本"""
        values = {
            'name': self.name,
            'alias': self.alias,
            'field_type': self.field_type,
            'required': self.required,
            'default': self.default,
            'serialize': self.serialize,
            'exclude_none': self.exclude_none,
            'exclude_empty': self.exclude_empty,
            'format_string': self.format_string,
            'precision': self.precision,
            'min_length': self.min_length,
            'max_length': self.max_length,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'pattern': self.pattern,
            'transformer': self.transformer,
            'case_transform': self.case_transform,
            'relation_type': self.relation_type,
            'target_model': self.target_model,
            'lazy_loading': self.lazy_loading,
            'description': self.description
        }
        values.update(kwargs)
        return FieldConfig(**values)


@dataclass
class SerializationField:
    """序列化字段"""
    
    config: FieldConfig
    source_name: str
    target_name: str
    transformer: Optional[Callable[[Any], Any]] = None
    
    def serialize_value(self, value: Any, context: Any = None) -> Any:
        """序列化字段值"""
        
        # 检查是否应该序列化
        if not self.config.serialize:
            return None
        
        # 处理None值
        if value is None:
            if self.config.exclude_none:
                return None
            return self.config.default
        
        # 处理空值
        if self.config.exclude_empty and self._is_empty_value(value):
            return None
        
        try:
            # 应用转换器
            if self.transformer:
                value = self.transformer(value)
            elif self.config.transformer:
                value = self.config.transformer(value)
            
            # 应用格式化
            value = self._apply_formatting(value)
            
            # 应用大小写转换
            value = self._apply_case_transform(value)
            
            return value
            
        except Exception as e:
            raise FieldSerializationError(
                f"字段值序列化失败: {str(e)}",
                field=self.source_name,
                value=value,
                field_type=self.config.field_type.value
            )
    
    def _is_empty_value(self, value: Any) -> bool:
        """检查是否为空值"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
            return True
        return False
    
    def _apply_formatting(self, value: Any) -> Any:
        """应用格式化"""
        
        if self.config.format_string and value is not None:
            if self.config.field_type == FieldType.DATETIME:
                if hasattr(value, 'strftime'):
                    return value.strftime(self.config.format_string)
            elif self.config.field_type == FieldType.FLOAT:
                if isinstance(value, (int, float)):
                    return self.config.format_string.format(value)
            elif self.config.field_type == FieldType.DECIMAL:
                if self.config.precision is not None:
                    return round(float(value), self.config.precision)
        
        return value
    
    def _apply_case_transform(self, value: Any) -> Any:
        """应用大小写转换"""
        
        if self.config.case_transform and isinstance(value, str):
            if self.config.case_transform == "lower":
                return value.lower()
            elif self.config.case_transform == "upper":
                return value.upper()
            elif self.config.case_transform == "title":
                return value.title()
            elif self.config.case_transform == "camel":
                return self._to_camel_case(value)
            elif self.config.case_transform == "snake":
                return self._to_snake_case(value)
        
        return value
    
    def _to_camel_case(self, value: str) -> str:
        """转换为驼峰命名"""
        components = value.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    def _to_snake_case(self, value: str) -> str:
        """转换为蛇形命名"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class FieldMapping:
    """字段映射"""
    
    def __init__(self, source_field: str, target_field: str):
        self.source_field = source_field
        self.target_field = target_field
        self.transformers: List[Callable[[Any], Any]] = []
        self.conditions: List[Callable[[Any], bool]] = []
    
    def add_transformer(
        self,
        transformer: Callable[[Any], Any]
    ) -> 'FieldMapping':
        """添加值转换器"""
        self.transformers.append(transformer)
        return self
    
    def add_condition(
        self,
        condition: Callable[[Any], bool]
    ) -> 'FieldMapping':
        """添加条件"""
        self.conditions.append(condition)
        return self
    
    def should_apply(self, value: Any) -> bool:
        """检查是否应该应用映射"""
        return all(condition(value) for condition in self.conditions)
    
    def transform_value(self, value: Any) -> Any:
        """转换值"""
        for transformer in self.transformers:
            value = transformer(value)
        return value
    
    def apply(self, value: Any) -> Any:
        """应用映射"""
        if self.should_apply(value):
            return self.transform_value(value)
        return value


class FieldTransformer:
    """字段转换器"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.transformers: Dict[str, Callable[[Any], Any]] = {}
    
    def register_transformer(
        self,
        field_name: str,
        transformer: Callable[[Any], Any]
    ) -> None:
        """注册字段转换器"""
        self.transformers[field_name] = transformer
    
    def transform_field(self, field_name: str, value: Any) -> Any:
        """转换字段值"""
        if field_name in self.transformers:
            return self.transformers[field_name](value)
        return value
    
    def transform_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换字典数据"""
        result = {}
        for key, value in data.items():
            result[key] = self.transform_field(key, value)
        return result


class FieldMappingRegistry:
    """字段映射注册表"""
    
    def __init__(self):
        self._field_configs: Dict[str, FieldConfig] = {}
        self._field_mappings: Dict[str, FieldMapping] = {}
        self._transformers: Dict[str, FieldTransformer] = {}
        self._aliases: Dict[str, str] = {}
    
    def register_field_config(
        self,
        field_name: str,
        config: FieldConfig
    ) -> None:
        """注册字段配置"""
        self._field_configs[field_name] = config
        
        # 注册别名
        if config.alias:
            self._aliases[config.alias] = field_name
    
    def register_field_mapping(
        self,
        mapping_name: str,
        mapping: FieldMapping
    ) -> None:
        """注册字段映射"""
        self._field_mappings[mapping_name] = mapping
    
    def register_transformer(
        self,
        transformer_name: str,
        transformer: FieldTransformer
    ) -> None:
        """注册转换器"""
        self._transformers[transformer_name] = transformer
    
    def get_field_config(self, field_name: str) -> Optional[FieldConfig]:
        """获取字段配置"""
        return self._field_configs.get(field_name)
    
    def get_field_mapping(self, mapping_name: str) -> Optional[FieldMapping]:
        """获取字段映射"""
        return self._field_mappings.get(mapping_name)
    
    def get_transformer(self, transformer_name: str) -> Optional[FieldTransformer]:
        """获取转换器"""
        return self._transformers.get(transformer_name)
    
    def resolve_field_name(self, field_name: str) -> str:
        """解析字段名（处理别名）"""
        return self._aliases.get(field_name, field_name)
    
    def create_serialization_field(
        self,
        field_name: str,
        config: Optional[FieldConfig] = None
    ) -> SerializationField:
        """创建序列化字段"""
        
        effective_config = config or self.get_field_config(field_name)
        if not effective_config:
            effective_config = FieldConfig(name=field_name)
        
        target_name = effective_config.alias or field_name
        
        return SerializationField(
            config=effective_config,
            source_name=field_name,
            target_name=target_name
        )
    
    def list_field_configs(self) -> List[str]:
        """列出所有字段配置"""
        return list(self._field_configs.keys())
    
    def list_mappings(self) -> List[str]:
        """列出所有映射"""
        return list(self._field_mappings.keys())
    
    def list_transformers(self) -> List[str]:
        """列出所有转换器"""
        return list(self._transformers.keys())
    
    def clear(self) -> None:
        """清空注册表"""
        self._field_configs.clear()
        self._field_mappings.clear()
        self._transformers.clear()
        self._aliases.clear()


# 内置转换器工厂函数

def create_string_transformer(
    strip: bool = True,
    lower: bool = False,
    upper: bool = False
) -> Callable[[Any], str]:
    """创建字符串转换器"""
    
    def transform(value: Any) -> str:
        result = str(value) if value is not None else ""
        if strip:
            result = result.strip()
        if lower:
            result = result.lower()
        elif upper:
            result = result.upper()
        return result
    
    return transform


def create_number_transformer(
    precision: Optional[int] = None,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None
) -> Callable[[Any], Union[int, float]]:
    """创建数值转换器"""
    
    def transform(value: Any) -> Union[int, float]:
        if value is None:
            return 0
        
        # 转换为数值
        if isinstance(value, str):
            try:
                if '.' in value or 'e' in value.lower():
                    result = float(value)
                else:
                    result = int(value)
            except ValueError:
                result = 0
        else:
            result = float(value) if isinstance(value, (int, float)) else 0
        
        # 应用精度
        if precision is not None and isinstance(result, float):
            result = round(result, precision)
        
        # 应用范围限制
        if min_value is not None:
            result = max(result, min_value)
        if max_value is not None:
            result = min(result, max_value)
        
        return result
    
    return transform


def create_list_transformer(
    item_transformer: Optional[Callable[[Any], Any]] = None,
    max_items: Optional[int] = None
) -> Callable[[Any], List[Any]]:
    """创建列表转换器"""
    
    def transform(value: Any) -> List[Any]:
        if value is None:
            return []
        
        # 确保是列表
        if not isinstance(value, (list, tuple, set)):
            value = [value]
        else:
            value = list(value)
        
        # 应用项目转换器
        if item_transformer:
            value = [item_transformer(item) for item in value]
        
        # 应用长度限制
        if max_items is not None:
            value = value[:max_items]
        
        return value
    
    return transform


def create_dict_transformer(
    key_transformer: Optional[Callable[[Any], str]] = None,
    value_transformer: Optional[Callable[[Any], Any]] = None,
    exclude_none: bool = True
) -> Callable[[Any], Dict[str, Any]]:
    """创建字典转换器"""
    
    def transform(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        
        # 确保是字典
        if not isinstance(value, dict):
            return {}
        
        result = {}
        for k, v in value.items():
            # 转换键
            if key_transformer:
                k = key_transformer(k)
            else:
                k = str(k)
            
            # 转换值
            if value_transformer:
                v = value_transformer(v)
            
            # 排除None值
            if exclude_none and v is None:
                continue
            
            result[k] = v
        
        return result
    
    return transform 