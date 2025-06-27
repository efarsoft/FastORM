"""
FastORM 验证引擎

基于Pydantic 2.11的高性能验证引擎，提供：
- 验证上下文管理
- 异步验证支持
- 验证缓存机制
- 性能监控
"""

import asyncio
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from dataclasses import field
from functools import lru_cache
from typing import Any

from pydantic import ValidationInfo

from .exceptions import AsyncValidationError
from .exceptions import FieldValidationError
from .exceptions import ModelValidationError
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationContext:
    """验证上下文

    提供验证过程中的上下文信息和配置
    """

    # 验证目标信息
    model_name: str
    instance_id: str | None = None
    operation: str = "validate"  # validate, create, update

    # 验证配置
    strict_mode: bool = False
    allow_partial: bool = False
    validate_assignment: bool = True

    # 异步验证配置
    async_timeout: float = 5.0
    max_concurrent_validations: int = 10

    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 300  # 5分钟

    # 执行上下文
    start_time: float = field(default_factory=time.time)
    validated_fields: set[str] = field(default_factory=set)
    errors: list[ValidationError] = field(default_factory=list)

    # 自定义数据
    custom_data: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: ValidationError) -> None:
        """添加验证错误"""
        self.errors.append(error)
        logger.debug(f"Validation error added: {error}")

    def has_errors(self) -> bool:
        """是否存在验证错误"""
        return len(self.errors) > 0

    def get_field_errors(self, field: str) -> list[FieldValidationError]:
        """获取字段验证错误"""
        return [
            error
            for error in self.errors
            if isinstance(error, FieldValidationError) and error.field == field
        ]

    def mark_field_validated(self, field: str) -> None:
        """标记字段已验证"""
        self.validated_fields.add(field)

    def is_field_validated(self, field: str) -> bool:
        """检查字段是否已验证"""
        return field in self.validated_fields

    def get_duration(self) -> float:
        """获取验证耗时"""
        return time.time() - self.start_time


class ValidationEngine:
    """验证引擎

    提供高性能的验证处理机制，支持同步和异步验证
    """

    def __init__(self):
        self._field_validators: dict[str, list[Callable]] = {}
        self._model_validators: dict[str, list[Callable]] = {}
        self._async_validators: dict[str, list[Callable]] = {}
        self._validation_cache: dict[str, Any] = {}
        self._stats = {
            "total_validations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "async_validations": 0,
            "validation_errors": 0,
        }

    def register_field_validator(
        self, field_name: str, validator: Callable, is_async: bool = False
    ) -> None:
        """注册字段验证器

        Args:
            field_name: 字段名
            validator: 验证器函数
            is_async: 是否为异步验证器
        """
        if is_async:
            if field_name not in self._async_validators:
                self._async_validators[field_name] = []
            self._async_validators[field_name].append(validator)
        else:
            if field_name not in self._field_validators:
                self._field_validators[field_name] = []
            self._field_validators[field_name].append(validator)

        logger.debug(
            f"Registered {'async' if is_async else 'sync'} validator "
            f"for field '{field_name}'"
        )

    def register_model_validator(
        self, model_name: str, validator: Callable, is_async: bool = False
    ) -> None:
        """注册模型验证器

        Args:
            model_name: 模型名
            validator: 验证器函数
            is_async: 是否为异步验证器
        """
        key = f"{model_name}:{'async' if is_async else 'sync'}"
        if key not in self._model_validators:
            self._model_validators[key] = []
        self._model_validators[key].append(validator)

        logger.debug(
            f"Registered {'async' if is_async else 'sync'} model validator "
            f"for model '{model_name}'"
        )

    async def validate_field(
        self,
        field_name: str,
        value: Any,
        context: ValidationContext,
        validation_info: ValidationInfo | None = None,
    ) -> Any:
        """验证单个字段

        Args:
            field_name: 字段名
            value: 字段值
            context: 验证上下文
            validation_info: Pydantic验证信息

        Returns:
            验证后的值

        Raises:
            FieldValidationError: 字段验证失败
        """
        self._stats["total_validations"] += 1

        # 检查缓存
        if context.enable_cache:
            cache_key = self._get_cache_key(field_name, value, context)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self._stats["cache_hits"] += 1
                return cached_result
            self._stats["cache_misses"] += 1

        try:
            # 执行同步验证器
            validated_value = await self._run_sync_field_validators(
                field_name, value, context, validation_info
            )

            # 执行异步验证器
            if field_name in self._async_validators:
                validated_value = await self._run_async_field_validators(
                    field_name, validated_value, context, validation_info
                )

            # 缓存结果
            if context.enable_cache:
                self._set_cache(cache_key, validated_value, context.cache_ttl)

            context.mark_field_validated(field_name)
            return validated_value

        except Exception as e:
            self._stats["validation_errors"] += 1
            if isinstance(e, FieldValidationError):
                context.add_error(e)
                raise
            else:
                error = FieldValidationError(
                    field=field_name,
                    value=value,
                    message=str(e),
                    validator_name="field_validator",
                )
                context.add_error(error)
                raise error

    async def validate_model(
        self, model_name: str, instance: Any, context: ValidationContext
    ) -> None:
        """验证整个模型

        Args:
            model_name: 模型名
            instance: 模型实例
            context: 验证上下文

        Raises:
            ModelValidationError: 模型验证失败
        """
        try:
            # 执行同步模型验证器
            sync_key = f"{model_name}:sync"
            if sync_key in self._model_validators:
                for validator in self._model_validators[sync_key]:
                    validator(instance, context)

            # 执行异步模型验证器
            async_key = f"{model_name}:async"
            if async_key in self._model_validators:
                await self._run_async_model_validators(
                    instance, self._model_validators[async_key], context
                )

        except Exception as e:
            self._stats["validation_errors"] += 1
            if isinstance(e, ModelValidationError):
                raise
            else:
                error = ModelValidationError(
                    model_name=model_name,
                    message=str(e),
                    context={"operation": context.operation},
                )
                raise error

    async def _run_sync_field_validators(
        self,
        field_name: str,
        value: Any,
        context: ValidationContext,
        validation_info: ValidationInfo | None,
    ) -> Any:
        """运行同步字段验证器"""
        validated_value = value

        if field_name in self._field_validators:
            for validator in self._field_validators[field_name]:
                if validation_info:
                    validated_value = validator(validated_value, validation_info)
                else:
                    validated_value = validator(validated_value)

        return validated_value

    async def _run_async_field_validators(
        self,
        field_name: str,
        value: Any,
        context: ValidationContext,
        validation_info: ValidationInfo | None,
    ) -> Any:
        """运行异步字段验证器"""
        self._stats["async_validations"] += 1
        validated_value = value

        validators = self._async_validators[field_name]

        # 并发执行异步验证器
        tasks = []
        for validator in validators:
            if validation_info:
                task = asyncio.create_task(
                    self._run_single_async_validator(
                        validator, validated_value, validation_info, context
                    )
                )
            else:
                task = asyncio.create_task(
                    self._run_single_async_validator(
                        validator, validated_value, None, context
                    )
                )
            tasks.append(task)

        # 等待所有验证器完成
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=context.async_timeout,
            )

            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    raise result
                validated_value = result

        except asyncio.TimeoutError:
            raise AsyncValidationError(
                message=f"Async validation timeout for field '{field_name}'",
                field=field_name,
                value=value,
                timeout=context.async_timeout,
            )

        return validated_value

    async def _run_single_async_validator(
        self,
        validator: Callable,
        value: Any,
        validation_info: ValidationInfo | None,
        context: ValidationContext,
    ) -> Any:
        """运行单个异步验证器"""
        if validation_info:
            return await validator(value, validation_info)
        else:
            return await validator(value)

    async def _run_async_model_validators(
        self, instance: Any, validators: list[Callable], context: ValidationContext
    ) -> None:
        """运行异步模型验证器"""
        tasks = [
            asyncio.create_task(validator(instance, context))
            for validator in validators
        ]

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=context.async_timeout
            )
        except asyncio.TimeoutError:
            raise AsyncValidationError(
                message="Async model validation timeout", timeout=context.async_timeout
            )

    @lru_cache(maxsize=1000)
    def _get_cache_key(
        self, field_name: str, value: Any, context: ValidationContext
    ) -> str:
        """生成缓存键"""
        # 简化的缓存键生成
        try:
            value_hash = hash(value) if value is not None else 0
        except TypeError:
            # 对于不可哈希的值，使用字符串表示
            value_hash = hash(str(value))

        return f"{context.model_name}:{field_name}:{value_hash}:{context.operation}"

    def _get_from_cache(self, cache_key: str) -> Any | None:
        """从缓存获取值"""
        cache_entry = self._validation_cache.get(cache_key)
        if cache_entry:
            timestamp, value, ttl = cache_entry
            if time.time() - timestamp < ttl:
                return value
            else:
                # 缓存过期，删除
                del self._validation_cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, value: Any, ttl: int) -> None:
        """设置缓存值"""
        self._validation_cache[cache_key] = (time.time(), value, ttl)

        # 简单的缓存清理机制
        if len(self._validation_cache) > 10000:
            self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, (timestamp, _, ttl) in self._validation_cache.items():
            if current_time - timestamp >= ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._validation_cache[key]

        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> dict[str, Any]:
        """获取验证引擎统计信息"""
        cache_hit_rate = 0
        total_cache_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        if total_cache_requests > 0:
            cache_hit_rate = self._stats["cache_hits"] / total_cache_requests

        return {
            **self._stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._validation_cache),
            "field_validators": sum(len(v) for v in self._field_validators.values()),
            "model_validators": sum(len(v) for v in self._model_validators.values()),
            "async_validators": sum(len(v) for v in self._async_validators.values()),
        }

    def clear_cache(self) -> None:
        """清空验证缓存"""
        self._validation_cache.clear()
        logger.info("Validation cache cleared")

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_validations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "async_validations": 0,
            "validation_errors": 0,
        }


# 全局验证引擎实例
_validation_engine: ValidationEngine | None = None


def get_validation_engine() -> ValidationEngine:
    """获取全局验证引擎实例"""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()
    return _validation_engine


@asynccontextmanager
async def create_validation_context(
    model_name: str, operation: str = "validate", **kwargs
) -> ValidationContext:
    """创建验证上下文管理器

    Args:
        model_name: 模型名
        operation: 操作类型
        **kwargs: 其他上下文参数

    Yields:
        ValidationContext: 验证上下文
    """
    context = ValidationContext(model_name=model_name, operation=operation, **kwargs)

    try:
        yield context
    finally:
        duration = context.get_duration()
        logger.debug(
            f"Validation completed for {model_name}: "
            f"duration={duration:.3f}s, errors={len(context.errors)}"
        )
