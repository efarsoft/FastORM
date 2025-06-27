"""
FastORM 字段验证器

基于Pydantic 2.11的字段验证器系统，提供：
- 内置验证器（email、url、phone等）
- 数值范围验证器
- 字符串长度验证器
- 自定义验证器支持
- 异步验证器支持
"""

import re
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
import logging

from pydantic import ValidationInfo
from .exceptions import FieldValidationError

logger = logging.getLogger(__name__)


@dataclass
class ValidatorConfig:
    """验证器配置"""
    name: str
    description: str
    error_message: str
    is_async: bool = False
    priority: int = 0  # 验证器优先级，数字越小优先级越高


class FieldValidatorRegistry:
    """字段验证器注册表
    
    管理所有字段验证器的注册、查询和执行
    """
    
    def __init__(self):
        self._validators: Dict[str, Callable] = {}
        self._configs: Dict[str, ValidatorConfig] = {}
        self._async_validators: Dict[str, Callable] = {}
    
    def register(
        self,
        name: str,
        validator: Callable,
        description: str = "",
        error_message: str = "",
        is_async: bool = False,
        priority: int = 0
    ) -> None:
        """注册验证器
        
        Args:
            name: 验证器名称
            validator: 验证器函数
            description: 描述
            error_message: 错误消息模板
            is_async: 是否为异步验证器
            priority: 优先级
        """
        config = ValidatorConfig(
            name=name,
            description=description,
            error_message=error_message or f"Validation failed for {name}",
            is_async=is_async,
            priority=priority
        )
        
        if is_async:
            self._async_validators[name] = validator
        else:
            self._validators[name] = validator
        
        self._configs[name] = config
        
        logger.debug(
            f"Registered {'async' if is_async else 'sync'} validator: {name}"
        )
    
    def get_validator(self, name: str) -> Optional[Callable]:
        """获取验证器"""
        if name in self._validators:
            return self._validators[name]
        elif name in self._async_validators:
            return self._async_validators[name]
        return None
    
    def get_config(self, name: str) -> Optional[ValidatorConfig]:
        """获取验证器配置"""
        return self._configs.get(name)
    
    def list_validators(self) -> List[str]:
        """列出所有验证器名称"""
        return list(self._configs.keys())
    
    def is_async_validator(self, name: str) -> bool:
        """检查是否为异步验证器"""
        config = self._configs.get(name)
        return config.is_async if config else False


# 全局验证器注册表
_field_validator_registry = FieldValidatorRegistry()


def register_field_validator(
    name: str,
    description: str = "",
    error_message: str = "",
    is_async: bool = False,
    priority: int = 0
):
    """字段验证器装饰器
    
    Args:
        name: 验证器名称
        description: 描述
        error_message: 错误消息
        is_async: 是否为异步验证器
        priority: 优先级
    """
    def decorator(func: Callable) -> Callable:
        _field_validator_registry.register(
            name=name,
            validator=func,
            description=description,
            error_message=error_message,
            is_async=is_async,
            priority=priority
        )
        return func
    return decorator


def get_field_validator_registry() -> FieldValidatorRegistry:
    """获取字段验证器注册表"""
    return _field_validator_registry


# =============================================================================
# 内置验证器
# =============================================================================

@register_field_validator(
    "email",
    description="验证邮箱地址格式",
    error_message="Invalid email format"
)
def validate_email(value: str, info: ValidationInfo = None) -> str:
    """邮箱验证器"""
    if not isinstance(value, str):
        raise FieldValidationError(
            field=info.field_name if info else "email",
            value=value,
            message="Email must be a string",
            validator_name="email"
        )
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise FieldValidationError(
            field=info.field_name if info else "email",
            value=value,
            message="Invalid email format",
            validator_name="email"
        )
    
    return value.lower()  # 标准化为小写


@register_field_validator(
    "url",
    description="验证URL格式",
    error_message="Invalid URL format"
)
def validate_url(value: str, info: ValidationInfo = None) -> str:
    """URL验证器"""
    if not isinstance(value, str):
        raise FieldValidationError(
            field=info.field_name if info else "url",
            value=value,
            message="URL must be a string",
            validator_name="url"
        )
    
    url_pattern = (
        r'^https?://(?:[-\w.])+(?:\:[0-9]+)?'
        r'(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    )
    if not re.match(url_pattern, value):
        raise FieldValidationError(
            field=info.field_name if info else "url",
            value=value,
            message="Invalid URL format",
            validator_name="url"
        )
    
    return value


@register_field_validator(
    "phone",
    description="验证手机号格式（中国）",
    error_message="Invalid phone number format"
)
def validate_phone(value: str, info: ValidationInfo = None) -> str:
    """手机号验证器（中国）"""
    if not isinstance(value, str):
        raise FieldValidationError(
            field=info.field_name if info else "phone",
            value=value,
            message="Phone number must be a string",
            validator_name="phone"
        )
    
    # 移除所有非数字字符
    cleaned = re.sub(r'\D', '', value)
    
    # 中国手机号格式：1开头，第二位是3-9，总共11位
    phone_pattern = r'^1[3-9]\d{9}$'
    if not re.match(phone_pattern, cleaned):
        raise FieldValidationError(
            field=info.field_name if info else "phone",
            value=value,
            message="Invalid Chinese phone number format",
            validator_name="phone"
        )
    
    return cleaned


def validate_min_length(min_len: int):
    """最小长度验证器工厂"""
    def validator(value: str, info: ValidationInfo = None) -> str:
        if not isinstance(value, str):
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message="Value must be a string",
                validator_name="min_length"
            )
        
        if len(value) < min_len:
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message=f"String must be at least {min_len} characters",
                validator_name="min_length",
                constraint={"min_length": min_len}
            )
        
        return value
    
    return validator


def validate_max_length(max_len: int):
    """最大长度验证器工厂"""
    def validator(value: str, info: ValidationInfo = None) -> str:
        if not isinstance(value, str):
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message="Value must be a string",
                validator_name="max_length"
            )
        
        if len(value) > max_len:
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message=f"String must be at most {max_len} characters",
                validator_name="max_length",
                constraint={"max_length": max_len}
            )
        
        return value
    
    return validator


def validate_min_value(min_val: Union[int, float]):
    """最小值验证器工厂"""
    def validator(
        value: Union[int, float], 
        info: ValidationInfo = None
    ) -> Union[int, float]:
        if not isinstance(value, (int, float)):
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message="Value must be a number",
                validator_name="min_value"
            )
        
        if value < min_val:
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message=f"Value must be at least {min_val}",
                validator_name="min_value",
                constraint={"min_value": min_val}
            )
        
        return value
    
    return validator


def validate_max_value(max_val: Union[int, float]):
    """最大值验证器工厂"""
    def validator(
        value: Union[int, float], 
        info: ValidationInfo = None
    ) -> Union[int, float]:
        if not isinstance(value, (int, float)):
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message="Value must be a number",
                validator_name="max_value"
            )
        
        if value > max_val:
            raise FieldValidationError(
                field=info.field_name if info else "field",
                value=value,
                message=f"Value must be at most {max_val}",
                validator_name="max_value",
                constraint={"max_value": max_val}
            )
        
        return value
    
    return validator


# =============================================================================
# 验证器组合器
# =============================================================================

class ValidatorChain:
    """验证器链
    
    允许组合多个验证器按顺序执行
    """
    
    def __init__(self):
        self.validators: List[Callable] = []
        self.async_validators: List[Callable] = []
    
    def add_validator(
        self, 
        validator: Callable, 
        is_async: bool = False
    ) -> 'ValidatorChain':
        """添加验证器"""
        if is_async:
            self.async_validators.append(validator)
        else:
            self.validators.append(validator)
        return self
    
    def add_min_length(self, min_len: int) -> 'ValidatorChain':
        """添加最小长度验证"""
        return self.add_validator(validate_min_length(min_len))
    
    def add_max_length(self, max_len: int) -> 'ValidatorChain':
        """添加最大长度验证"""
        return self.add_validator(validate_max_length(max_len))
    
    async def validate(
        self, 
        value: Any, 
        info: ValidationInfo = None
    ) -> Any:
        """执行验证链"""
        # 执行同步验证器
        for validator in self.validators:
            value = validator(value, info)
        
        # 执行异步验证器
        for async_validator in self.async_validators:
            value = await async_validator(value, info)
        
        return value


def create_validator_chain() -> ValidatorChain:
    """创建验证器链"""
    return ValidatorChain()


def create_string_validator(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    email: bool = False,
    url: bool = False,
    phone: bool = False
) -> ValidatorChain:
    """创建字符串验证器组合
    
    Args:
        min_length: 最小长度
        max_length: 最大长度
        email: 是否验证邮箱格式
        url: 是否验证URL格式
        phone: 是否验证手机号格式
        
    Returns:
        验证器链
    """
    chain = create_validator_chain()
    
    if min_length is not None:
        chain.add_min_length(min_length)
    
    if max_length is not None:
        chain.add_max_length(max_length)
    
    if email:
        chain.add_validator(validate_email)
    
    if url:
        chain.add_validator(validate_url)
        
    if phone:
        chain.add_validator(validate_phone)
    
    return chain


def create_number_validator(
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None
) -> ValidatorChain:
    """创建数值验证器组合
    
    Args:
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        验证器链
    """
    chain = create_validator_chain()
    
    if min_value is not None:
        chain.add_validator(validate_min_value(min_value))
    
    if max_value is not None:
        chain.add_validator(validate_max_value(max_value))
    
    return chain 