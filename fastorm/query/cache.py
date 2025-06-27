"""
FastORM 查询缓存集成

参考Laravel Illuminate Database的缓存设计模式，
直接集成到QueryBuilder中，提供remember/forget等方法。
"""

import hashlib
import json
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("fastorm.cache")

T = TypeVar("T")


class QueryCacheSupport:
    """查询缓存支持 Mixin

    为QueryBuilder提供缓存功能，参考Laravel的设计：
    - remember() 方法缓存查询结果
    - forget() 方法清除缓存
    - flush() 方法清除标签缓存
    """

    def __init__(self):
        self._cache_ttl: int | None = None
        self._cache_key: str | None = None
        self._cache_tags: set[str] | None = None
        self._cache_driver: str | None = None
        self._should_cache: bool = False

    def remember(
        self,
        ttl: int = 300,
        key: str | None = None,
        tags: str | list[str] | set[str] | None = None,
    ) -> "QueryBuilder":
        """缓存查询结果

        参考Laravel的Cache::remember模式：

        Args:
            ttl: 缓存时间（秒）
            key: 自定义缓存键，不指定则自动生成
            tags: 缓存标签，支持字符串、列表或集合

        Returns:
            QueryBuilder实例，支持链式调用

        Example:
            # 基本用法
            users = await User.query().where('status', 'active').remember(3600).get()

            # 自定义键和标签
            users = await User.query().remember(
                ttl=1800,
                key='active_users',
                tags=['users', 'active']
            ).where('status', 'active').get()
        """
        self._should_cache = True
        self._cache_ttl = ttl
        self._cache_key = key

        # 标准化标签
        if tags is not None:
            if isinstance(tags, str):
                self._cache_tags = {tags}
            elif isinstance(tags, list):
                self._cache_tags = set(tags)
            else:
                self._cache_tags = set(tags)

        return self

    def forget(self, key: str | None = None) -> "QueryBuilder":
        """清除查询缓存

        Args:
            key: 要清除的缓存键，不指定则清除当前查询的缓存

        Returns:
            QueryBuilder实例

        Example:
            # 清除指定键的缓存
            User.query().forget('active_users')

            # 清除当前查询的缓存
            User.query().where('status', 'active').forget()
        """
        from fastorm.cache import cache

        if key:
            cache.delete(key)
        else:
            # 生成当前查询的缓存键并删除
            cache_key = self._generate_cache_key()
            cache.delete(cache_key)

        return self

    def flush(self, *tags: str) -> "QueryBuilder":
        """清除标签缓存

        Args:
            *tags: 要清除的标签列表

        Returns:
            QueryBuilder实例

        Example:
            # 清除用户相关的所有缓存
            User.query().flush('users', 'profiles')
        """
        from fastorm.cache import cache

        for tag in tags:
            cache.invalidate_tag(tag)

        return self

    def cache_for(self, ttl: int) -> "QueryBuilder":
        """设置缓存时间（语法糖）

        Args:
            ttl: 缓存时间（秒）

        Returns:
            QueryBuilder实例

        Example:
            users = await User.query().cache_for(3600).where('status', 'active').get()
        """
        return self.remember(ttl)

    def cache_forever(self) -> "QueryBuilder":
        """永久缓存（语法糖）

        Returns:
            QueryBuilder实例

        Example:
            settings = await Settings.query().cache_forever().get()
        """
        return self.remember(ttl=86400 * 365)  # 1年

    def dont_cache(self) -> "QueryBuilder":
        """禁用缓存

        Returns:
            QueryBuilder实例

        Example:
            # 强制不使用缓存
            users = await User.query().dont_cache().where('status', 'active').get()
        """
        self._should_cache = False
        return self

    async def _execute_with_cache(self, executor: Callable[[], Awaitable[T]]) -> T:
        """执行查询并处理缓存

        Args:
            executor: 执行查询的函数

        Returns:
            查询结果
        """
        if not self._should_cache:
            return await executor()

        from fastorm.cache import cache

        # 生成缓存键
        cache_key = self._cache_key or self._generate_cache_key()

        # 尝试从缓存获取
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"查询缓存命中: {cache_key}")
            return self._deserialize_result(cached_result)

        # 执行查询
        result = await executor()

        # 设置缓存
        serialized_result = self._serialize_result(result)
        await cache.set(
            key=cache_key,
            value=serialized_result,
            ttl=self._cache_ttl or 300,
            tags=self._cache_tags,
        )

        logger.debug(f"查询结果已缓存: {cache_key}")
        return result

    def _generate_cache_key(self) -> str:
        """生成查询缓存键

        基于查询条件、排序、限制等生成唯一键
        """
        # 获取模型类名
        model_name = getattr(self, "_model", {}).get("__name__", "query")

        # 构建查询标识
        query_parts = []

        # 添加WHERE条件
        if hasattr(self, "_wheres") and self._wheres:
            where_str = json.dumps(self._wheres, sort_keys=True, default=str)
            query_parts.append(
                f"where:{hashlib.md5(where_str.encode()).hexdigest()[:8]}"
            )

        # 添加ORDER BY
        if hasattr(self, "_orders") and self._orders:
            order_str = json.dumps(self._orders, sort_keys=True, default=str)
            query_parts.append(
                f"order:{hashlib.md5(order_str.encode()).hexdigest()[:8]}"
            )

        # 添加LIMIT和OFFSET
        if hasattr(self, "_limit") and self._limit:
            query_parts.append(f"limit:{self._limit}")

        if hasattr(self, "_offset") and self._offset:
            query_parts.append(f"offset:{self._offset}")

        # 添加SELECT字段
        if hasattr(self, "_columns") and self._columns:
            columns_str = json.dumps(sorted(self._columns), default=str)
            query_parts.append(
                f"select:{hashlib.md5(columns_str.encode()).hexdigest()[:8]}"
            )

        # 生成最终键
        query_signature = ":".join(query_parts)
        query_hash = hashlib.md5(query_signature.encode()).hexdigest()[:12]

        return f"fastorm:query:{model_name}:{query_hash}"

    def _serialize_result(self, result: Any) -> Any:
        """序列化查询结果"""
        if result is None:
            return None

        # 如果是模型实例列表
        if isinstance(result, list):
            return [self._serialize_model(item) for item in result]

        # 如果是单个模型实例
        if hasattr(result, "to_dict"):
            return self._serialize_model(result)

        # 其他类型直接返回
        return result

    def _serialize_model(self, model: Any) -> dict[str, Any]:
        """序列化单个模型实例"""
        if hasattr(model, "to_dict"):
            data = model.to_dict()
            data["__model_class__"] = model.__class__.__name__
            return data
        return model

    def _deserialize_result(self, cached_data: Any) -> Any:
        """反序列化查询结果"""
        if cached_data is None:
            return None

        # 如果是列表，反序列化每个项目
        if isinstance(cached_data, list):
            return [self._deserialize_model(item) for item in cached_data]

        # 如果是单个模型数据
        if isinstance(cached_data, dict) and "__model_class__" in cached_data:
            return self._deserialize_model(cached_data)

        # 其他类型直接返回
        return cached_data

    def _deserialize_model(self, model_data: Any) -> Any:
        """反序列化单个模型实例"""
        if not isinstance(model_data, dict) or "__model_class__" not in model_data:
            return model_data

        # 这里需要根据实际的模型系统来实现
        # 目前简化为返回字典数据
        data = model_data.copy()
        data.pop("__model_class__", None)
        return data


class CacheableQueryBuilder:
    """支持缓存的查询构建器基类

    提供查询缓存的核心功能，可以被具体的QueryBuilder类继承。
    """

    def __init__(self):
        self.cache_support = QueryCacheSupport()

    # 代理缓存相关方法
    def remember(
        self,
        ttl: int = 300,
        key: str | None = None,
        tags: str | list[str] | set[str] | None = None,
    ):
        self.cache_support.remember(ttl, key, tags)
        return self

    def forget(self, key: str | None = None):
        self.cache_support.forget(key)
        return self

    def flush(self, *tags: str):
        self.cache_support.flush(*tags)
        return self

    def cache_for(self, ttl: int):
        self.cache_support.cache_for(ttl)
        return self

    def cache_forever(self):
        self.cache_support.cache_forever()
        return self

    def dont_cache(self):
        self.cache_support.dont_cache()
        return self


# 为兼容性提供的快捷函数


def remember_query(
    key: str,
    ttl: int,
    query_func: Callable[[], Awaitable[T]],
    tags: set[str] | None = None,
) -> Awaitable[T]:
    """缓存查询结果的便捷函数

    参考Laravel的Cache::remember模式

    Args:
        key: 缓存键
        ttl: 缓存时间
        query_func: 查询函数
        tags: 缓存标签

    Returns:
        查询结果

    Example:
        users = await remember_query(
            key='active_users',
            ttl=3600,
            query_func=lambda: User.where('status', 'active').get(),
            tags={'users'}
        )
    """

    async def _execute():
        from fastorm.cache import cache

        # 尝试从缓存获取
        cached_result = await cache.get(key)
        if cached_result is not None:
            return cached_result

        # 执行查询
        result = await query_func()

        # 设置缓存
        await cache.set(key, result, ttl, tags)

        return result

    return _execute()


def forget_query(key: str) -> Awaitable[bool]:
    """清除查询缓存的便捷函数

    Args:
        key: 缓存键

    Returns:
        是否成功清除

    Example:
        await forget_query('active_users')
    """

    async def _execute():
        from fastorm.cache import cache

        return await cache.delete(key)

    return _execute()
