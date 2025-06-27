"""
FastORM 验证装饰器

提供简洁的验证装饰器，用于字段和模型验证
"""

from collections.abc import Callable
from functools import wraps

from pydantic import field_validator
from pydantic import model_validator

from .field_validators import get_field_validator_registry
from .model_validators import get_model_validator_registry


def validate_field(field_name: str, *validator_names: str, mode: str = "before"):
    """字段验证装饰器

    Args:
        field_name: 字段名
        *validator_names: 验证器名称列表
        mode: 验证模式
    """

    def decorator(cls):
        registry = get_field_validator_registry()

        for validator_name in validator_names:
            validator = registry.get_validator(validator_name)
            if validator:
                # 动态添加 field_validator
                setattr(
                    cls,
                    f"validate_{field_name}_{validator_name}",
                    field_validator(field_name, mode=mode)(validator),
                )

        return cls

    return decorator


def validate_model(*validator_names: str, mode: str = "after"):
    """模型验证装饰器

    Args:
        *validator_names: 验证器名称列表
        mode: 验证模式
    """

    def decorator(cls):
        model_name = cls.__name__
        registry = get_model_validator_registry()

        for validator_name in validator_names:
            validators = registry.get_validators(model_name)
            for validator_func, config in validators:
                if config.name == validator_name:
                    # 动态添加 model_validator
                    setattr(
                        cls,
                        f"validate_model_{validator_name}",
                        model_validator(mode=mode)(validator_func),
                    )

        return cls

    return decorator


def async_validator(timeout: float = 5.0):
    """异步验证器装饰器

    Args:
        timeout: 超时时间
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里可以添加超时控制和其他异步验证逻辑
            return await func(*args, **kwargs)

        wrapper._is_async_validator = True
        wrapper._timeout = timeout
        return wrapper

    return decorator
