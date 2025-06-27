"""
FastORM序列化系统模块

基于Pydantic 2.11的高性能序列化系统，提供：
- 模型到字典/JSON的序列化
- 字典/JSON到模型的反序列化
- 自定义序列化器和字段映射
- 关系对象序列化支持
- 批量序列化优化
- 异步序列化支持
"""

from .decorators import custom_serializer
from .decorators import serialize_field
from .decorators import serialize_model
from .decorators import serialize_relation
from .engine import SerializationConfig
from .engine import SerializationContext
from .engine import SerializationEngine
from .exceptions import FieldSerializationError
from .exceptions import FormatterError
from .exceptions import RelationSerializationError
from .exceptions import SerializationError
from .exceptions import convert_pydantic_serialization_error
from .fields import FieldConfig
from .fields import FieldMapping
from .fields import FieldMappingRegistry
from .fields import FieldTransformer
from .fields import SerializationField
from .formatters import BaseFormatter
from .formatters import CSVFormatter
from .formatters import FormatterRegistry
from .formatters import JSONFormatter
from .formatters import XMLFormatter
from .serializers import BaseSerializer
from .serializers import FieldSerializer
from .serializers import ModelSerializer
from .serializers import RelationSerializer
from .serializers import SerializerChain
from .serializers import SerializerRegistry

__all__ = [
    # 序列化引擎
    "SerializationEngine",
    "SerializationContext",
    "SerializationConfig",
    # 序列化器
    "BaseSerializer",
    "ModelSerializer",
    "FieldSerializer",
    "RelationSerializer",
    "SerializerRegistry",
    "SerializerChain",
    # 字段处理
    "SerializationField",
    "FieldConfig",
    "FieldMapping",
    "FieldTransformer",
    "FieldMappingRegistry",
    # 格式化器
    "BaseFormatter",
    "JSONFormatter",
    "XMLFormatter",
    "CSVFormatter",
    "FormatterRegistry",
    # 装饰器
    "serialize_field",
    "serialize_model",
    "serialize_relation",
    "custom_serializer",
    # 异常
    "SerializationError",
    "FieldSerializationError",
    "RelationSerializationError",
    "FormatterError",
    "convert_pydantic_serialization_error",
]
