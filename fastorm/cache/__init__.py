"""
FastORM 缓存模块

参考Laravel和ThinkORM的设计，提供完整的缓存解决方案：
- 后端支持：内存、Redis
- 查询缓存：直接集成到QueryBuilder
- 模型缓存：模型级别的缓存支持
- 装饰器：便捷的函数缓存
"""

from .manager import CacheManager
from .decorators import (
    cache_query, 
    invalidate_cache, 
    cache_method, 
    cache_property, 
    conditional_cache
)
from .backends import MemoryBackend, RedisBackend

# 导入查询缓存集成
try:
    from .cache import (
        QueryCacheSupport,
        CacheableQueryBuilder,
        remember_query,
        forget_query
    )
except ImportError:
    # 如果查询模块不存在，忽略导入错误
    QueryCacheSupport = None
    CacheableQueryBuilder = None
    remember_query = None
    forget_query = None

# 导入模型缓存集成
try:
    from .cacheable import (
        CacheableModel,
        CacheableModelMixin,
        cache_model_query,
        invalidate_model_cache
    )
except ImportError:
    # 如果模型模块不存在，忽略导入错误
    CacheableModel = None
    CacheableModelMixin = None
    cache_model_query = None
    invalidate_model_cache = None

# 全局缓存管理器实例
cache = CacheManager()

__all__ = [
    # 核心组件
    "CacheManager",
    "cache",
    
    # 后端
    "MemoryBackend",
    "RedisBackend",
    
    # 装饰器
    "cache_query", 
    "invalidate_cache",
    "cache_method",
    "cache_property", 
    "conditional_cache",
    
    # 查询缓存集成
    "QueryCacheSupport",
    "CacheableQueryBuilder", 
    "remember_query",
    "forget_query",
    
    # 模型缓存集成
    "CacheableModel",
    "CacheableModelMixin",
    "cache_model_query",
    "invalidate_model_cache",
]


def setup_cache(
    backend: str = "memory",
    **config
) -> CacheManager:
    """设置缓存系统
    
    Args:
        backend: 缓存后端类型 ('memory' 或 'redis')
        **config: 后端配置参数
        
    Returns:
        配置好的缓存管理器
        
    Example:
        # 内存缓存
        setup_cache("memory", max_size=5000)
        
        # Redis缓存  
        setup_cache("redis", redis_url="redis://localhost:6379/0")
    """
    cache.setup(backend, **config)
    return cache


def get_cache() -> CacheManager:
    """获取全局缓存管理器实例
    
    Returns:
        缓存管理器
    """
    return cache


# Laravel风格的便捷函数

async def remember(
    key: str,
    ttl: int,
    callback,
    tags: set = None
):
    """Laravel风格的remember函数
    
    Args:
        key: 缓存键
        ttl: 缓存时间
        callback: 回调函数（同步或异步）
        tags: 缓存标签
        
    Returns:
        缓存的值或回调函数结果
        
    Example:
        # 缓存数据库查询
        users = await remember(
            'active_users', 
            3600,
            lambda: User.where('status', 'active').get(),
            {'users'}
        )
    """
    # 尝试从缓存获取
    cached_value = await cache.get(key)
    if cached_value is not None:
        return cached_value
    
    # 执行回调函数
    if asyncio.iscoroutinefunction(callback):
        value = await callback()
    else:
        value = callback()
    
    # 设置缓存
    await cache.set(key, value, ttl, tags)
    
    return value


async def forget(key: str) -> bool:
    """Laravel风格的forget函数
    
    Args:
        key: 缓存键
        
    Returns:
        是否成功删除
        
    Example:
        await forget('active_users')
    """
    return await cache.delete(key)


async def flush(*tags: str) -> int:
    """清除标签缓存
    
    Args:
        *tags: 标签列表
        
    Returns:
        清除的条目数量
        
    Example:
        count = await flush('users', 'posts')
    """
    total_count = 0
    for tag in tags:
        count = await cache.invalidate_tag(tag)
        total_count += count
    return total_count


# 为了兼容性，导入asyncio
import asyncio 