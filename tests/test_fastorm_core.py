"""
FastORM 核心类测试

测试FastORM主类的数据库连接、会话管理等核心功能。
"""

import pytest
from fastorm.core.fastorm import FastORM
from sqlalchemy.ext.asyncio import AsyncSession
from fastorm import Model, Field


class TestFastORM:
    """FastORM核心类测试"""

    async def test_fastorm_initialization(self):
        """测试FastORM初始化"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url)

        assert fastorm.database_url == database_url
        assert fastorm.engine is not None
        assert fastorm.session_factory is not None
        assert FastORM._instance is fastorm

        # 清理
        await fastorm.close()

    async def test_get_instance(self):
        """测试获取FastORM实例"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url)

        # 测试获取实例
        instance = FastORM.get_instance()
        assert instance is fastorm

        # 清理
        await fastorm.close()

    async def test_get_instance_not_initialized(self):
        """测试未初始化时获取实例"""
        # 清理可能存在的实例
        FastORM._instance = None

        with pytest.raises(RuntimeError, match="FastORM not initialized"):
            FastORM.get_instance()

    async def test_create_session(self):
        """测试创建数据库会话"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url)

        session = await fastorm.create_session()
        assert isinstance(session, AsyncSession)

        # 清理
        await session.close()
        await fastorm.close()

    async def test_create_all_tables(self):
        """测试创建所有表"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url)

        # 这里只测试方法调用不出错
        await fastorm.create_all()

        # 清理
        await fastorm.close()

    async def test_drop_all_tables(self):
        """测试删除所有表"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url)

        # 先创建表再删除
        await fastorm.create_all()
        await fastorm.drop_all()

        # 清理
        await fastorm.close()

    async def test_close_connection(self):
        """测试关闭数据库连接"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url)

        # 测试关闭连接
        await fastorm.close()

    async def test_fastorm_with_engine_options(self):
        """测试带有引擎选项的FastORM初始化"""
        database_url = "sqlite+aiosqlite:///test_core.db"
        fastorm = FastORM(database_url, echo=True)

        assert fastorm.database_url == database_url
        assert fastorm.engine is not None

        # 清理
        await fastorm.close()

    async def test_multiple_fastorm_instances(self):
        """测试多个FastORM实例（应该覆盖全局实例）"""
        database_url1 = "sqlite+aiosqlite:///test_core1.db"
        database_url2 = "sqlite+aiosqlite:///test_core2.db"

        fastorm1 = FastORM(database_url1)
        assert FastORM.get_instance() is fastorm1

        fastorm2 = FastORM(database_url2)
        assert FastORM.get_instance() is fastorm2
        assert FastORM.get_instance() is not fastorm1

        # 清理
        await fastorm1.close()
        await fastorm2.close()


class User(Model):
    __tablename__ = "users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True, max_length=255)
    age: int = Field(default=0)


@pytest.mark.asyncio
async def test_field_syntax_crud(test_database):
    # 创建
    user = await User.create(name="张三", email="zhangsan@example.com", age=18)
    assert user.id is not None
    assert user.name == "张三"
    assert user.email == "zhangsan@example.com"
    assert user.age == 18
    # 查询
    user2 = await User.find(user.id)
    assert user2 is not None
    assert user2.name == "张三"
    # 更新
    await user.update(name="李四")
    user3 = await User.find(user.id)
    assert user3.name == "李四"
    # 删除
    await user.delete()
    user4 = await User.find(user.id)
    assert user4 is None


def test_composite_pseudo_primary_key():
    class MyView(Model):
        __tablename__ = "my_view"
        col1: str = Field()
        col2: int = Field()
        col3: str = Field()
        __mapper_args__ = {
            "primary_key": ["col1", "col2"]  # 使用字符串引用字段名
        }
    # 不应抛出主键缺失异常
    assert hasattr(MyView, "__mapper_args__")
    assert "primary_key" in MyView.__mapper_args__
