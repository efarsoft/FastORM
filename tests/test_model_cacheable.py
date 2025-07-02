"""
测试 CacheableModel 模型缓存功能
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

from fastorm.model.model import Model
from fastorm.model.cacheable import CacheableModel


class CachedUser(Model, CacheableModel):
    """支持缓存的用户模型"""
    __tablename__ = 'cached_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    status = Column(String(20))
    
    # 缓存配置
    _cache_ttl = 600  # 10分钟
    _cache_prefix = "test_fastorm"


class TestCacheableModel:
    """测试模型缓存功能"""

    @pytest.fixture
    async def cache_user(self, test_session: AsyncSession):
        """创建缓存用户测试数据"""
        # 使用随机ID避免冲突
        random_id = 5000 + (int(uuid4().int) % 9000)  # 5000-13999范围
        user = CachedUser(
            id=random_id,
            name=f"cache_user_{uuid4().hex[:8]}",
            status="active"
        )
        test_session.add(user)
        await test_session.commit()
        return user

    async def test_cache_key_for_id_generation(self):
        """测试ID缓存键生成"""
        cache_key = await CachedUser.cache_key_for_id(123)
        expected_key = "test_fastorm:model:cacheduser:123"
        assert cache_key == expected_key

    async def test_cache_key_for_query_generation(self):
        """测试查询缓存键生成"""
        conditions = {"status": "active", "age": 25}
        cache_key = await CachedUser.cache_key_for_query(**conditions)
        
        # 验证键格式
        assert cache_key.startswith("test_fastorm:query:cacheduser:")
        assert len(cache_key.split(":")) == 4  # prefix:query:model:hash

    async def test_cache_instance_without_id(self):
        """测试缓存没有ID的实例"""
        user_without_id = CachedUser(name="no_id_user", status="pending")
        
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            await user_without_id.cache_instance()
            
            # 不应该调用缓存设置
            mock_cache.set.assert_not_called()

    async def test_cache_instance_with_id(self, cache_user):
        """测试缓存有ID的实例"""
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            # 模拟to_dict方法
            def mock_to_dict():
                return {
                    'id': cache_user.id,
                    'name': cache_user.name,
                    'status': cache_user.status
                }
            cache_user.to_dict = mock_to_dict
            
            await cache_user.cache_instance(3600)
            
            # 验证缓存调用
            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            
            assert call_args[0][1]['id'] == cache_user.id  # 缓存数据
            assert call_args[0][1]['__model_class__'] == 'CachedUser'
            assert call_args[0][2] == 3600  # TTL

    async def test_forget_instance_cache_without_id(self):
        """测试忘记没有ID的实例缓存"""
        user_without_id = CachedUser(name="no_id_user")
        result = await user_without_id.forget_instance_cache()
        assert result is False

    async def test_forget_instance_cache_with_id(self, cache_user):
        """测试忘记有ID的实例缓存"""
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.delete = AsyncMock(return_value=True)
            
            result = await cache_user.forget_instance_cache()
            
            assert result is True
            mock_cache.delete.assert_called_once()

    async def test_forget_cache_class_method(self):
        """测试类方法忘记缓存"""
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.delete = AsyncMock(return_value=True)
            
            result = await CachedUser.forget_cache('test_key')
            
            assert result is True
            mock_cache.delete.assert_called_once_with('test_key')

    async def test_flush_cache_class_method(self):
        """测试类方法刷新标签缓存"""
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.invalidate_tag = AsyncMock()
            
            await CachedUser.flush_cache('users', 'profiles')
            
            assert mock_cache.invalidate_tag.call_count == 2
            mock_cache.invalidate_tag.assert_any_call('users')
            mock_cache.invalidate_tag.assert_any_call('profiles')

    async def test_find_cached_miss(self):
        """测试缓存未命中的查找"""
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            
            result = await CachedUser.find_cached(123)
            
            assert result is None
            mock_cache.get.assert_called_once()

    async def test_find_cached_hit(self):
        """测试缓存命中的查找"""
        cached_data = {
            'id': 123,
            'name': 'cached_user',
            'status': 'active',
            '__model_class__': 'CachedUser'
        }
        
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=cached_data)
            
            with patch.object(CachedUser, '_deserialize_instance') as mock_deserialize:
                mock_instance = CachedUser(id=123, name='cached_user')
                mock_deserialize.return_value = mock_instance
                
                result = await CachedUser.find_cached(123)
                
                assert result == mock_instance
                mock_deserialize.assert_called_once_with(cached_data)

    async def test_find_or_cache_cached_exists(self):
        """测试查找或缓存：缓存存在"""
        cached_data = {
            'id': 123,
            'name': 'cached_user',
            'status': 'active',
            '__model_class__': 'CachedUser'
        }
        
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=cached_data)
            
            with patch.object(CachedUser, '_deserialize_instance') as mock_deserialize:
                mock_instance = CachedUser(id=123, name='cached_user')
                mock_deserialize.return_value = mock_instance
                
                result = await CachedUser.find_or_cache(123)
                
                assert result == mock_instance

    async def test_find_or_cache_not_cached(self):
        """测试查找或缓存：缓存不存在，需要查询数据库"""
        with patch('fastorm.cache.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            
            with patch.object(CachedUser, 'find') as mock_find:
                mock_instance = CachedUser(id=123, name='db_user')
                mock_instance.to_dict = lambda: {
                    'id': 123,
                    'name': 'db_user',
                    'status': 'active'
                }
                mock_find.return_value = mock_instance
                
                result = await CachedUser.find_or_cache(123, ttl=1800)
                
                assert result == mock_instance
                mock_find.assert_called_once_with(123)
                # 应该缓存查找到的实例
                mock_cache.set.assert_called_once()

    async def test_get_cache_tags_default(self, cache_user):
        """测试获取默认缓存标签"""
        tags = cache_user._get_cache_tags()
        
        # 默认情况下应该返回模型名标签和实例标签(带ID)
        expected_tags = {"cacheduser", f"cacheduser:{cache_user.id}"}
        assert tags == expected_tags

    async def test_get_cache_tags_custom(self):
        """测试自定义缓存标签"""
        CachedUser._cache_tags = {"custom_tag", "users"}
        
        user = CachedUser(id=1, name="test")
        tags = user._get_cache_tags()
        
        assert "custom_tag" in tags
        assert "users" in tags

    async def test_deserialize_instance_valid_data(self):
        """测试反序列化有效数据"""
        cached_data = {
            'id': 123,
            'name': 'deserialized_user',
            'status': 'active',
            '__model_class__': 'CachedUser'
        }
        
        instance = CachedUser._deserialize_instance(cached_data)
        
        assert instance is not None
        assert instance.id == 123
        assert instance.name == 'deserialized_user'
        assert instance.status == 'active'

    async def test_deserialize_instance_invalid_class(self):
        """测试反序列化错误类名数据"""
        cached_data = {
            'id': 123,
            'name': 'user',
            '__model_class__': 'WrongClass'
        }
        
        instance = CachedUser._deserialize_instance(cached_data)
        assert instance is None

    async def test_deserialize_instance_missing_class(self):
        """测试反序列化缺少类名数据"""
        cached_data = {
            'id': 123,
            'name': 'user'
            # 缺少 __model_class__
        }
        
        instance = CachedUser._deserialize_instance(cached_data)
        assert instance is None

    async def test_cache_for_class_method(self):
        """测试cache_for类方法"""
        with patch.object(CachedUser, 'query') as mock_query:
            mock_builder = AsyncMock()
            mock_builder.remember.return_value = mock_builder
            mock_query.return_value = mock_builder
            
            result = CachedUser.cache_for(3600)
            
            mock_query.assert_called_once()
            mock_builder.remember.assert_called_once_with(3600)

    async def test_cache_forever_class_method(self):
        """测试cache_forever类方法"""
        with patch.object(CachedUser, 'query') as mock_query:
            mock_builder = AsyncMock()
            mock_builder.remember.return_value = mock_builder
            mock_query.return_value = mock_builder
            
            result = CachedUser.cache_forever()
            
            mock_query.assert_called_once()
            # 应该使用一年的TTL
            mock_builder.remember.assert_called_once_with(ttl=86400 * 365)

    async def test_remember_class_method(self):
        """测试remember类方法"""
        with patch.object(CachedUser, 'query') as mock_query:
            mock_builder = AsyncMock()
            mock_builder.remember.return_value = mock_builder
            mock_query.return_value = mock_builder
            
            result = CachedUser.remember('test_key', 1800, ['tag1', 'tag2'])
            
            mock_query.assert_called_once()
            mock_builder.remember.assert_called_once_with(
                ttl=1800,
                key='test_key',
                tags=['tag1', 'tag2']
            )

    async def test_cache_configuration_inheritance(self):
        """测试缓存配置继承"""
        class CustomCachedUser(CachedUser):
            _cache_ttl = 1800
            _cache_prefix = "custom"
            _cache_tags = {"custom_users"}
        
        assert CustomCachedUser._cache_ttl == 1800
        assert CustomCachedUser._cache_prefix == "custom"
        assert "custom_users" in CustomCachedUser._cache_tags

    async def test_cacheable_model_mixin_subclass_hook(self):
        """测试CacheableModelMixin的子类钩子"""
        from fastorm.model.cacheable import CacheableModelMixin
        
        class TestCacheableModel(Model, CacheableModelMixin):
            __tablename__ = 'test_cacheable'
            id = Column(Integer, primary_key=True)
        
        # 验证子类正确设置了缓存混入
        # CacheableModelMixin只设置缓存标签和前缀，不提供方法
        assert hasattr(TestCacheableModel, '_cache_tags')
        assert hasattr(TestCacheableModel, '_cache_prefix')
        assert TestCacheableModel._cache_tags == {'testcacheablemodel'}
        assert TestCacheableModel._cache_prefix == 'fastorm' 