"""
FastORM序列化引擎模块

提供高性能的序列化引擎，支持：
- 模型序列化和反序列化
- 异步序列化支持
- 缓存机制
- 循环引用检测
- 性能监控
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .exceptions import AsyncSerializationError
from .exceptions import CircularReferenceError
from .exceptions import SerializationError
from .exceptions import convert_pydantic_serialization_error


@dataclass
class SerializationConfig:
    """序列化配置"""

    # 基础配置
    include_none: bool = False
    exclude_none: bool = True
    by_alias: bool = True
    exclude_unset: bool = False

    # 关系序列化配置
    serialize_relations: bool = True
    max_depth: int = 3
    exclude_relations: set[str] = field(default_factory=set)

    # 性能配置
    enable_cache: bool = True
    cache_ttl: int = 300  # 5分钟

    # 异步配置
    async_timeout: float = 30.0
    max_concurrent: int = 10

    # 循环引用检测
    detect_circular: bool = True
    max_reference_depth: int = 10

    # 输出格式配置
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    decimal_precision: int = 2

    def copy(self, **kwargs) -> "SerializationConfig":
        """创建配置副本"""
        values = {
            "include_none": self.include_none,
            "exclude_none": self.exclude_none,
            "by_alias": self.by_alias,
            "exclude_unset": self.exclude_unset,
            "serialize_relations": self.serialize_relations,
            "max_depth": self.max_depth,
            "exclude_relations": self.exclude_relations.copy(),
            "enable_cache": self.enable_cache,
            "cache_ttl": self.cache_ttl,
            "async_timeout": self.async_timeout,
            "max_concurrent": self.max_concurrent,
            "detect_circular": self.detect_circular,
            "max_reference_depth": self.max_reference_depth,
            "datetime_format": self.datetime_format,
            "decimal_precision": self.decimal_precision,
        }
        values.update(kwargs)
        return SerializationConfig(**values)


@dataclass
class SerializationContext:
    """序列化上下文"""

    # 序列化目标信息
    model_name: str | None = None
    instance_id: str | None = None
    operation_type: str = "serialize"  # serialize, deserialize

    # 序列化状态
    current_depth: int = 0
    reference_path: list[str] = field(default_factory=list)
    serialized_objects: set[int] = field(default_factory=set)

    # 配置
    config: SerializationConfig = field(default_factory=SerializationConfig)

    # 执行上下文
    start_time: float = field(default_factory=time.time)
    errors: list[SerializationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 异步支持
    semaphore: asyncio.Semaphore | None = None

    def add_error(self, error: SerializationError) -> None:
        """添加错误"""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)

    def enter_object(self, obj_id: int, obj_name: str) -> bool:
        """进入对象序列化，检测循环引用"""
        if self.config.detect_circular:
            if obj_id in self.serialized_objects:
                raise CircularReferenceError(
                    f"检测到循环引用: {obj_name}",
                    reference_path=self.reference_path + [obj_name],
                )

            if len(self.reference_path) >= self.config.max_reference_depth:
                raise CircularReferenceError(
                    f"引用深度超过限制: {self.config.max_reference_depth}",
                    reference_path=self.reference_path + [obj_name],
                )

        self.serialized_objects.add(obj_id)
        self.reference_path.append(obj_name)
        self.current_depth += 1

        return self.current_depth <= self.config.max_depth

    def exit_object(self, obj_id: int) -> None:
        """退出对象序列化"""
        if self.reference_path:
            self.reference_path.pop()
        if obj_id in self.serialized_objects:
            self.serialized_objects.remove(obj_id)
        self.current_depth = max(0, self.current_depth - 1)

    def get_elapsed_time(self) -> float:
        """获取执行时间"""
        return time.time() - self.start_time


class SerializationEngine:
    """序列化引擎"""

    def __init__(self, config: SerializationConfig | None = None):
        self.config = config or SerializationConfig()

        # 缓存
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timestamps: dict[str, float] = {}

        # 序列化器注册表
        self._serializers: dict[type, Callable] = {}
        self._field_serializers: dict[str, Callable] = {}

        # 性能统计
        self._stats = {
            "total_serializations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "async_serializations": 0,
            "errors": 0,
            "average_time": 0.0,
        }

        # 异步支持
        self._semaphore: asyncio.Semaphore | None = None

    def register_serializer(
        self,
        model_type: type,
        serializer: Callable[[Any, SerializationContext], dict[str, Any]],
    ) -> None:
        """注册模型序列化器"""
        self._serializers[model_type] = serializer

    def register_field_serializer(
        self, field_name: str, serializer: Callable[[Any, SerializationContext], Any]
    ) -> None:
        """注册字段序列化器"""
        self._field_serializers[field_name] = serializer

    def serialize(
        self,
        obj: Any,
        config: SerializationConfig | None = None,
        context: SerializationContext | None = None,
    ) -> dict[str, Any]:
        """序列化对象"""

        start_time = time.time()
        self._stats["total_serializations"] += 1

        try:
            # 准备配置和上下文
            effective_config = config or self.config
            if context is None:
                context = SerializationContext(config=effective_config)

            # 检查缓存
            if effective_config.enable_cache:
                cache_key = self._get_cache_key(obj, effective_config)
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self._stats["cache_hits"] += 1
                    return cached_result
                self._stats["cache_misses"] += 1

            # 执行序列化
            result = self._serialize_object(obj, context)

            # 缓存结果
            if effective_config.enable_cache and cache_key:
                self._set_cache(cache_key, result, effective_config.cache_ttl)

            # 更新统计
            elapsed_time = time.time() - start_time
            self._update_stats(elapsed_time)

            return result

        except Exception as e:
            self._stats["errors"] += 1
            if isinstance(e, SerializationError):
                raise
            else:
                raise SerializationError(
                    f"序列化失败: {e!s}", context={"object_type": type(obj).__name__}
                )

    async def serialize_async(
        self,
        obj: Any,
        config: SerializationConfig | None = None,
        context: SerializationContext | None = None,
    ) -> dict[str, Any]:
        """异步序列化对象"""

        self._stats["async_serializations"] += 1

        # 准备信号量
        if self._semaphore is None:
            max_concurrent = (config or self.config).max_concurrent
            self._semaphore = asyncio.Semaphore(max_concurrent)

        async with self._semaphore:
            try:
                # 设置超时
                timeout = (config or self.config).async_timeout
                return await asyncio.wait_for(
                    self._serialize_async_impl(obj, config, context), timeout=timeout
                )
            except asyncio.TimeoutError:
                raise AsyncSerializationError(
                    "异步序列化超时",
                    timeout=timeout,
                    async_serializer=type(obj).__name__,
                )

    async def _serialize_async_impl(
        self,
        obj: Any,
        config: SerializationConfig | None,
        context: SerializationContext | None,
    ) -> dict[str, Any]:
        """异步序列化实现"""

        # 在线程池中执行序列化
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.serialize, obj, config, context)

    def _serialize_object(
        self, obj: Any, context: SerializationContext
    ) -> dict[str, Any]:
        """序列化单个对象"""

        if obj is None:
            return None

        # 获取对象信息
        obj_type = type(obj)
        obj_id = id(obj)
        obj_name = getattr(obj, "__class__.__name__", str(obj_type))

        # 检查是否应该继续序列化
        should_continue = context.enter_object(obj_id, obj_name)

        try:
            if not should_continue:
                context.add_warning(f"达到最大深度，跳过 {obj_name}")
                return {"__skipped__": True, "__reason__": "max_depth"}

            # 查找自定义序列化器
            if obj_type in self._serializers:
                return self._serializers[obj_type](obj, context)

            # 处理Pydantic模型
            if isinstance(obj, BaseModel):
                return self._serialize_pydantic_model(obj, context)

            # 处理SQLAlchemy模型
            if hasattr(obj, "__table__"):
                return self._serialize_sqlalchemy_model(obj, context)

            # 处理基础类型
            if isinstance(obj, (str, int, float, bool)):
                return obj

            # 处理容器类型
            if isinstance(obj, (list, tuple, set)):
                return self._serialize_container(obj, context)

            if isinstance(obj, dict):
                return self._serialize_dict(obj, context)

            # 处理日期时间
            if isinstance(obj, datetime):
                return obj.strftime(context.config.datetime_format)

            # 默认转换为字符串
            context.add_warning(f"未知类型 {obj_type}，转换为字符串")
            return str(obj)

        finally:
            context.exit_object(obj_id)

    def _serialize_pydantic_model(
        self, model: BaseModel, context: SerializationContext
    ) -> dict[str, Any]:
        """序列化Pydantic模型"""

        try:
            # 使用Pydantic的model_dump方法
            return model.model_dump(
                include=None,
                exclude=context.config.exclude_relations
                if not context.config.serialize_relations
                else None,
                by_alias=context.config.by_alias,
                exclude_unset=context.config.exclude_unset,
                exclude_none=context.config.exclude_none,
            )
        except Exception as e:
            if hasattr(e, "errors"):
                raise convert_pydantic_serialization_error(
                    e,
                    {"model": model.__class__.__name__, "context": context.model_name},
                )
            else:
                raise SerializationError(
                    f"Pydantic模型序列化失败: {e!s}",
                    context={"model": model.__class__.__name__},
                )

    def _serialize_sqlalchemy_model(
        self, model: Any, context: SerializationContext
    ) -> dict[str, Any]:
        """序列化SQLAlchemy模型"""

        result = {}

        # 序列化列字段
        for column in model.__table__.columns:
            field_name = column.name

            # 检查是否有自定义字段序列化器
            if field_name in self._field_serializers:
                try:
                    value = getattr(model, field_name)
                    result[field_name] = self._field_serializers[field_name](
                        value, context
                    )
                except Exception as e:
                    context.add_error(
                        SerializationError(
                            f"字段序列化失败: {e!s}",
                            field=field_name,
                            value=getattr(model, field_name, None),
                        )
                    )
            else:
                value = getattr(model, field_name)
                result[field_name] = self._serialize_object(value, context)

        # 序列化关系字段（如果启用）
        if context.config.serialize_relations:
            self._serialize_relations(model, result, context)

        return result

    def _serialize_relations(
        self, model: Any, result: dict[str, Any], context: SerializationContext
    ) -> None:
        """序列化关系字段"""

        # 获取关系属性
        if hasattr(model, "__mapper__"):
            for rel in model.__mapper__.relationships:
                rel_name = rel.key

                # 检查是否排除此关系
                if rel_name in context.config.exclude_relations:
                    continue

                try:
                    rel_value = getattr(model, rel_name)
                    if rel_value is not None:
                        result[rel_name] = self._serialize_object(rel_value, context)
                except Exception as e:
                    context.add_error(
                        SerializationError(
                            f"关系序列化失败: {e!s}",
                            field=rel_name,
                            context={"relation_type": str(rel.direction)},
                        )
                    )

    def _serialize_container(
        self, container: list | tuple | set, context: SerializationContext
    ) -> list[Any]:
        """序列化容器类型"""

        result = []
        for item in container:
            try:
                serialized_item = self._serialize_object(item, context)
                result.append(serialized_item)
            except Exception as e:
                context.add_error(
                    SerializationError(f"容器项序列化失败: {e!s}", value=item)
                )

        return result

    def _serialize_dict(
        self, data: dict[str, Any], context: SerializationContext
    ) -> dict[str, Any]:
        """序列化字典"""

        result = {}
        for key, value in data.items():
            try:
                result[str(key)] = self._serialize_object(value, context)
            except Exception as e:
                context.add_error(
                    SerializationError(
                        f"字典项序列化失败: {e!s}", field=str(key), value=value
                    )
                )

        return result

    def _get_cache_key(self, obj: Any, config: SerializationConfig) -> str:
        """生成缓存键"""

        obj_repr = f"{type(obj).__name__}_{id(obj)}"
        config_repr = f"{config.exclude_none}_{config.by_alias}_{config.max_depth}"
        return f"{obj_repr}_{config_repr}"

    def _get_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """从缓存获取结果"""

        if cache_key not in self._cache:
            return None

        # 检查是否过期
        if cache_key in self._cache_timestamps:
            cache_time = self._cache_timestamps[cache_key]
            if time.time() - cache_time > self.config.cache_ttl:
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
                return None

        return self._cache[cache_key]

    def _set_cache(self, cache_key: str, result: dict[str, Any], ttl: int) -> None:
        """设置缓存"""

        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

    def _update_stats(self, elapsed_time: float) -> None:
        """更新性能统计"""

        # 更新平均时间
        total = self._stats["total_serializations"]
        current_avg = self._stats["average_time"]
        self._stats["average_time"] = (current_avg * (total - 1) + elapsed_time) / total

    def get_stats(self) -> dict[str, Any]:
        """获取性能统计"""

        total = self._stats["total_serializations"]
        cache_total = self._stats["cache_hits"] + self._stats["cache_misses"]

        return {
            "total_serializations": total,
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "cache_hit_rate": (
                self._stats["cache_hits"] / cache_total if cache_total > 0 else 0.0
            ),
            "async_serializations": self._stats["async_serializations"],
            "errors": self._stats["errors"],
            "error_rate": self._stats["errors"] / total if total > 0 else 0.0,
            "average_time": self._stats["average_time"],
            "cache_size": len(self._cache),
        }

    def clear_cache(self) -> None:
        """清空缓存"""

        self._cache.clear()
        self._cache_timestamps.clear()

    def reset_stats(self) -> None:
        """重置性能统计"""

        self._stats = {
            "total_serializations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "async_serializations": 0,
            "errors": 0,
            "average_time": 0.0,
        }
