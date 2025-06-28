"""
FastORM 软删除功能测试

测试软删除功能的各种场景。
"""

import pytest
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from fastorm import Model


class SoftDeleteUser(Model):
    """软删除测试用户模型"""
    __tablename__ = "soft_delete_users"
    
    # 启用软删除功能
    soft_delete = True
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")


class RegularUser(Model):
    """普通用户模型（未启用软删除）"""
    __tablename__ = "regular_users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class TestSoftDelete:
    """软删除功能测试类"""

    @pytest.mark.asyncio
    async def test_soft_delete_model_has_deleted_at_field(self, test_database):
        """测试软删除模型具有deleted_at字段"""
        # 创建软删除用户
        user = await SoftDeleteUser.create(
            name="Test User", 
            email="test@softdelete.com"
        )
        
        # 检查deleted_at字段存在且为None
        assert hasattr(user, 'deleted_at')
        assert user.deleted_at is None
        assert not user.is_deleted()
        assert user.is_not_deleted()

    @pytest.mark.asyncio
    async def test_soft_delete_operation(self, test_database):
        """测试软删除操作"""
        # 创建用户
        user = await SoftDeleteUser.create(
            name="To Delete", 
            email="delete@softdelete.com"
        )
        original_id = user.id
        
        # 执行软删除
        await user.delete()
        
        # 检查软删除状态
        assert user.is_deleted()
        assert user.deleted_at is not None
        
        # 普通查询应该找不到已删除的记录
        found_user = await SoftDeleteUser.find(original_id)
        assert found_user is None
        
        # 使用with_trashed可以找到已删除的记录
        trashed_user = await SoftDeleteUser.with_trashed().where('id', original_id).first()
        assert trashed_user is not None
        assert trashed_user.is_deleted()

    @pytest.mark.asyncio
    async def test_restore_soft_deleted_record(self, test_database):
        """测试恢复软删除的记录"""
        # 创建并软删除用户
        user = await SoftDeleteUser.create(
            name="To Restore", 
            email="restore@softdelete.com"
        )
        await user.delete()
        assert user.is_deleted()
        
        # 恢复记录
        await user.restore()
        
        # 检查恢复状态
        assert not user.is_deleted()
        assert user.deleted_at is None
        
        # 普通查询应该能找到恢复的记录
        found_user = await SoftDeleteUser.find(user.id)
        assert found_user is not None
        assert not found_user.is_deleted()

    @pytest.mark.asyncio
    async def test_force_delete_operation(self, test_database):
        """测试强制物理删除"""
        # 创建用户
        user = await SoftDeleteUser.create(
            name="To Force Delete", 
            email="forcedelete@softdelete.com"
        )
        original_id = user.id
        
        # 执行强制删除
        await user.force_delete()
        
        # 任何查询都应该找不到记录
        found_user = await SoftDeleteUser.find(original_id)
        assert found_user is None
        
        trashed_user = await SoftDeleteUser.with_trashed().where('id', original_id).first()
        assert trashed_user is None

    @pytest.mark.asyncio
    async def test_with_trashed_query(self, test_database):
        """测试with_trashed查询"""
        # 创建两个用户
        user1 = await SoftDeleteUser.create(name="Active User", email="active@test.com")
        user2 = await SoftDeleteUser.create(name="Deleted User", email="deleted@test.com")
        
        # 软删除一个用户
        await user2.delete()
        
        # 普通查询只能找到活跃用户
        active_users = await SoftDeleteUser.all()
        active_names = [u.name for u in active_users]
        assert "Active User" in active_names
        assert "Deleted User" not in active_names
        
        # with_trashed查询能找到所有用户
        all_users = await SoftDeleteUser.with_trashed().get()
        all_names = [u.name for u in all_users]
        assert "Active User" in all_names
        assert "Deleted User" in all_names

    @pytest.mark.asyncio
    async def test_only_trashed_query(self, test_database):
        """测试only_trashed查询"""
        # 创建两个用户
        user1 = await SoftDeleteUser.create(name="Active User 2", email="active2@test.com")
        user2 = await SoftDeleteUser.create(name="Deleted User 2", email="deleted2@test.com")
        
        # 软删除一个用户
        await user2.delete()
        
        # only_trashed查询只能找到已删除用户
        deleted_users = await SoftDeleteUser.only_trashed().get()
        deleted_names = [u.name for u in deleted_users]
        assert "Deleted User 2" in deleted_names
        assert "Active User 2" not in deleted_names

    @pytest.mark.asyncio
    async def test_without_trashed_query(self, test_database):
        """测试without_trashed查询（默认行为）"""
        # 创建两个用户
        user1 = await SoftDeleteUser.create(name="Active User 3", email="active3@test.com")
        user2 = await SoftDeleteUser.create(name="Deleted User 3", email="deleted3@test.com")
        
        # 软删除一个用户
        await user2.delete()
        
        # without_trashed查询只能找到活跃用户（默认行为）
        active_users = await SoftDeleteUser.without_trashed().get()
        active_names = [u.name for u in active_users]
        assert "Active User 3" in active_names
        assert "Deleted User 3" not in active_names

    @pytest.mark.asyncio
    async def test_regular_model_without_soft_delete(self, test_database):
        """测试普通模型（未启用软删除）的行为"""
        # 创建普通用户
        user = await RegularUser.create(name="Regular User", email="regular@test.com")
        original_id = user.id
        
        # 普通删除应该是物理删除
        await user.delete()
        
        # 记录应该完全消失
        found_user = await RegularUser.find(original_id)
        assert found_user is None
        
        # with_trashed对普通模型应该返回普通查询构建器
        all_users = await RegularUser.with_trashed().get()
        # 不应该包含已删除的用户
        user_ids = [u.id for u in all_users]
        assert original_id not in user_ids

    @pytest.mark.asyncio
    async def test_soft_delete_error_handling(self, test_database):
        """测试软删除错误处理"""
        # 测试对未启用软删除的模型调用only_trashed
        with pytest.raises(ValueError, match="未启用软删除功能"):
            await RegularUser.only_trashed().get()
        
        # 测试恢复未删除的记录
        user = await SoftDeleteUser.create(name="Not Deleted", email="notdeleted@test.com")
        with pytest.raises(ValueError, match="记录未被删除，无需恢复"):
            await user.restore()

    @pytest.mark.asyncio
    async def test_soft_delete_with_force_parameter(self, test_database):
        """测试delete方法的force参数"""
        # 创建用户
        user = await SoftDeleteUser.create(name="Force Test", email="force@test.com")
        original_id = user.id
        
        # 使用force=True进行物理删除
        await user.delete(force=True)
        
        # 记录应该完全消失
        found_user = await SoftDeleteUser.find(original_id)
        assert found_user is None
        
        trashed_user = await SoftDeleteUser.with_trashed().where('id', original_id).first()
        assert trashed_user is None 