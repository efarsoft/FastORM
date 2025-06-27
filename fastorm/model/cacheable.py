"""
FastORM 模型缓存支持

参考Laravel Eloquent模型的缓存设计，
为模型提供内建的缓存功能。
"""

import logging
from typing import Any, TypeVar

logger = logging.getLogger("fastorm.cache")

T = TypeVar("T", bound="CacheableModel")


class CacheableModel:
    """支持缓存的模型混入类

    参考Laravel Eloquent的设计模式，
    直接在模型中提供缓存功能。
    """

    # 类级别的缓存配置
    _cache_ttl: int = 300  # 默认5分钟
    _cache_tags: set[str] | None = None
    _cache_prefix: str | None = None

    @classmethod
    def cache_for(cls, ttl: int) -> "ModelQueryBuilder":
        """设置缓存时间

        Args:
            ttl: 缓存时间（秒）

        Returns:
            ModelQueryBuilder实例

        Example:
            users = await User.cache_for(3600).where('status', 'active').get()
        """
        return cls.query().remember(ttl)

    @classmethod
    def cache_forever(cls) -> "ModelQueryBuilder":
        """永久缓存

        Returns:
            ModelQueryBuilder实例

        Example:
            settings = await Settings.cache_forever().all()
        """
        return cls.query().remember(ttl=86400 * 365)

    @classmethod
    def remember(
        cls, key: str, ttl: int = 300, tags: str | list[str] | set[str] | None = None
    ) -> "ModelQueryBuilder":
        """使用指定键缓存查询

        参考Laravel的Cache::remember模式

        Args:
            key: 缓存键
            ttl: 缓存时间
            tags: 缓存标签

        Returns:
            ModelQueryBuilder实例

        Example:
            users = await User.remember('active_users', 3600).where('status', 'active').get()
        """
        return cls.query().remember(ttl=ttl, key=key, tags=tags)

    @classmethod
    async def forget_cache(cls, key: str) -> bool:
        """清除指定的缓存

        Args:
            key: 缓存键

        Returns:
            是否成功清除

        Example:
            await User.forget_cache('active_users')
        """
        from fastorm.cache import cache

        return await cache.delete(key)

    @classmethod
    async def flush_cache(cls, *tags: str) -> None:
        """清除标签缓存

        Args:
            *tags: 要清除的标签

        Example:
            await User.flush_cache('users', 'profiles')
        """
        from fastorm.cache import cache

        for tag in tags:
            await cache.invalidate_tag(tag)

    @classmethod
    async def cache_key_for_id(cls, id: Any) -> str:
        """为指定ID生成缓存键

        Args:
            id: 记录ID

        Returns:
            缓存键
        """
        model_name = cls.__name__.lower()
        prefix = cls._cache_prefix or "fastorm"
        return f"{prefix}:model:{model_name}:{id}"

    @classmethod
    async def cache_key_for_query(cls, **conditions) -> str:
        """为查询条件生成缓存键

        Args:
            **conditions: 查询条件

        Returns:
            缓存键
        """
        import hashlib
        import json

        model_name = cls.__name__.lower()
        prefix = cls._cache_prefix or "fastorm"

        # 生成条件哈希
        conditions_str = json.dumps(conditions, sort_keys=True, default=str)
        conditions_hash = hashlib.md5(conditions_str.encode()).hexdigest()[:8]

        return f"{prefix}:query:{model_name}:{conditions_hash}"

    async def cache_instance(self, ttl: int | None = None) -> None:
        """缓存当前模型实例

        Args:
            ttl: 缓存时间，不指定使用类默认值

        Example:
            user = await User.find(1)
            await user.cache_instance(3600)
        """
        if not hasattr(self, "id") or self.id is None:
            logger.warning("无法缓存没有ID的模型实例")
            return

        from fastorm.cache import cache

        cache_key = await self.cache_key_for_id(self.id)
        cache_ttl = ttl or self._cache_ttl

        # 获取模型标签
        tags = self._get_cache_tags()

        # 缓存实例数据
        instance_data = self.to_dict() if hasattr(self, "to_dict") else {}
        instance_data["__model_class__"] = self.__class__.__name__

        await cache.set(cache_key, instance_data, cache_ttl, tags)
        logger.debug(f"模型实例已缓存: {cache_key}")

    async def forget_instance_cache(self) -> bool:
        """清除当前实例的缓存

        Returns:
            是否成功清除

        Example:
            user = await User.find(1)
            await user.forget_instance_cache()
        """
        if not hasattr(self, "id") or self.id is None:
            return False

        from fastorm.cache import cache

        cache_key = await self.cache_key_for_id(self.id)
        return await cache.delete(cache_key)

    @classmethod
    async def find_cached(cls: type[T], id: Any) -> T | None:
        """从缓存中查找模型实例

        Args:
            id: 记录ID

        Returns:
            模型实例或None

        Example:
            user = await User.find_cached(1)
            if user is None:
                user = await User.find(1)
                await user.cache_instance()
        """
        from fastorm.cache import cache

        cache_key = await cls.cache_key_for_id(id)
        cached_data = await cache.get(cache_key)

        if cached_data is None:
            return None

        # 反序列化模型实例
        return cls._deserialize_instance(cached_data)

    @classmethod
    async def find_or_cache(cls: type[T], id: Any, ttl: int | None = None) -> T | None:
        """查找模型实例，如果不在缓存中则查询并缓存

        参考Laravel的Cache::remember模式

        Args:
            id: 记录ID
            ttl: 缓存时间

        Returns:
            模型实例或None

        Example:
            user = await User.find_or_cache(1, ttl=3600)
        """
        # 先尝试从缓存获取
        cached_instance = await cls.find_cached(id)
        if cached_instance is not None:
            logger.debug(f"从缓存获取模型实例: {cls.__name__}#{id}")
            return cached_instance

        # 从数据库查询
        instance = await cls.find(id)
        if instance is not None:
            # 缓存实例
            await instance.cache_instance(ttl)
            logger.debug(f"查询并缓存模型实例: {cls.__name__}#{id}")

        return instance

    def _get_cache_tags(self) -> set[str] | None:
        """获取模型的缓存标签

        Returns:
            缓存标签集合
        """
        tags = set()

        # 添加类级别标签
        if self._cache_tags:
            tags.update(self._cache_tags)

        # 添加模型名称标签
        tags.add(self.__class__.__name__.lower())

        # 如果有ID，添加实例标签
        if hasattr(self, "id") and self.id is not None:
            tags.add(f"{self.__class__.__name__.lower()}:{self.id}")

        return tags if tags else None

    @classmethod
    def _deserialize_instance(cls: type[T], cached_data: dict[str, Any]) -> T | None:
        """反序列化缓存的模型实例

        Args:
            cached_data: 缓存的数据

        Returns:
            模型实例或None
        """
        if not isinstance(cached_data, dict):
            return None

        # 验证模型类型
        model_class = cached_data.get("__model_class__")
        if model_class != cls.__name__:
            logger.warning(
                f"缓存数据类型不匹配: 期望 {cls.__name__}, 实际 {model_class}"
            )
            return None

        # 移除元数据
        instance_data = cached_data.copy()
        instance_data.pop("__model_class__", None)

        # 创建实例（这里需要根据实际的模型构造方式调整）
        try:
            # 简化的实例创建，实际应该根据模型系统调整
            instance = cls(**instance_data)
            return instance
        except Exception as e:
            logger.error(f"反序列化模型实例失败: {e}")
            return None


class CacheableModelMixin:
    """模型缓存混入类

    可以与现有的Model类组合使用
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # 自动设置缓存标签
        if not hasattr(cls, "_cache_tags") or cls._cache_tags is None:
            cls._cache_tags = {cls.__name__.lower()}

        # 设置缓存前缀
        if not hasattr(cls, "_cache_prefix") or cls._cache_prefix is None:
            cls._cache_prefix = "fastorm"


# 缓存辅助函数


async def cache_model_query(
    model_class,
    query_method: str,
    key: str,
    ttl: int = 300,
    tags: set[str] | None = None,
    *args,
    **kwargs,
) -> Any:
    """缓存模型查询的通用函数

    Args:
        model_class: 模型类
        query_method: 查询方法名
        key: 缓存键
        ttl: 缓存时间
        tags: 缓存标签
        *args: 查询方法的位置参数
        **kwargs: 查询方法的关键字参数

    Returns:
        查询结果

    Example:
        users = await cache_model_query(
            User,
            'where',
            'active_users',
            3600,
            {'users'},
            'status', 'active'
        )
    """
    from fastorm.cache import cache

    # 尝试从缓存获取
    cached_result = await cache.get(key)
    if cached_result is not None:
        logger.debug(f"模型查询缓存命中: {key}")
        return cached_result

    # 执行查询
    query_func = getattr(model_class, query_method)
    result = await query_func(*args, **kwargs)

    # 缓存结果
    await cache.set(key, result, ttl, tags)
    logger.debug(f"模型查询结果已缓存: {key}")

    return result


async def invalidate_model_cache(
    model_class, instance_id: Any | None = None, tags: list[str] | None = None
) -> None:
    """失效模型缓存

    Args:
        model_class: 模型类
        instance_id: 实例ID，指定则清除该实例的缓存
        tags: 要清除的标签列表

    Example:
        # 清除特定实例缓存
        await invalidate_model_cache(User, instance_id=1)

        # 清除标签缓存
        await invalidate_model_cache(User, tags=['users', 'profiles'])
    """
    from fastorm.cache import cache

    if instance_id is not None:
        # 清除实例缓存
        cache_key = await model_class.cache_key_for_id(instance_id)
        await cache.delete(cache_key)
        logger.debug(f"已清除模型实例缓存: {model_class.__name__}#{instance_id}")

    if tags:
        # 清除标签缓存
        for tag in tags:
            count = await cache.invalidate_tag(tag)
            logger.debug(f"已清除标签缓存 {tag}: {count} 个条目")
