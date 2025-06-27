"""
FastORM 缓存管理器

提供统一的缓存管理接口。
"""

import hashlib
import logging
from typing import Any, Optional

from .backends import CacheBackend
from .backends import MemoryBackend
from .backends import RedisBackend

logger = logging.getLogger("fastorm.cache")


class CacheManager:
    """缓存管理器

    提供统一的缓存操作接口，支持多种后端。
    """

    _instance: Optional["CacheManager"] = None
    _backend: CacheBackend | None = None

    def __new__(cls) -> "CacheManager":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._backend is None:
            # 默认使用内存缓存
            self._backend = MemoryBackend()

    @classmethod
    def setup(cls, backend: str | CacheBackend, **config: Any) -> None:
        """设置缓存后端

        Args:
            backend: 后端类型("memory", "redis")或后端实例
            **config: 后端配置参数
        """
        if isinstance(backend, str):
            if backend.lower() == "memory":
                max_size = config.get("max_size", 1000)
                cls._backend = MemoryBackend(max_size=max_size)
            elif backend.lower() == "redis":
                redis_url = config.get("redis_url", "redis://localhost:6379/0")
                prefix = config.get("prefix", "fastorm:")
                cls._backend = RedisBackend(redis_url=redis_url, prefix=prefix)
            else:
                raise ValueError(f"Unsupported backend: {backend}")
        elif isinstance(backend, CacheBackend):
            cls._backend = backend
        else:
            raise TypeError("Backend must be string or CacheBackend instance")

        logger.info(f"缓存后端设置为: {type(cls._backend).__name__}")

    @classmethod
    def get_backend(cls) -> CacheBackend:
        """获取当前缓存后端"""
        if cls._backend is None:
            cls._backend = MemoryBackend()
        return cls._backend

    @staticmethod
    def generate_key(
        prefix: str,
        query: str = "",
        params: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> str:
        """生成缓存键

        Args:
            prefix: 键前缀
            query: 查询字符串
            params: 查询参数
            model: 模型名称

        Returns:
            生成的缓存键
        """
        parts = [prefix]

        if model:
            parts.append(f"model:{model}")

        if query:
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            parts.append(f"query:{query_hash}")

        if params:
            # 将参数转换为确定性字符串
            param_str = str(sorted(params.items()))
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            parts.append(f"params:{param_hash}")

        return ":".join(parts)

    async def get(self, key: str) -> Any | None:
        """获取缓存值"""
        backend = self.get_backend()
        return await backend.get(key)

    async def set(
        self, key: str, value: Any, ttl: int = 300, tags: set[str] | None = None
    ) -> bool:
        """设置缓存值"""
        backend = self.get_backend()
        return await backend.set(key, value, ttl, tags)

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        backend = self.get_backend()
        return await backend.delete(key)

    async def clear(self) -> bool:
        """清空所有缓存"""
        backend = self.get_backend()
        return await backend.clear()

    async def invalidate_tag(self, tag: str) -> int:
        """根据标签失效缓存"""
        backend = self.get_backend()
        return await backend.invalidate_tag(tag)

    async def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        backend = self.get_backend()
        if hasattr(backend, "get_stats"):
            return await backend.get_stats()
        return {"backend": type(backend).__name__}


# 全局缓存管理器实例
cache = CacheManager()
