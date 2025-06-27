"""
FastORM 时间戳功能测试

测试内置到Model基类中的时间戳功能
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from fastorm import Model


class TimestampEnabledUser(Model):
    """启用时间戳的用户模型（默认已启用）"""
    __tablename__ = "timestamp_users"
    
    # 时间戳默认已启用，无需显式设置
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class CustomTimestampUser(Model):
    """自定义时间戳字段名的用户模型"""
    __tablename__ = "custom_timestamp_users"
    
    # 启用时间戳并自定义字段名
    timestamps = True
    created_at_column = "created_time"
    updated_at_column = "updated_time"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class NoTimestampUser(Model):
    """不启用时间戳的用户模型"""
    __tablename__ = "no_timestamp_users"
    
    # 不启用时间戳（默认行为）
    timestamps = False
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class TestTimestamps:
    """时间戳功能测试类"""

    @pytest.mark.asyncio
    async def test_timestamps_enabled(self, async_session):
        """测试启用时间戳的模型"""
        # 创建表
        async with async_session.begin():
            await async_session.run_sync(
                lambda sync_session: TimestampEnabledUser.metadata.create_all(sync_session.bind)
            )

        # 测试创建记录
        user = TimestampEnabledUser(name="John", email="john@example.com")
        
        # 检查时间戳是否启用
        assert user.is_timestamps_enabled() is True
        
        # 创建前时间戳应该为空
        assert user.get_created_at() is None
        assert user.get_updated_at() is None
        
        # 手动调用时间戳处理
        user._before_create_timestamp()
        
        # 检查时间戳是否已设置
        created_at = user.get_created_at()
        updated_at = user.get_updated_at()
        
        assert created_at is not None
        assert updated_at is not None
        assert isinstance(created_at, datetime)
        assert isinstance(updated_at, datetime)
        
        # 检查时间戳字段是否存在
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')

    @pytest.mark.asyncio  
    async def test_custom_timestamp_columns(self, async_session):
        """测试自定义时间戳字段名"""
        user = CustomTimestampUser(name="Jane", email="jane@example.com")
        
        # 检查时间戳是否启用
        assert user.is_timestamps_enabled() is True
        
        # 检查自定义字段名
        assert user.created_at_column == "created_time"
        assert user.updated_at_column == "updated_time"
        
        # 手动调用时间戳处理
        user._before_create_timestamp()
        
        # 检查自定义字段是否设置
        assert user.get_created_at() is not None
        assert user.get_updated_at() is not None

    @pytest.mark.asyncio
    async def test_timestamps_disabled(self, async_session):
        """测试关闭时间戳的模型"""
        user = NoTimestampUser(name="Bob", email="bob@example.com")
        
        # 检查时间戳是否关闭
        assert user.is_timestamps_enabled() is False
        
        # 时间戳方法应该返回None
        assert user.get_created_at() is None
        assert user.get_updated_at() is None
        
        # 调用时间戳处理不应该有效果
        user._before_create_timestamp()
        user._before_update_timestamp()
        
        assert user.get_created_at() is None
        assert user.get_updated_at() is None

    @pytest.mark.asyncio
    async def test_global_timestamps_control(self, async_session):
        """测试全局时间戳控制"""
        # 保存原始状态
        original_state = Model._get_global_timestamps_enabled()
        
        try:
            # 全局关闭时间戳
            Model.set_global_timestamps(False)
            
            user = TimestampEnabledUser(name="Test", email="test@example.com")
            assert user.is_timestamps_enabled() is False
            
            # 全局启用时间戳
            Model.set_global_timestamps(True)
            
            user2 = TimestampEnabledUser(name="Test2", email="test2@example.com")
            assert user2.is_timestamps_enabled() is True
            
        finally:
            # 恢复原始状态
            Model.set_global_timestamps(original_state)

    @pytest.mark.asyncio
    async def test_manual_timestamp_methods(self, async_session):
        """测试手动时间戳方法"""
        user = TimestampEnabledUser(name="Manual", email="manual@example.com")
        
        # 手动设置时间戳
        now = datetime.now(timezone.utc)
        user.set_created_at(now)
        user.set_updated_at(now)
        
        assert user.get_created_at() == now
        assert user.get_updated_at() == now
        
        # 测试touch方法
        import time
        original_updated = user.get_updated_at()
        time.sleep(0.01)  # 添加小延迟确保时间不同
        user.touch()
        new_updated = user.get_updated_at()
        
        assert new_updated > original_updated

    @pytest.mark.asyncio
    async def test_update_timestamp_behavior(self, async_session):
        """测试更新时的时间戳行为"""
        user = TimestampEnabledUser(name="Update", email="update@example.com")
        
        # 初始化时间戳
        user._before_create_timestamp()
        original_created = user.get_created_at()
        original_updated = user.get_updated_at()
        
        # 模拟更新
        import time
        time.sleep(0.01)  # 添加小延迟确保时间不同
        user._before_update_timestamp()
        
        # created_at 不应该改变
        assert user.get_created_at() == original_created
        
        # updated_at 应该更新
        assert user.get_updated_at() > original_updated

    def test_timestamp_configuration_inheritance(self):
        """测试时间戳配置的继承"""
        
        class BaseUserWithTimestamps(Model):
            __abstract__ = True
            timestamps = True
            
        class InheritedUser(BaseUserWithTimestamps):
            __tablename__ = "inherited_users"
            
            id: Mapped[int] = mapped_column(Integer, primary_key=True)
            name: Mapped[str] = mapped_column(String(100))
        
        user = InheritedUser(name="Inherited")
        assert user.is_timestamps_enabled() is True

    def test_timestamp_field_access(self):
        """测试时间戳字段的访问"""
        user = TimestampEnabledUser(name="Field", email="field@example.com")
        
        # 初始化时间戳
        user._before_create_timestamp()
        
        # 直接访问字段
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
        assert user.created_at is not None
        assert user.updated_at is not None 