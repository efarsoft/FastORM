"""
FastORM 关系功能简化测试

测试基本的关系类型：HasOne、BelongsTo
"""

import pytest
from sqlalchemy import Column, Integer, String, ForeignKey
from fastorm.model import Model
from fastorm.relations import HasOne, BelongsTo
from fastorm.relations.mixins import RelationMixin

class SimpleUser(Model, RelationMixin):
    """简单用户模型"""
    __tablename__ = 'simple_test_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True)
    
    profile = HasOne('SimpleProfile', foreign_key='user_id')

class SimpleProfile(Model, RelationMixin):
    """简单档案模型"""
    __tablename__ = 'simple_test_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('simple_test_users.id'), nullable=False)
    bio = Column(String(500))
    
    user = BelongsTo('SimpleUser', foreign_key='user_id')

class TestSimpleRelations:
    """简化关系功能测试类"""
    
    @pytest.mark.asyncio
    async def test_has_one_basic_load(self, test_database):
        """测试HasOne关系基本加载"""
        user = SimpleUser(name="Alice", email="alice@example.com")
        await user.save()
        
        profile = SimpleProfile(user_id=user.id, bio="Alice的简介")
        await profile.save()
        
        found_user = await SimpleUser.find(user.id)
        assert found_user is not None
        
        loaded_profile = await found_user.profile.load()
        assert loaded_profile is not None
        assert loaded_profile.bio == "Alice的简介"
    
    @pytest.mark.asyncio
    async def test_belongs_to_basic_load(self, test_database):
        """测试BelongsTo关系基本加载"""
        user = SimpleUser(name="Bob", email="bob@example.com")
        await user.save()
        
        profile = SimpleProfile(user_id=user.id, bio="Bob的简介")
        await profile.save()
        
        found_profile = await SimpleProfile.find(profile.id)
        assert found_profile is not None
        
        loaded_user = await found_profile.user.load()
        assert loaded_user is not None
        assert loaded_user.name == "Bob"
    
    @pytest.mark.asyncio
    async def test_has_one_cache(self, test_database):
        """测试HasOne关系缓存"""
        user = SimpleUser(name="Charlie", email="charlie@example.com")
        await user.save()
        
        profile = SimpleProfile(user_id=user.id, bio="Charlie的简介")
        await profile.save()
        
        found_user = await SimpleUser.find(user.id)
        
        profile1 = await found_user.profile.load()
        assert found_user.profile.is_loaded
        
        profile2 = await found_user.profile.load()
        assert profile1 is profile2
    
    @pytest.mark.anyio
    async def test_has_one_no_relation(self, test_database):
        """测试HasOne关系不存在的情况"""
        user = SimpleUser(name="NoProfile", email="noprofile@example.com")
        await user.save()

        found_user = await SimpleUser.find(user.id)
        profile = await found_user.profile.load()
        assert profile is None
    
    @pytest.mark.asyncio
    async def test_relation_discovery(self, test_database):
        """测试关系自动发现"""
        user = SimpleUser(name="Test", email="test@example.com")
        profile = SimpleProfile(user_id=1, bio="test")
        
        user_relations = user.get_relations()
        assert 'profile' in user_relations
        assert isinstance(user_relations['profile'], HasOne)
        
        profile_relations = profile.get_relations()
        assert 'user' in profile_relations
        assert isinstance(profile_relations['user'], BelongsTo) 