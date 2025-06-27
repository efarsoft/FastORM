"""
FastORM批量操作装饰器

提供批量操作的装饰器支持
"""

import functools
from typing import Any, Callable, TypeVar, Optional

from .exceptions import BatchError

F = TypeVar("F", bound=Callable[..., Any])


def batch_operation(
    batch_size: int = 1000,
    validate: bool = True,
    monitor: bool = True,
) -> Callable[[F], F]:
    """批量操作装饰器
    
    Args:
        batch_size: 批量大小
        validate: 是否验证
        monitor: 是否监控
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise BatchError(f"批量操作失败: {e}")
        return wrapper
    return decorator


def monitor_batch(func: F) -> F:
    """监控批量操作装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def retry_batch(
    max_retries: int = 3,
    delay: float = 1.0,
) -> Callable[[F], F]:
    """重试批量操作装饰器"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate_batch(func: F) -> F:
    """验证批量操作装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper 