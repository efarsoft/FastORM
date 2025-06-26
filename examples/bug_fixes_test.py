"""
FastORM 第五阶段 Bug修复验证测试

测试修复的问题：
1. 事件重复触发
2. 状态追踪问题  
3. 异常处理改进
4. 类型支持
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from fastorm import FastORM
from fastorm.model import Model
from fastorm.mixins import TimestampMixin


# =================================================================
# 测试模型
# =================================================================

class User(Model, TimestampMixin):
    """用户模型 - 用于测试事件系统修复"""
    
    __tablename__ = 'bug_test_users'
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='active')
    last_login: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    def __init__(self, *args, **kwargs):
        """测试状态管理初始化"""
        super().__init__(*args, **kwargs)
        self.event_log = []  # 记录事件触发历史
    
    # =================================================================
    # 事件处理器 - 记录触发次数
    # =================================================================
    
    def on_before_insert(self):
        """新增前事件处理器"""
        self.event_log.append(f"before_insert: {datetime.now()}")
        print(f"📝 before_insert: 准备创建用户 {self.name}")
    
    def on_after_insert(self):
        """新增后事件处理器"""
        self.event_log.append(f"after_insert: {datetime.now()}")
        print(f"✅ after_insert: 用户 {self.name} 创建成功，ID: {self.id}")
    
    def on_before_update(self):
        """更新前事件处理器"""
        self.event_log.append(f"before_update: {datetime.now()}")
        dirty_fields = self.get_dirty_fields()
        if dirty_fields:
            field_names = list(dirty_fields.keys())
            print(f"📝 before_update: 准备更新用户 {self.name}，修改字段: {field_names}")
    
    def on_after_update(self):
        """更新后事件处理器"""
        self.event_log.append(f"after_update: {datetime.now()}")
        print(f"✅ after_update: 用户 {self.name} 更新完成")
    
    def on_before_delete(self):
        """删除前事件处理器"""
        self.event_log.append(f"before_delete: {datetime.now()}")
        print(f"🗑️ before_delete: 准备删除用户 {self.name}")
    
    def on_after_delete(self):
        """删除后事件处理器"""
        self.event_log.append(f"after_delete: {datetime.now()}")
        print(f"❌ after_delete: 用户 {self.name} 已被删除")


# =================================================================
# 验证器事件处理器（测试异常处理）
# =================================================================

@User.on_event('before_insert', priority=10)
def validate_user_email(user: User):
    """邮箱验证器 - 测试异常处理"""
    if not user.email or '@' not in user.email:
        raise ValueError(f"无效的邮箱地址: {user.email}")
    print(f"🔍 validate_user_email: 邮箱 {user.email} 验证通过")


@User.on_event('after_insert', priority=5) 
def send_welcome_email(user: User):
    """发送欢迎邮件 - 测试非关键事件异常"""
    if user.email == 'error@test.com':
        raise RuntimeError("邮件服务器异常")
    print(f"📧 send_welcome_email: 向 {user.email} 发送欢迎邮件")


# =================================================================
# 测试函数
# =================================================================

async def test_event_duplicate_fix():
    """测试事件重复触发修复"""
    print("\n=== 1. 测试事件重复触发修复 ===")
    
    # 创建用户
    user = await User.create(
        name="测试用户1",
        email="test1@example.com"
    )
    
    # 检查事件触发次数
    insert_events = [log for log in user.event_log if 'insert' in log]
    print(f"📊 插入事件触发次数: {len(insert_events)}")
    for event in insert_events:
        print(f"   - {event}")
    
    # 使用update方法更新
    print("\n--- 使用update()方法更新 ---")
    await user.update(name="测试用户1更新", status="inactive")
    
    # 检查更新事件触发次数
    update_events = [log for log in user.event_log if 'update' in log]
    print(f"📊 更新事件触发次数: {len(update_events)}")
    for event in update_events:
        print(f"   - {event}")
    
    # 验证修复：每种事件应该只触发一次
    before_update_count = sum(
        1 for log in update_events if 'before_update' in log
    )
    after_update_count = sum(
        1 for log in update_events if 'after_update' in log
    )
    
    if before_update_count == 1 and after_update_count == 1:
        print("✅ 事件重复触发问题已修复！")
    else:
        print(
            f"❌ 事件重复触发问题未修复: "
            f"before={before_update_count}, after={after_update_count}"
        )
    
    return user


async def test_state_tracking_fix():
    """测试状态追踪修复"""
    print("\n=== 2. 测试状态追踪修复 ===")
    
    # 创建用户
    user = await User.create(
        name="状态测试用户",
        email="state@example.com"
    )
    
    # 测试脏检查
    print("\n--- 修改前状态检查 ---")
    print(f"   是否为新记录: {user.is_new_record()}")
    print(f"   是否有修改: {user.is_dirty()}")
    print(f"   修改的字段: {user.get_dirty_fields()}")
    
    # 修改字段
    user.name = "状态测试用户修改"
    user.status = "modified"
    
    print("\n--- 修改后状态检查 ---")
    print(f"   是否有修改: {user.is_dirty()}")
    dirty_fields = user.get_dirty_fields()
    print(f"   修改的字段: {list(dirty_fields.keys())}")
    
    # 验证修复：应该只显示真正修改的字段
    expected_dirty = {'name', 'status'}
    actual_dirty = set(dirty_fields.keys())
    
    if expected_dirty.issubset(actual_dirty):
        print("✅ 状态追踪正常工作！")
    else:
        print(f"❌ 状态追踪问题: 期望 {expected_dirty}, 实际 {actual_dirty}")
    
    # 保存并重新检查
    await user.save()
    
    print("\n--- 保存后状态检查 ---")
    print(f"   是否有修改: {user.is_dirty()}")
    print(f"   修改的字段: {user.get_dirty_fields()}")
    
    return user


async def test_exception_handling():
    """测试异常处理改进"""
    print("\n=== 3. 测试异常处理改进 ===")
    
    # 测试验证器异常（应该中断操作）
    print("\n--- 测试验证器异常 ---")
    try:
        await User.create(
            name="无效用户",
            email="invalid-email"  # 无效邮箱
        )
        print("❌ 验证器异常未正确处理")
    except (ValueError, RuntimeError) as e:
        print(f"✅ 验证器异常正确处理: {e}")
    
    # 测试非关键事件异常（不应该中断操作）
    print("\n--- 测试非关键事件异常 ---")
    try:
        user = await User.create(
            name="异常测试用户",
            email="error@test.com"  # 会触发邮件服务异常
        )
        print(f"✅ 用户创建成功，非关键事件异常未中断操作: {user.name}")
    except Exception as e:
        print(f"❌ 非关键事件异常意外中断操作: {e}")


async def test_multiple_instances():
    """测试多实例状态隔离"""
    print("\n=== 4. 测试多实例状态隔离 ===")
    
    # 创建多个用户实例
    user1 = await User.create(name="用户1", email="user1@example.com")
    user2 = await User.create(name="用户2", email="user2@example.com")
    
    # 修改不同字段
    user1.name = "用户1修改"
    user2.status = "modified"
    
    # 检查状态隔离
    user1_dirty = user1.get_dirty_fields()
    user2_dirty = user2.get_dirty_fields()
    
    print(f"用户1修改字段: {list(user1_dirty.keys())}")
    print(f"用户2修改字段: {list(user2_dirty.keys())}")
    
    # 验证状态不互相影响
    if 'name' in user1_dirty and 'name' not in user2_dirty:
        if 'status' in user2_dirty and 'status' not in user1_dirty:
            print("✅ 多实例状态隔离正常！")
        else:
            print("❌ 用户2状态异常")
    else:
        print("❌ 用户1状态异常")


async def main():
    """主测试函数"""
    print("🧪 FastORM 第五阶段 Bug修复验证测试")
    print("=" * 60)
    
    # 初始化FastORM
    fastorm = FastORM("sqlite+aiosqlite:///bug_fixes_test.db")
    
    # 创建表
    await fastorm.create_all()
    
    try:
        # 运行所有测试
        await test_event_duplicate_fix()
        await test_state_tracking_fix()
        await test_exception_handling()
        await test_multiple_instances()
        
        print("\n" + "=" * 60)
        print("✅ 第五阶段 Bug修复验证测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        raise
    finally:
        # 清理
        await fastorm.close()


if __name__ == "__main__":
    asyncio.run(main()) 