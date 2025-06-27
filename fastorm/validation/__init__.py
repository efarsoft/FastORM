"""
FastORM 验证系统

基于Pydantic 2.11的现代验证框架，提供：
- 字段级验证器
- 模型级验证器  
- 自定义验证规则
- 异步验证支持
- 验证上下文管理
"""

# Pydantic 2.11 验证器
from pydantic import field_validator, model_validator, ValidationInfo
from pydantic.functional_validators import (
    BeforeValidator,
    AfterValidator, 
    PlainValidator,
    WrapValidator
)

# 验证器核心组件
from .engine import ValidationEngine, ValidationContext
from .field_validators import (
    FieldValidatorRegistry, 
    register_field_validator
)
from .model_validators import (
    ModelValidatorRegistry, 
    register_model_validator
)
from .rules import ValidationRule, create_validation_rule
from .decorators import validate_field, validate_model, async_validator
from .exceptions import (
    ValidationError, 
    FieldValidationError, 
    ModelValidationError
)

__all__ = [
    # Pydantic 2.11 验证器
    "field_validator",
    "model_validator", 
    "ValidationInfo",
    "BeforeValidator",
    "AfterValidator",
    "PlainValidator", 
    "WrapValidator",
    
    # 验证引擎
    "ValidationEngine",
    "ValidationContext",
    
    # 验证器注册
    "FieldValidatorRegistry",
    "ModelValidatorRegistry",
    "register_field_validator",
    "register_model_validator",
    
    # 验证规则
    "ValidationRule",
    "create_validation_rule",
    
    # 装饰器
    "validate_field",
    "validate_model", 
    "async_validator",
    
    # 异常
    "ValidationError",
    "FieldValidationError",
    "ModelValidationError",
] 