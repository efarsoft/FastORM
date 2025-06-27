"""
FastORM 缓存后端实现

支持内存缓存和Redis缓存。
"""

import pickle
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set, List
from dataclasses import dataclass

logger = logging.getLogger("fastorm.cache")


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    expires_at: float
    tags: Optional[Set[str]] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at


class CacheBackend(ABC):
    """缓存后端抽象基类"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod 
    async def set(self, key: str, value: Any, ttl: int = 300, tags: Optional[Set[str]] = None) -> bool:
        """设置缓存值"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """清空所有缓存"""
        pass
    
    @abstractmethod
    async def invalidate_tag(self, tag: str) -> int:
        """根据标签失效缓存"""
        pass


class MemoryBackend(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._tag_mappings: Dict[str, Set[str]] = {}  # tag -> keys
        self._key_tags: Dict[str, Set[str]] = {}      # key -> tags
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            await self.delete(key)
            return None
        
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: int = 300, tags: Optional[Set[str]] = None) -> bool:
        """设置缓存值"""
        # 检查容量限制
        if len(self._cache) >= self.max_size and key not in self._cache:
            # 清理过期条目
            await self._cleanup_expired()
            
            # 如果仍然超出限制，删除最旧的条目
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].expires_at)
                await self.delete(oldest_key)
        
        # 删除旧的标签映射
        if key in self._key_tags:
            old_tags = self._key_tags[key]
            for tag in old_tags:
                if tag in self._tag_mappings:
                    self._tag_mappings[tag].discard(key)
                    if not self._tag_mappings[tag]:
                        del self._tag_mappings[tag]
            del self._key_tags[key]
        
        # 创建缓存条目
        expires_at = time.time() + ttl
        entry = CacheEntry(value=value, expires_at=expires_at, tags=tags)
        self._cache[key] = entry
        
        # 设置标签映射
        if tags:
            self._key_tags[key] = tags
            for tag in tags:
                if tag not in self._tag_mappings:
                    self._tag_mappings[tag] = set()
                self._tag_mappings[tag].add(key)
        
        return True
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key not in self._cache:
            return False
        
        # 删除缓存条目
        del self._cache[key]
        
        # 删除标签映射
        if key in self._key_tags:
            tags = self._key_tags[key]
            for tag in tags:
                if tag in self._tag_mappings:
                    self._tag_mappings[tag].discard(key)
                    if not self._tag_mappings[tag]:
                        del self._tag_mappings[tag]
            del self._key_tags[key]
        
        return True
    
    async def clear(self) -> bool:
        """清空所有缓存"""
        self._cache.clear()
        self._tag_mappings.clear()
        self._key_tags.clear()
        return True
    
    async def invalidate_tag(self, tag: str) -> int:
        """根据标签失效缓存"""
        if tag not in self._tag_mappings:
            return 0
        
        keys_to_delete = self._tag_mappings[tag].copy()
        count = 0
        
        for key in keys_to_delete:
            if await self.delete(key):
                count += 1
        
        return count
    
    async def _cleanup_expired(self) -> None:
        """清理过期条目"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            await self.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "backend": "memory",
            "total_keys": len(self._cache),
            "max_size": self.max_size,
            "tags_count": len(self._tag_mappings)
        }


class RedisBackend(CacheBackend):
    """Redis缓存后端"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", prefix: str = "fastorm:"):
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis = None
        self._connected = False
    
    async def _ensure_connection(self) -> bool:
        """确保Redis连接"""
        if self._connected and self._redis:
            return True
        
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url, decode_responses=False)
            await self._redis.ping()
            self._connected = True
            logger.info("Redis缓存连接成功")
            return True
        except ImportError:
            logger.error("Redis依赖未安装，请运行: pip install redis")
            return False
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.prefix}{key}"
    
    def _make_tag_key(self, tag: str) -> str:
        """生成标签键"""
        return f"{self.prefix}tag:{tag}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not await self._ensure_connection():
            return None
        
        try:
            redis_key = self._make_key(key)
            data = await self._redis.get(redis_key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis获取缓存失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300, tags: Optional[Set[str]] = None) -> bool:
        """设置缓存值"""
        if not await self._ensure_connection():
            return False
        
        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(value)
            
            # 设置缓存值
            await self._redis.setex(redis_key, ttl, data)
            
            # 设置标签映射
            if tags:
                for tag in tags:
                    tag_key = self._make_tag_key(tag)
                    await self._redis.sadd(tag_key, key)
                    await self._redis.expire(tag_key, ttl)
            
            return True
        except Exception as e:
            logger.warning(f"Redis设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        if not await self._ensure_connection():
            return False
        
        try:
            redis_key = self._make_key(key)
            result = await self._redis.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis删除缓存失败: {e}")
            return False
    
    async def clear(self) -> bool:
        """清空所有缓存"""
        if not await self._ensure_connection():
            return False
        
        try:
            # 获取所有匹配前缀的键
            pattern = f"{self.prefix}*"
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._redis.delete(*keys)
            
            return True
        except Exception as e:
            logger.warning(f"Redis清空缓存失败: {e}")
            return False
    
    async def invalidate_tag(self, tag: str) -> int:
        """根据标签失效缓存"""
        if not await self._ensure_connection():
            return 0
        
        try:
            tag_key = self._make_tag_key(tag)
            
            # 获取标签下的所有键
            keys = await self._redis.smembers(tag_key)
            if not keys:
                return 0
            
            # 删除缓存条目
            redis_keys = [self._make_key(key.decode()) for key in keys]
            await self._redis.delete(*redis_keys)
            
            # 删除标签索引
            await self._redis.delete(tag_key)
            
            return len(keys)
        except Exception as e:
            logger.warning(f"Redis标签失效失败: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if not await self._ensure_connection():
            return {"backend": "redis", "connected": False}
        
        try:
            info = await self._redis.info()
            return {
                "backend": "redis",
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {"backend": "redis", "connected": True, "error": str(e)} 