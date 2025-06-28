"""
FastORM 缓存功能测试

测试缓存系统的性能优化功能：
- 缓存管理器
- 内存缓存后端
- Redis缓存后端
- 缓存装饰器
- 查询缓存
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock
from sqlalchemy import Column, Integer, String

from fastorm.model.model import Model
from fastorm.cache import (
    CacheManager,
    MemoryBackend,
    RedisBackend,
    cache,
    setup_cache,
    get_cache,
    remember,
    forget,
    flush,
)
from fastorm.cache.backends import CacheEntry


# =================================================================
# 测试模型定义
# =================================================================

class CacheTestUser(Model):
    """缓存测试用户模型"""
    __tablename__ = 'cache_test_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True)
    status = Column(String(20), default='active')


# =================================================================
# 测试用例
# =================================================================

class TestCacheManager:
    """缓存管理器测试类"""
    
    @pytest.fixture(autouse=True)
    async def setup_cache_manager(self):
        """设置缓存管理器"""
        # 为每个测试创建新的缓存管理器
        CacheManager._instance = None
        CacheManager._backend = None
        
    @pytest.mark.asyncio
    async def test_cache_manager_singleton(self):
        """测试缓存管理器单例模式"""
        manager1 = CacheManager()
        manager2 = CacheManager()
        
        assert manager1 is manager2
        assert CacheManager._instance is manager1
    
    @pytest.mark.asyncio
    async def test_cache_manager_setup_memory(self):
        """测试内存缓存后端设置"""
        manager = CacheManager()
        manager.setup("memory", max_size=500)
        
        backend = manager.get_backend()
        assert isinstance(backend, MemoryBackend)
        assert backend.max_size == 500
    
    @pytest.mark.asyncio
    async def test_cache_manager_setup_invalid_backend(self):
        """测试无效缓存后端设置"""
        manager = CacheManager()
        
        with pytest.raises(ValueError, match="Unsupported backend"):
            manager.setup("invalid_backend")
    
    @pytest.mark.asyncio
    async def test_cache_manager_basic_operations(self):
        """测试缓存管理器基本操作"""
        manager = CacheManager()
        manager.setup("memory")
        
        # 测试设置和获取
        success = await manager.set("test_key", "test_value", ttl=60)
        assert success is True
        
        value = await manager.get("test_key")
        assert value == "test_value"
        
        # 测试删除
        deleted = await manager.delete("test_key")
        assert deleted is True
        
        # 验证删除后无法获取
        value = await manager.get("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_manager_key_generation(self):
        """测试缓存键生成"""
        # 测试基本键生成
        key1 = CacheManager.generate_key("prefix", "SELECT * FROM users")
        assert key1.startswith("prefix:")
        assert "query:" in key1
        
        # 测试带参数的键生成
        key2 = CacheManager.generate_key(
            "prefix", 
            "SELECT * FROM users WHERE id = ?",
            {"id": 1},
            "User"
        )
        assert "model:User" in key2
        assert "params:" in key2
        
        # 相同参数应该生成相同的键
        key3 = CacheManager.generate_key(
            "prefix",
            "SELECT * FROM users WHERE id = ?", 
            {"id": 1},
            "User"
        )
        assert key2 == key3


class TestMemoryBackend:
    """内存缓存后端测试类"""
    
    @pytest.fixture
    def memory_backend(self):
        """创建内存缓存后端"""
        return MemoryBackend(max_size=100)
    
    @pytest.mark.asyncio
    async def test_memory_backend_basic_operations(self, memory_backend):
        """测试内存后端基本操作"""
        # 测试设置和获取
        success = await memory_backend.set("key1", "value1", ttl=60)
        assert success is True
        
        value = await memory_backend.get("key1")
        assert value == "value1"
        
        # 测试删除
        deleted = await memory_backend.delete("key1")
        assert deleted is True
        
        value = await memory_backend.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_memory_backend_ttl_expiration(self, memory_backend):
        """测试TTL过期功能"""
        # 设置短TTL的缓存
        await memory_backend.set("expire_key", "expire_value", ttl=1)
        
        # 立即获取应该成功
        value = await memory_backend.get("expire_key")
        assert value == "expire_value"
        
        # 等待过期
        await asyncio.sleep(1.1)
        
        # 过期后应该返回None
        value = await memory_backend.get("expire_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_memory_backend_tags(self, memory_backend):
        """测试标签功能"""
        # 设置带标签的缓存
        await memory_backend.set("user1", "Alice", ttl=60, tags={"users", "active"})
        await memory_backend.set("user2", "Bob", ttl=60, tags={"users"})
        await memory_backend.set("post1", "Hello", ttl=60, tags={"posts"})
        
        # 验证缓存存在
        assert await memory_backend.get("user1") == "Alice"
        assert await memory_backend.get("user2") == "Bob"
        assert await memory_backend.get("post1") == "Hello"
        
        # 按标签失效缓存
        count = await memory_backend.invalidate_tag("users")
        assert count == 2
        
        # 验证users标签的缓存已失效
        assert await memory_backend.get("user1") is None
        assert await memory_backend.get("user2") is None
        
        # 验证其他标签的缓存仍然存在
        assert await memory_backend.get("post1") == "Hello"
    
    @pytest.mark.asyncio
    async def test_memory_backend_max_size(self):
        """测试最大容量限制"""
        backend = MemoryBackend(max_size=3)
        
        # 填满缓存
        await backend.set("key1", "value1", ttl=60)
        await backend.set("key2", "value2", ttl=60)
        await backend.set("key3", "value3", ttl=60)
        
        # 验证所有键都存在
        assert await backend.get("key1") == "value1"
        assert await backend.get("key2") == "value2"
        assert await backend.get("key3") == "value3"
        
        # 添加第四个键，应该删除最旧的
        await backend.set("key4", "value4", ttl=60)
        
        # 验证最旧的键被删除
        assert await backend.get("key1") is None
        assert await backend.get("key4") == "value4"
    
    @pytest.mark.asyncio
    async def test_memory_backend_clear(self, memory_backend):
        """测试清空缓存"""
        # 添加一些缓存
        await memory_backend.set("key1", "value1", ttl=60)
        await memory_backend.set("key2", "value2", ttl=60, tags={"test"})
        
        # 验证缓存存在
        assert await memory_backend.get("key1") == "value1"
        assert await memory_backend.get("key2") == "value2"
        
        # 清空缓存
        success = await memory_backend.clear()
        assert success is True
        
        # 验证所有缓存都被清除
        assert await memory_backend.get("key1") is None
        assert await memory_backend.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_memory_backend_stats(self, memory_backend):
        """测试缓存统计"""
        # 添加一些缓存
        await memory_backend.set("key1", "value1", ttl=60, tags={"tag1"})
        await memory_backend.set("key2", "value2", ttl=60, tags={"tag2"})
        
        stats = memory_backend.get_stats()
        
        assert stats["backend"] == "memory"
        assert stats["total_keys"] == 2
        assert stats["max_size"] == 100
        assert stats["tags_count"] == 2


class TestCacheEntry:
    """缓存条目测试类"""
    
    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry(
            value="test_value",
            expires_at=time.time() + 60,
            tags={"test"}
        )
        
        assert entry.value == "test_value"
        assert entry.tags == {"test"}
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """测试缓存条目过期"""
        # 创建已过期的条目
        entry = CacheEntry(
            value="test_value",
            expires_at=time.time() - 1  # 1秒前过期
        )
        
        assert entry.is_expired()


class TestCacheUtilityFunctions:
    """缓存工具函数测试类"""
    
    @pytest.fixture(autouse=True)
    async def setup_test_cache(self):
        """设置测试缓存"""
        setup_cache("memory", max_size=100)
    
    @pytest.mark.asyncio
    async def test_setup_cache_function(self):
        """测试setup_cache函数"""
        manager = setup_cache("memory", max_size=200)
        
        assert isinstance(manager, CacheManager)
        backend = manager.get_backend()
        assert isinstance(backend, MemoryBackend)
        assert backend.max_size == 200
    
    @pytest.mark.asyncio
    async def test_get_cache_function(self):
        """测试get_cache函数"""
        manager = get_cache()
        
        assert isinstance(manager, CacheManager)
    
    @pytest.mark.asyncio
    async def test_remember_function(self):
        """测试remember函数"""
        call_count = 0
        
        def expensive_operation():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        # 第一次调用应该执行函数
        result1 = await remember("test_key", 60, expensive_operation, {"test"})
        assert result1 == "result_1"
        assert call_count == 1
        
        # 第二次调用应该从缓存获取
        result2 = await remember("test_key", 60, expensive_operation, {"test"})
        assert result2 == "result_1"  # 相同的结果
        assert call_count == 1  # 函数没有再次调用
    
    @pytest.mark.asyncio
    async def test_remember_function_async_callback(self):
        """测试remember函数与异步回调"""
        call_count = 0
        
        async def async_expensive_operation():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # 模拟异步操作
            return f"async_result_{call_count}"
        
        # 测试异步回调
        result = await remember("async_key", 60, async_expensive_operation)
        assert result == "async_result_1"
        assert call_count == 1
        
        # 再次调用应该从缓存获取
        result2 = await remember("async_key", 60, async_expensive_operation)
        assert result2 == "async_result_1"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_forget_function(self):
        """测试forget函数"""
        # 先设置一个缓存
        cache_manager = get_cache()
        await cache_manager.set("forget_key", "forget_value", 60)
        
        # 验证缓存存在
        value = await cache_manager.get("forget_key")
        assert value == "forget_value"
        
        # 删除缓存
        success = await forget("forget_key")
        assert success is True
        
        # 验证缓存已删除
        value = await cache_manager.get("forget_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_flush_function(self):
        """测试flush函数"""
        cache_manager = get_cache()
        
        # 设置带不同标签的缓存
        await cache_manager.set("key1", "value1", 60, {"tag1", "common"})
        await cache_manager.set("key2", "value2", 60, {"tag2", "common"})
        await cache_manager.set("key3", "value3", 60, {"tag3"})
        
        # 按标签清除缓存
        count = await flush("tag1", "tag2")
        assert count == 2
        
        # 验证相应的缓存已清除
        assert await cache_manager.get("key1") is None
        assert await cache_manager.get("key2") is None
        
        # 验证其他缓存仍然存在
        assert await cache_manager.get("key3") == "value3"


class TestCacheIntegration:
    """缓存集成测试类"""
    
    @pytest.mark.asyncio
    async def test_cache_with_model_operations(self, test_database):
        """测试缓存与模型操作的集成"""
        setup_cache("memory")
        
        # 创建测试用户
        user = CacheTestUser(name="Cache User", email="cache@example.com")
        await user.save()
        
        # 模拟查询缓存
        cache_key = f"user:{user.id}"
        cache_manager = get_cache()
        
        # 缓存用户数据
        await cache_manager.set(cache_key, user.to_dict(), ttl=300, tags={"users"})
        
        # 从缓存获取数据
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is not None
        assert cached_data["name"] == "Cache User"
        assert cached_data["email"] == "cache@example.com"
        
        # 测试标签失效
        count = await cache_manager.invalidate_tag("users")
        assert count == 1
        
        # 验证缓存已失效
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is None 