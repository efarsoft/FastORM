"""
高级关系测试 - 测试复杂的关系查询、链式查询、预加载等功能
"""

import pytest
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from datetime import datetime

from fastorm.model.model import Model
from fastorm.relations.has_many import HasMany
from fastorm.relations.has_one import HasOne
from fastorm.relations.belongs_to import BelongsTo
from fastorm.relations.loader import RelationLoader


# 测试模型定义
class User(Model):
    __tablename__ = "adv_users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Post(Model):
    __tablename__ = "adv_posts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('adv_users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    status = Column(String(20), default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)


class Comment(Model):
    __tablename__ = "adv_comments"
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('adv_posts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('adv_users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Profile(Model):
    __tablename__ = "adv_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey('adv_users.id'), unique=True, nullable=False
    )
    bio = Column(Text)
    avatar = Column(String(200))


@pytest.fixture
async def sample_data(test_session):
    """创建测试数据"""
    import uuid
    
    # 使用UUID确保每次测试数据的唯一性
    unique_suffix = str(uuid.uuid4())[:8]
    
    # 创建用户
    user1 = User(name="Alice", email=f"alice_{unique_suffix}@example.com")
    user2 = User(name="Bob", email=f"bob_{unique_suffix}@example.com")
    test_session.add_all([user1, user2])
    await test_session.flush()
    
    # 创建文章
    post1 = Post(
        user_id=user1.id, 
        title="Alice的第一篇文章", 
        content="内容1", 
        status="published"
    )
    post2 = Post(
        user_id=user1.id, 
        title="Alice的第二篇文章", 
        content="内容2", 
        status="draft"
    )
    post3 = Post(
        user_id=user2.id, 
        title="Bob的文章", 
        content="内容3", 
        status="published"
    )
    test_session.add_all([post1, post2, post3])
    await test_session.flush()
    
    # 创建评论
    comment1 = Comment(
        post_id=post1.id, 
        user_id=user2.id, 
        content="很好的文章！"
    )
    comment2 = Comment(
        post_id=post1.id, 
        user_id=user1.id, 
        content="谢谢支持"
    )
    test_session.add_all([comment1, comment2])
    
    # 创建用户资料
    profile1 = Profile(
        user_id=user1.id, 
        bio="Alice的个人简介", 
        avatar="alice.jpg"
    )
    profile2 = Profile(
        user_id=user2.id, 
        bio="Bob的个人简介", 
        avatar="bob.jpg"
    )
    test_session.add_all([profile1, profile2])
    
    await test_session.commit()
    
    return {
        'users': [user1, user2],
        'posts': [post1, post2, post3],
        'comments': [comment1, comment2],
        'profiles': [profile1, profile2]
    }


class TestAdvancedRelations:
    """高级关系测试"""
    
    async def test_has_many_relation_loading(self, test_session, sample_data):
        """测试HasMany关系加载"""
        user = sample_data['users'][0]  # Alice
        
        # 创建关系实例
        posts_relation = HasMany(Post, foreign_key='user_id')
        
        # 加载关系
        posts = await posts_relation.load(user, test_session)
        
        assert len(posts) == 2
        assert all(post.user_id == user.id for post in posts)
        titles = {post.title for post in posts}
        expected_titles = {"Alice的第一篇文章", "Alice的第二篇文章"}
        assert titles == expected_titles
    
    async def test_belongs_to_relation_loading(self, test_session, sample_data):
        """测试BelongsTo关系加载"""
        post = sample_data['posts'][0]  # Alice的第一篇文章
        
        # 创建关系实例
        author_relation = BelongsTo(User, foreign_key='user_id')
        
        # 加载关系
        author = await author_relation.load(post, test_session)
        
        assert author is not None
        assert author.id == post.user_id
        assert author.name == "Alice"
    
    async def test_has_one_relation_loading(self, test_session, sample_data):
        """测试HasOne关系加载"""
        user = sample_data['users'][0]  # Alice
        
        # 创建关系实例
        profile_relation = HasOne(Profile, foreign_key='user_id')
        
        # 加载关系
        profile = await profile_relation.load(user, test_session)
        
        assert profile is not None
        assert profile.user_id == user.id
        assert profile.bio == "Alice的个人简介"
    
    async def test_relation_loader_basic_caching(
        self, test_session, sample_data
    ):
        """测试关系加载器的基本缓存功能"""
        user = sample_data['users'][0]
        posts_relation = HasMany(Post, foreign_key='user_id')
        
        # 首次加载
        posts1 = await RelationLoader.load_relation(
            user, 'posts', posts_relation, test_session
        )
        
        # 检查是否已加载
        assert RelationLoader.is_relation_loaded(user, 'posts')
        
        # 从缓存获取
        cached_posts = RelationLoader.get_relation_cache(user, 'posts')
        assert cached_posts is posts1
        assert len(cached_posts) == 2
    
    async def test_relation_cache_clearing(self, test_session, sample_data):
        """测试关系缓存清理"""
        user = sample_data['users'][0]
        posts_relation = HasMany(Post, foreign_key='user_id')
        
        # 加载并缓存
        await RelationLoader.load_relation(
            user, 'posts', posts_relation, test_session
        )
        assert RelationLoader.is_relation_loaded(user, 'posts')
        
        # 清除特定关系缓存
        RelationLoader.clear_relation_cache(user, 'posts')
        assert not RelationLoader.is_relation_loaded(user, 'posts')
        
        # 重新加载
        await RelationLoader.load_relation(
            user, 'posts', posts_relation, test_session
        )
        profile_relation = HasOne(Profile, foreign_key='user_id')
        await RelationLoader.load_relation(
            user, 'profile', profile_relation, test_session
        )
        
        # 清除所有关系缓存
        RelationLoader.clear_relation_cache(user)
        assert not RelationLoader.is_relation_loaded(user, 'posts')
        assert not RelationLoader.is_relation_loaded(user, 'profile')
    
    async def test_eager_loading_multiple_relations(
        self, test_session, sample_data
    ):
        """测试预加载多个关系"""
        users = sample_data['users']
        
        # 定义关系
        relations = {
            'posts': HasMany(Post, foreign_key='user_id'),
            'profile': HasOne(Profile, foreign_key='user_id')
        }
        
        # 预加载关系
        await RelationLoader.eager_load_relations(
            users, relations, test_session
        )
        
        # 验证所有用户的关系都已加载
        for user in users:
            assert RelationLoader.is_relation_loaded(user, 'posts')
            assert RelationLoader.is_relation_loaded(user, 'profile')
            
            # 验证数据正确性
            posts = RelationLoader.get_relation_cache(user, 'posts')
            profile = RelationLoader.get_relation_cache(user, 'profile')
            
            if user.name == "Alice":
                assert len(posts) == 2
            elif user.name == "Bob":
                assert len(posts) == 1
            
            assert profile.user_id == user.id
    
    async def test_batch_relation_loading(self, test_session, sample_data):
        """测试批量关系加载"""
        user = sample_data['users'][0]  # Alice
        
        # 定义多个关系
        relations = {
            'posts': HasMany(Post, foreign_key='user_id'),
            'profile': HasOne(Profile, foreign_key='user_id')
        }
        
        # 批量加载
        results = await RelationLoader.load_relations(
            user, relations, test_session
        )
        
        # 验证结果
        assert 'posts' in results
        assert 'profile' in results
        
        # 验证posts
        posts = results['posts']
        assert len(posts) == 2
        assert all(post.user_id == user.id for post in posts)
        
        # 验证profile
        profile = results['profile']
        assert profile.user_id == user.id
    
    async def test_nested_relation_loading(self, test_session, sample_data):
        """测试嵌套关系加载（模拟链式查询中的深度关系）"""
        post = sample_data['posts'][0]  # Alice的第一篇文章
        
        # 1. 加载文章的评论（has_many）
        comments_relation = HasMany(Comment, foreign_key='post_id')
        comments = await comments_relation.load(post, test_session)
        assert len(comments) == 2
        
        # 2. 为每个评论加载作者（belongs_to）
        author_relation = BelongsTo(User, foreign_key='user_id')
        comment_authors = []
        for comment in comments:
            author = await author_relation.load(comment, test_session)
            comment_authors.append((comment, author))
        
        # 验证嵌套关系数据
        assert len(comment_authors) == 2
        for comment, author in comment_authors:
            assert author.id == comment.user_id
            assert author.name in ["Alice", "Bob"]
    
    async def test_has_many_create_operation(self, test_session, sample_data):
        """测试HasMany关系的创建操作（模拟关系create操作）"""
        user = sample_data['users'][1]  # Bob
        posts_relation = HasMany(Post, foreign_key='user_id')
        
        # 模拟关系create操作的逻辑
        foreign_key = posts_relation.get_foreign_key(user)
        local_key_value = posts_relation.get_local_key_value(user)
        
        # 创建新文章，设置外键值
        attributes = {
            "title": "Bob的新文章",
            "content": "这是新创建的文章",
            "status": "published",
            foreign_key: local_key_value
        }
        
        new_post = Post(**attributes)
        test_session.add(new_post)
        await test_session.flush()
        await test_session.refresh(new_post)
        
        assert new_post.user_id == user.id
        assert new_post.title == "Bob的新文章"
        assert new_post.id is not None
    
    async def test_has_many_save_operation(self, test_session, sample_data):
        """测试HasMany关系的保存操作（模拟关系save操作）"""
        user = sample_data['users'][1]  # Bob
        posts_relation = HasMany(Post, foreign_key='user_id')
        
        # 创建新文章实例
        new_post = Post(title="待保存的文章", content="内容")
        
        # 模拟关系save操作的逻辑
        foreign_key = posts_relation.get_foreign_key(user)
        local_key_value = posts_relation.get_local_key_value(user)
        setattr(new_post, foreign_key, local_key_value)
        
        # 保存实例
        test_session.add(new_post)
        await test_session.flush()
        await test_session.refresh(new_post)
        
        assert new_post.user_id == user.id
        assert new_post.title == "待保存的文章"
        assert new_post.id is not None
    
    async def test_has_many_count_operation(self, test_session, sample_data):
        """测试HasMany关系的计数操作（模拟关系count操作）"""
        user = sample_data['users'][0]  # Alice
        posts_relation = HasMany(Post, foreign_key='user_id')
        
        # 模拟关系count操作的逻辑
        from sqlalchemy import func, select
        
        foreign_key = posts_relation.get_foreign_key(user)
        local_key_value = posts_relation.get_local_key_value(user)
        
        # 执行计数查询
        result = await test_session.execute(
            select(func.count())
            .select_from(Post)
            .where(getattr(Post, foreign_key) == local_key_value)
        )
        
        post_count = result.scalar() or 0
        assert post_count == 2 