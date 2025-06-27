"""
FastORM 测试配置

提供测试所需的基础fixtures和配置
"""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, ForeignKey
from fastorm import Model
from fastorm.connection.database import init, close, create_all


# 测试数据库URL - 使用SQLite内存数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestUser(Model):
    """测试用户模型"""
    __tablename__ = "test_users"
    
    # 启用时间戳（现在是Model的内置功能）
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)


class TestPost(Model):
    """测试文章模型"""
    __tablename__ = "test_posts"
    
    # 启用时间戳
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_users.id"), nullable=False)


@pytest.fixture(scope="session")
def event_loop():
    """创建测试事件循环"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # 测试时不显示SQL
        future=True
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    
    yield engine
    
    # 清理
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(test_engine):
    """创建测试会话 - 与测试文件中的命名保持一致"""
    async_session_maker = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_session(test_engine):
    """创建测试会话"""
    async_session_maker = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_database():
    """初始化测试数据库"""
    # 使用全局便利函数 - 简洁明了
    db = init(TEST_DATABASE_URL, echo=False)
    
    # 创建所有表
    await create_all()
    
    yield db
    
    # 清理连接
    await close()


@pytest_asyncio.fixture
async def sample_user(test_session):
    """创建测试用户"""
    user = TestUser(
        name="张三",
        email="zhangsan@example.com",
        age=25
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_users(test_session):
    """创建多个测试用户"""
    users = [
        TestUser(name="张三", email="zhangsan@example.com", age=25),
        TestUser(name="李四", email="lisi@example.com", age=30),
        TestUser(name="王五", email="wangwu@example.com", age=28),
    ]
    
    for user in users:
        test_session.add(user)
    await test_session.commit()
    
    for user in users:
        await test_session.refresh(user)
    
    return users


@pytest_asyncio.fixture  
async def sample_post(test_session, sample_user):
    """创建测试文章"""
    post = TestPost(
        title="测试文章",
        content="这是一篇测试文章的内容",
        user_id=sample_user.id
    )
    test_session.add(post)
    await test_session.commit()
    await test_session.refresh(post)
    return post 