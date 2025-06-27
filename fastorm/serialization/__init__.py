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

from .engine import (
    SerializationEngine,
    SerializationContext,
    SerializationConfig
)
from .serializers import (
    BaseSerializer,
    ModelSerializer,
    FieldSerializer,
    RelationSerializer,
    SerializerRegistry,
    SerializerChain
)
from .fields import (
    SerializationField,
    FieldConfig,
    FieldMapping,
    FieldTransformer,
    FieldMappingRegistry
)
from .formatters import (
    BaseFormatter,
    JSONFormatter,
    XMLFormatter,
    CSVFormatter,
    FormatterRegistry
)
from .decorators import (
    serialize_field,
    serialize_model,
    serialize_relation,
    custom_serializer
)
from .exceptions import (
    SerializationError,
    FieldSerializationError,
    RelationSerializationError,
    FormatterError,
    convert_pydantic_serialization_error
)

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
    "convert_pydantic_serialization_error"
] 