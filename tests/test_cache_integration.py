"""
FastORM 缓存集成测试

测试缓存系统的各个组件和集成功能。
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


@pytest.fixture
async def cache_manager():
    """缓存管理器fixture"""
    from fastorm.cache import CacheManager
    
    manager = CacheManager()
    await manager.setup("memory", max_size=100)
    yield manager
    await manager.clear()


@pytest.fixture
async def mock_model():
    """模拟模型fixture"""
    class MockUser:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def to_dict(self):
            return {k: v for k, v in self.__dict__.items() 
                   if not k.startswith('_')}
        
        @classmethod
        async def find(cls, id: int):
            await asyncio.sleep(0.01)  # 模拟查询延迟
            return cls(id=id, name=f"User {id}", status="active")
    
    return MockUser


class TestCacheManager:
    """缓存管理器测试"""
    
    async def test_basic_operations(self, cache_manager):
        """测试基础缓存操作"""
        # 设置缓存
        await cache_manager.set("test_key", "test_value", ttl=60)
        
        # 获取缓存
        value = await cache_manager.get("test_key")
        assert value == "test_value"
        
        # 删除缓存
        result = await cache_manager.delete("test_key")
        assert result is True
        
        # 确认已删除
        value = await cache_manager.get("test_key")
        assert value is None
    
    async def test_tags_functionality(self, cache_manager):
        """测试标签功能"""
        # 设置带标签的缓存
        await cache_manager.set("user:1", {"id": 1}, ttl=300, 
                               tags={'users', 'user:1'})
        await cache_manager.set("user:2", {"id": 2}, ttl=300, 
                               tags={'users', 'user:2'})
        await cache_manager.set("product:1", {"id": 1}, ttl=300, 
                               tags={'products'})
        
        # 清除用户标签
        count = await cache_manager.invalidate_tag('users')
        assert count == 2
        
        # 确认用户缓存已清除
        assert await cache_manager.get("user:1") is None
        assert await cache_manager.get("user:2") is None
        
        # 确认产品缓存仍存在
        assert await cache_manager.get("product:1") is not None
    
    async def test_ttl_expiration(self, cache_manager):
        """测试TTL过期"""
        # 设置短TTL的缓存
        await cache_manager.set("short_lived", "value", ttl=1)
        
        # 立即检查存在
        value = await cache_manager.get("short_lived")
        assert value == "value"
        
        # 等待过期
        await asyncio.sleep(1.1)
        
        # 清理过期项目
        await cache_manager.cleanup_expired()
        
        # 确认已过期
        value = await cache_manager.get("short_lived")
        assert value is None


class TestLaravelStyleCache:
    """Laravel风格缓存测试"""
    
    async def test_remember_function(self, cache_manager):
        """测试remember函数"""
        from fastorm.cache import remember
        
        call_count = 0
        
        async def expensive_operation():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"result": "data", "call": call_count}
        
        # 第一次调用
        result1 = await remember("test_operation", 60, expensive_operation)
        assert result1["call"] == 1
        assert call_count == 1
        
        # 第二次调用（应该从缓存获取）
        result2 = await remember("test_operation", 60, expensive_operation)
        assert result2["call"] == 1  # 同样的结果
        assert call_count == 1  # 没有再次调用
    
    async def test_forget_function(self, cache_manager):
        """测试forget函数"""
        from fastorm.cache import remember, forget
        
        async def test_operation():
            return "test_result"
        
        # 设置缓存
        result = await remember("forget_test", 60, test_operation)
        assert result == "test_result"
        
        # 清除缓存
        success = await forget("forget_test")
        assert success is True
        
        # 确认已清除
        cached_value = await cache_manager.get("forget_test")
        assert cached_value is None


class TestDecoratorCache:
    """装饰器缓存测试"""
    
    async def test_cache_query_decorator(self, cache_manager):
        """测试cache_query装饰器"""
        from fastorm.cache.decorators import cache_query
        
        call_count = 0
        
        @cache_query(ttl=60, tags={'test'})
        async def test_function(x: int, y: int) -> dict:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"result": x + y, "call": call_count}
        
        # 第一次调用
        result1 = await test_function(1, 2)
        assert result1["result"] == 3
        assert result1["call"] == 1
        assert call_count == 1
        
        # 第二次调用（相同参数）
        result2 = await test_function(1, 2)
        assert result2["result"] == 3
        assert result2["call"] == 1  # 缓存结果
        assert call_count == 1  # 没有再次调用
        
        # 第三次调用（不同参数）
        result3 = await test_function(3, 4)
        assert result3["result"] == 7
        assert result3["call"] == 2  # 新的调用
        assert call_count == 2
    
    async def test_cache_method_decorator(self, cache_manager):
        """测试cache_method装饰器"""
        from fastorm.cache.decorators import cache_method
        
        class TestClass:
            def __init__(self, name: str):
                self.name = name
                self.call_count = 0
            
            @cache_method(ttl=60)
            async def expensive_method(self, value: int) -> dict:
                self.call_count += 1
                await asyncio.sleep(0.01)
                return {"name": self.name, "value": value, 
                       "call": self.call_count}
        
        obj = TestClass("test")
        
        # 第一次调用
        result1 = await obj.expensive_method(10)
        assert result1["value"] == 10
        assert result1["call"] == 1
        assert obj.call_count == 1
        
        # 第二次调用（应该从缓存获取）
        result2 = await obj.expensive_method(10)
        assert result2["call"] == 1  # 缓存结果
        assert obj.call_count == 1  # 没有再次调用


class TestModelCache:
    """模型缓存测试"""
    
    async def test_cacheable_model_find_or_cache(self, cache_manager, mock_model):
        """测试模型的find_or_cache功能"""
        from fastorm.cache.cacheable import CacheableModel
        
        class CacheableUser(mock_model, CacheableModel):
            _cache_ttl = 300
            _cache_tags = {'users'}
        
        # 模拟find方法的调用次数
        original_find = CacheableUser.find
        call_count = 0
        
        async def counted_find(cls, id: int):
            nonlocal call_count
            call_count += 1
            return await original_find(id)
        
        CacheableUser.find = classmethod(counted_find)
        
        # 第一次查找
        user1 = await CacheableUser.find_or_cache(1, ttl=300)
        assert user1.id == 1
        assert user1.name == "User 1"
        assert call_count == 1
        
        # 第二次查找（应该从缓存获取）
        user2 = await CacheableUser.find_or_cache(1, ttl=300)
        assert user2.id == 1
        assert call_count == 1  # 没有再次调用find
    
    async def test_model_cache_invalidation(self, cache_manager, mock_model):
        """测试模型缓存失效"""
        from fastorm.cache.cacheable import invalidate_model_cache
        
        class CacheableUser(mock_model):
            _cache_prefix = 'test'
            
            @classmethod
            async def cache_key_for_id(cls, id):
                return f"test:model:cacheableuser:{id}"
        
        # 设置模型实例缓存
        cache_key = await CacheableUser.cache_key_for_id(1)
        await cache_manager.set(cache_key, {"id": 1, "name": "User 1"}, 
                               ttl=300, tags={'users', 'user:1'})
        
        # 确认缓存存在
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is not None
        
        # 清除模型缓存
        await invalidate_model_cache(CacheableUser, instance_id=1)
        
        # 确认缓存已清除
        cached_data = await cache_manager.get(cache_key)
        assert cached_data is None


class TestPerformance:
    """性能测试"""
    
    async def test_cache_performance_improvement(self, cache_manager):
        """测试缓存性能提升"""
        from fastorm.cache import remember
        
        async def slow_operation():
            await asyncio.sleep(0.1)  # 模拟慢操作
            return {"timestamp": datetime.now().isoformat()}
        
        # 测试无缓存性能
        start_time = datetime.now()
        for _ in range(3):
            await slow_operation()
        no_cache_time = (datetime.now() - start_time).total_seconds()
        
        # 测试有缓存性能
        start_time = datetime.now()
        for _ in range(3):
            await remember("slow_op", 60, slow_operation)
        cache_time = (datetime.now() - start_time).total_seconds()
        
        # 缓存应该显著提升性能
        improvement = no_cache_time / cache_time
        assert improvement > 2.0  # 至少2倍提升
    
    async def test_memory_backend_capacity(self, cache_manager):
        """测试内存后端容量限制"""
        # 设置大量缓存项
        for i in range(150):  # 超过max_size=100
            await cache_manager.set(f"item_{i}", f"value_{i}", ttl=3600)
        
        # 检查是否正确限制了容量
        backend = cache_manager.backend
        assert len(backend._data) <= backend.max_size


class TestIntegration:
    """集成测试"""
    
    async def test_complete_workflow(self, cache_manager):
        """测试完整的缓存工作流"""
        from fastorm.cache import remember, forget, flush
        
        # 1. 设置数据
        user_data = await remember(
            "user:profile:1", 
            300,
            lambda: {"id": 1, "name": "Alice", "email": "alice@example.com"}
        )
        
        posts_data = await remember(
            "user:posts:1",
            300, 
            lambda: [{"id": 1, "title": "Post 1"}, {"id": 2, "title": "Post 2"}],
            tags={'posts', 'user:1'}
        )
        
        # 2. 验证缓存存在
        assert user_data["name"] == "Alice"
        assert len(posts_data) == 2
        
        # 3. 清除特定缓存
        await forget("user:profile:1")
        cached_user = await cache_manager.get("user:profile:1")
        assert cached_user is None
        
        # 4. 按标签清除
        count = await flush('user:1')
        assert count >= 1
        
        cached_posts = await cache_manager.get("user:posts:1")
        assert cached_posts is None
    
    async def test_error_handling(self, cache_manager):
        """测试错误处理"""
        from fastorm.cache import remember
        
        async def failing_operation():
            raise ValueError("Test error")
        
        # 确保异常正确传播
        with pytest.raises(ValueError, match="Test error"):
            await remember("failing_op", 60, failing_operation)
        
        # 确保缓存中没有错误结果
        cached_result = await cache_manager.get("failing_op")
        assert cached_result is None


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"]) 