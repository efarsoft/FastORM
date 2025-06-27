"""
FastORM 缓存装饰器

提供方便的缓存装饰器功能。
"""

import hashlib
import json
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .manager import cache

logger = logging.getLogger("fastorm.cache")

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def cache_query(
    ttl: int = 300,
    tags: str | set[str] | None = None,
    key_prefix: str | None = None,
    condition: Callable[..., bool] | None = None,
    serialize: bool = True,
) -> Callable[[F], F]:
    """查询缓存装饰器

    Args:
        ttl: 缓存时间（秒）
        tags: 缓存标签，用于批量失效
        key_prefix: 键前缀，如果不指定则使用函数名
        condition: 缓存条件函数，返回True时才缓存
        serialize: 是否序列化结果（对于复杂对象）

    Example:
        @cache_query(ttl=3600, tags=['users'])
        async def get_active_users():
            return await User.where('status', 'active').get()
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 检查缓存条件
            if condition and not condition(*args, **kwargs):
                return await func(*args, **kwargs)

            # 生成缓存键
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(
                prefix=prefix, args=args, kwargs=kwargs, func_name=func.__qualname__
            )

            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return _deserialize_if_needed(cached_result, serialize)

            # 执行原函数
            result = await func(*args, **kwargs)

            # 设置缓存
            cache_tags = _normalize_tags(tags)
            serialized_result = _serialize_if_needed(result, serialize)

            await cache.set(cache_key, serialized_result, ttl, cache_tags)
            logger.debug(f"缓存设置: {cache_key}")

            return result

        return wrapper  # type: ignore

    return decorator


def invalidate_cache(
    tags: str | set[str] | None = None,
    keys: str | set[str] | None = None,
    clear_all: bool = False,
    before: bool = False,
) -> Callable[[F], F]:
    """缓存失效装饰器

    在函数执行前后自动失效相关缓存。

    Args:
        tags: 要失效的缓存标签
        keys: 要失效的具体缓存键
        clear_all: 是否清空所有缓存
        before: 是否在函数执行前失效缓存

    Example:
        @invalidate_cache(tags=['users'])
        async def create_user(user_data):
            return await User.create(**user_data)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 执行前失效缓存
            if before:
                await _invalidate_caches(tags, keys, clear_all)

            # 执行原函数
            result = await func(*args, **kwargs)

            # 执行后失效缓存
            if not before:
                await _invalidate_caches(tags, keys, clear_all)

            return result

        return wrapper  # type: ignore

    return decorator


def cache_method(
    ttl: int = 300,
    tags: str | set[str] | None = None,
    use_self: bool = True,
    include_class: bool = True,
) -> Callable[[F], F]:
    """模型方法缓存装饰器

    专为模型实例方法设计的缓存装饰器。

    Args:
        ttl: 缓存时间（秒）
        tags: 缓存标签
        use_self: 是否在键中包含实例信息
        include_class: 是否在标签中包含类名

    Example:
        class User(BaseModel):
            @cache_method(ttl=1800, tags=['user_profile'])
            async def get_profile(self):
                return await Profile.where('user_id', self.id).first()
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            prefix = f"{self.__class__.__name__}.{func.__name__}"

            cache_params = {}
            if use_self and hasattr(self, "id"):
                cache_params["id"] = self.id
            elif use_self:
                cache_params["self"] = str(hash(self))

            cache_key = _generate_cache_key(
                prefix=prefix, args=args, kwargs=kwargs, extra_params=cache_params
            )

            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"方法缓存命中: {cache_key}")
                return cached_result

            # 执行原方法
            result = await func(self, *args, **kwargs)

            # 设置缓存
            cache_tags = _normalize_tags(tags)
            if include_class and cache_tags:
                cache_tags.add(self.__class__.__name__.lower())
            elif include_class:
                cache_tags = {self.__class__.__name__.lower()}

            await cache.set(cache_key, result, ttl, cache_tags)
            logger.debug(f"方法缓存设置: {cache_key}")

            return result

        return wrapper  # type: ignore

    return decorator


def cache_property(
    ttl: int = 300, tags: str | set[str] | None = None
) -> Callable[[F], F]:
    """属性缓存装饰器

    缓存计算属性的结果。

    Args:
        ttl: 缓存时间（秒）
        tags: 缓存标签

    Example:
        class User(BaseModel):
            @cache_property(ttl=600, tags=['user_stats'])
            async def order_count(self):
                return await Order.where('user_id', self.id).count()
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            cache_key = _generate_cache_key(
                prefix=f"{self.__class__.__name__}.{func.__name__}",
                args=(getattr(self, "id", str(hash(self))),),
                kwargs=kwargs,
            )

            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"属性缓存命中: {cache_key}")
                return cached_result

            # 计算属性值
            result = await func(self, *args, **kwargs)

            # 设置缓存
            cache_tags = _normalize_tags(tags)
            await cache.set(cache_key, result, ttl, cache_tags)
            logger.debug(f"属性缓存设置: {cache_key}")

            return result

        return wrapper  # type: ignore

    return decorator


def conditional_cache(
    condition_func: Callable[..., bool],
    ttl: int = 300,
    tags: str | set[str] | None = None,
) -> Callable[[F], F]:
    """条件缓存装饰器

    根据条件函数的结果决定是否缓存。

    Args:
        condition_func: 条件判断函数
        ttl: 缓存时间（秒）
        tags: 缓存标签

    Example:
        @conditional_cache(
            condition_func=lambda *args, **kwargs: kwargs.get('use_cache', True),
            ttl=1800
        )
        async def get_user_data(user_id, use_cache=True):
            return await User.find(user_id)
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 检查是否应该使用缓存
            if not condition_func(*args, **kwargs):
                return await func(*args, **kwargs)

            # 使用普通缓存逻辑
            cache_key = _generate_cache_key(
                prefix=func.__name__,
                args=args,
                kwargs=kwargs,
                func_name=func.__qualname__,
            )

            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"条件缓存命中: {cache_key}")
                return cached_result

            result = await func(*args, **kwargs)

            cache_tags = _normalize_tags(tags)
            await cache.set(cache_key, result, ttl, cache_tags)
            logger.debug(f"条件缓存设置: {cache_key}")

            return result

        return wrapper  # type: ignore

    return decorator


# 辅助函数


def _generate_cache_key(
    prefix: str,
    args: tuple = (),
    kwargs: dict | None = None,
    func_name: str | None = None,
    extra_params: dict | None = None,
) -> str:
    """生成缓存键"""
    key_parts = [prefix]

    if func_name:
        key_parts.append(func_name)

    # 处理位置参数
    if args:
        args_str = _serialize_args(args)
        key_parts.append(f"args:{args_str}")

    # 处理关键字参数
    if kwargs:
        kwargs_str = _serialize_kwargs(kwargs)
        key_parts.append(f"kwargs:{kwargs_str}")

    # 处理额外参数
    if extra_params:
        extra_str = _serialize_kwargs(extra_params)
        key_parts.append(f"extra:{extra_str}")

    key = ":".join(key_parts)

    # 如果键太长，使用哈希
    if len(key) > 250:
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{prefix}:hash:{key_hash}"

    return key


def _serialize_args(args: tuple) -> str:
    """序列化位置参数"""
    try:
        return hashlib.md5(str(args).encode()).hexdigest()[:16]
    except Exception:
        args_hash = str(hash(args))
        return hashlib.md5(args_hash.encode()).hexdigest()[:16]


def _serialize_kwargs(kwargs: dict) -> str:
    """序列化关键字参数"""
    try:
        # 排序以确保一致性
        sorted_items = sorted(kwargs.items())
        return hashlib.md5(str(sorted_items).encode()).hexdigest()[:16]
    except Exception:
        frozen_items = frozenset(kwargs.items())
        return hashlib.md5(str(hash(frozen_items)).encode()).hexdigest()[:16]


def _normalize_tags(tags: str | set[str] | None) -> set[str] | None:
    """标准化标签"""
    if not tags:
        return None

    if isinstance(tags, str):
        return {tags}

    return set(tags)


def _serialize_if_needed(result: Any, serialize: bool) -> Any:
    """根据需要序列化结果"""
    if not serialize:
        return result

    # 如果是简单类型，直接返回
    if isinstance(result, (str, int, float, bool, type(None))):
        return result

    # 对于复杂对象，尝试序列化
    try:
        return json.dumps(result, default=str)
    except Exception:
        return result


def _deserialize_if_needed(cached_result: Any, serialize: bool) -> Any:
    """根据需要反序列化结果"""
    if not serialize:
        return cached_result

    # 如果是字符串且看起来像JSON，尝试反序列化
    if isinstance(cached_result, str) and cached_result.startswith("{"):
        try:
            return json.loads(cached_result)
        except Exception:
            return cached_result

    return cached_result


async def _invalidate_caches(
    tags: str | set[str] | None, keys: str | set[str] | None, clear_all: bool
) -> None:
    """失效缓存的通用方法"""
    try:
        if clear_all:
            await cache.clear()
            logger.info("已清空所有缓存")
            return

        # 失效标签
        if tags:
            tag_set = _normalize_tags(tags)
            if tag_set:
                for tag in tag_set:
                    count = await cache.invalidate_tag(tag)
                    logger.info(f"标签 '{tag}' 失效了 {count} 个缓存")

        # 失效具体键
        if keys:
            if isinstance(keys, str):
                await cache.delete(keys)
                logger.info(f"缓存键 '{keys}' 已失效")
            else:
                for key in keys:
                    await cache.delete(key)
                    logger.info(f"缓存键 '{key}' 已失效")
    except Exception as e:
        logger.warning(f"缓存失效失败: {e}")
