"""
FastORM 链式查询测试

测试FastORM链式查询功能的核心方法。
"""

import pytest
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean
from fastorm import Model


class ChainUser(Model):
    """链式查询测试用户模型"""
    __tablename__ = "chain_users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class TestChainQueries:
    """链式查询测试类"""

    @pytest.mark.asyncio
    async def test_basic_where_queries(self, test_database):
        """测试基础where查询"""
        # 使用FastORM的create方法创建测试数据
        await ChainUser.create(name="Alice", email="alice@test.com", age=25, status="active")
        await ChainUser.create(name="Bob", email="bob@test.com", age=30, status="inactive")
        await ChainUser.create(name="Charlie", email="charlie@test.com", age=35, status="active")

        # 测试等于查询
        active_users = await ChainUser.where('status', 'active').get()
        assert len(active_users) == 2
        assert all(user.status == 'active' for user in active_users)

        # 测试简化语法（两参数形式）
        alice = await ChainUser.where('name', 'Alice').first()
        assert alice is not None
        assert alice.name == 'Alice'

        # 测试大于查询
        older_users = await ChainUser.where('age', '>', 30).get()
        assert len(older_users) == 1
        assert older_users[0].name == 'Charlie'

    @pytest.mark.asyncio
    async def test_chained_where_queries(self, test_database):
        """测试链式where查询"""
        # 使用FastORM的create方法创建测试数据
        await ChainUser.create(name="Test", email="test2@example.com", age=25, status="active")

        # 测试多个where条件
        result = await ChainUser.where('status', 'active').where('age', '>', 20).get()
        assert len(result) >= 1
        test_user = next((user for user in result if user.name == 'Test'), None)
        assert test_user is not None

    @pytest.mark.asyncio
    async def test_query_builder_methods(self, test_database):
        """测试查询构建器方法"""
        # 使用FastORM的create方法创建测试数据
        await ChainUser.create(name="User1", email="user1@test.com", age=25)
        await ChainUser.create(name="User2", email="user2@test.com", age=30)

        # 测试query()方法
        query_users = await ChainUser.query().get()
        assert len(query_users) >= 2

        # 测试order_by
        ordered_users = await ChainUser.query().order_by('age').get()
        assert len(ordered_users) >= 2
        # 检查是否按年龄排序
        for i in range(len(ordered_users) - 1):
            assert ordered_users[i].age <= ordered_users[i + 1].age

        # 测试limit
        limited_users = await ChainUser.query().limit(1).get()
        assert len(limited_users) == 1

        # 测试offset
        offset_users = await ChainUser.query().offset(1).get()
        assert len(offset_users) >= 1

    @pytest.mark.asyncio
    async def test_aggregation_methods(self, test_database):
        """测试聚合方法"""
        # 清理之前的数据，避免唯一约束冲突
        await ChainUser.delete_where('email', 'test3@example.com')
        
        # 使用FastORM的create方法创建测试数据
        await ChainUser.create(name="Test", email="test3@example.com", age=25)

        # 测试count
        total_count = await ChainUser.count()
        assert total_count >= 1

        # 测试带条件的count
        count_result = await ChainUser.where('name', 'Test').count()
        assert count_result >= 1

        # 测试exists
        exists_result = await ChainUser.where('name', 'Test').exists()
        assert exists_result is True

        non_exists = await ChainUser.where('name', 'NonExistent').exists()
        assert non_exists is False

    @pytest.mark.asyncio
    async def test_force_write_queries(self, test_database):
        """测试强制写库查询"""
        # 使用FastORM的create方法创建测试数据
        await ChainUser.create(name="WriteTest", email="write@test.com", age=25)

        # 测试force_write
        result = await ChainUser.where('name', 'WriteTest').force_write().first()
        assert result is not None
        assert result.name == 'WriteTest'

    @pytest.mark.asyncio
    async def test_bulk_operations(self, test_database):
        """测试批量操作"""
        # 使用FastORM的create方法创建测试数据
        await ChainUser.create(name="Bulk1", email="bulk1@test.com", status="pending")
        await ChainUser.create(name="Bulk2", email="bulk2@test.com", status="pending")

        # 测试批量更新
        updated_count = await ChainUser.where('status', 'pending').update(status='processed')
        assert updated_count >= 2

        # 验证更新结果
        processed_users = await ChainUser.where('status', 'processed').get()
        assert len(processed_users) >= 2

        # 测试批量删除
        deleted_count = await ChainUser.where('status', 'processed').delete()
        assert deleted_count >= 2

    @pytest.mark.asyncio
    async def test_error_handling(self, async_session, test_database):
        """测试错误处理"""
        # 创建表
        async with async_session.begin():
            await async_session.run_sync(
                lambda sync_session: ChainUser.metadata.create_all(sync_session.bind)
            )

        # 测试无效字段名
        with pytest.raises(ValueError, match="Field invalid_field not found"):
            await ChainUser.where('invalid_field', 'value').get()

        # 测试无效操作符
        with pytest.raises(ValueError, match="Unsupported operator"):
            await ChainUser.where('name', 'invalid_op', 'value').get()

        # 测试无效排序字段
        with pytest.raises(ValueError, match="Field invalid_field not found"):
            await ChainUser.query().order_by('invalid_field').get()

    @pytest.mark.asyncio
    async def test_query_builder_clone(self, async_session, test_database):
        """测试查询构建器克隆"""
        # 创建表
        async with async_session.begin():
            await async_session.run_sync(
                lambda sync_session: ChainUser.metadata.create_all(sync_session.bind)
            )

        # 测试克隆独立性
        base_query = ChainUser.where('status', 'active')
        modified_query = base_query.where('age', '>', 25)

        # 原查询条件数量应该保持不变
        assert len(base_query._conditions) == 1
        assert len(modified_query._conditions) == 2

    @pytest.mark.asyncio
    async def test_session_type_detection(self, async_session, test_database):
        """测试会话类型检测"""
        # 创建表
        async with async_session.begin():
            await async_session.run_sync(
                lambda sync_session: ChainUser.metadata.create_all(sync_session.bind)
            )

        # 测试读操作使用读库
        read_builder = ChainUser.where('status', 'active')
        assert read_builder._get_session_type() == 'read'

        # 测试强制写库
        write_builder = ChainUser.where('status', 'active').force_write()
        assert write_builder._get_session_type() == 'write' 