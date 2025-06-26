"""
FastORM 事件系统完整演示

展示ThinkORM风格的生命周期事件处理：
- 自动事件触发（无需手动调用）
- 多种事件处理器定义方式
- 事件优先级和条件
- 状态追踪和验证
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from fastorm import FastORM
from fastorm.model import Model
from fastorm.mixins import TimestampMixin


# =================================================================
# 事件处理演示模型
# =================================================================

class User(Model, TimestampMixin):
    """用户模型 - 演示完整的事件生命周期"""
    
    __tablename__ = 'demo_users'
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='active')
    last_login: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # =================================================================
    # 方法1: 直接定义事件处理器（推荐）
    # =================================================================
    
    def on_before_insert(self):
        """新增前事件处理器"""
        print(f"🔔 before_insert: 准备创建用户 {self.name}")
        # 自动设置默认值
        if not hasattr(self, 'status') or not self.status:
            self.status = 'pending'
    
    def on_after_insert(self):
        """新增后事件处理器"""
        print(f"✅ after_insert: 用户 {self.name} 创建成功，ID: {self.id}")
    
    def on_before_update(self):
        """更新前事件处理器"""
        if self.is_dirty('email'):
            old_email = self.get_original_value('email')
            new_email = self.email
            print(f"🔄 before_update: 邮箱即将从 {old_email} 更改为 {new_email}")
        print(f"🔔 before_update: 准备更新用户 {self.name}")
    
    def on_after_update(self):
        """更新后事件处理器"""
        dirty_fields = self.get_dirty_fields()
        if dirty_fields:
            field_names = list(dirty_fields.keys())
            print(f"✅ after_update: 用户 {self.name} 更新完成，修改字段: {field_names}")
    
    def on_before_delete(self):
        """删除前事件处理器"""
        print(f"🗑️ before_delete: 准备删除用户 {self.name} (ID: {self.id})")
    
    def on_after_delete(self):
        """删除后事件处理器"""
        print(f"❌ after_delete: 用户 {self.name} 已被删除")


# =================================================================
# 方法2: 使用装饰器定义事件处理器
# =================================================================

@User.on_event('before_insert', priority=10)
def validate_user_data(user: User):
    """高优先级验证器"""
    if not user.email or '@' not in user.email:
        raise ValueError(f"无效的邮箱地址: {user.email}")
    print(f"🔍 validate_user_data: 邮箱 {user.email} 验证通过")


@User.on_event('after_insert', priority=5) 
def send_welcome_email(user: User):
    """发送欢迎邮件（模拟）"""
    print(f"📧 send_welcome_email: 向 {user.email} 发送欢迎邮件")


@User.on_event('before_update', condition=lambda u: u.is_dirty('email'))
def email_change_notification(user: User):
    """邮箱变更通知（仅当邮箱改变时触发）"""
    old_email = user.get_original_value('email')
    new_email = user.email
    print(f"📨 email_change_notification: 邮箱从 {old_email} 变更为 {new_email}")


# =================================================================
# 演示函数
# =================================================================

async def demo_lifecycle_events():
    """演示完整的模型生命周期事件"""
    
    print("🧪 FastORM 事件系统演示")
    print("=" * 50)
    
    # =================================================================
    # 1. 创建事件演示
    # =================================================================
    print("\n=== 1. 创建用户事件演示 ===")
    
    try:
        # 这将触发: before_insert -> after_insert 事件链
        user = await User.create(
            name="张三",
            email="zhangsan@example.com"
        )
        print(f"📊 创建结果: ID={user.id}, 状态={user.status}")
        
    except ValueError as e:
        print(f"❌ 验证失败: {e}")
        return
    
    # =================================================================
    # 2. 更新事件演示  
    # =================================================================
    print("\n=== 2. 更新用户事件演示 ===")
    
    # 更新单个字段
    await user.update(status='active')
    
    # 更新邮箱（会触发条件事件处理器）
    await user.update(email='zhangsan.new@example.com')
    
    # =================================================================
    # 3. 状态追踪演示
    # =================================================================
    print("\n=== 3. 状态追踪演示 ===")
    
    user2 = await User.create(name="李四", email="lisi@example.com")
    
    # 修改多个字段
    user2.name = "李四四"
    user2.status = "inactive"
    user2.last_login = datetime.now(timezone.utc)
    
    print("🔍 修改前检查:")
    print(f"   是否为新记录: {user2.is_new_record()}")
    print(f"   是否有修改: {user2.is_dirty()}")
    print(f"   修改的字段: {list(user2.get_dirty_fields().keys())}")
    
    # 保存修改（触发更新事件）
    await user2.save()
    
    # =================================================================
    # 4. 删除事件演示
    # =================================================================
    print("\n=== 4. 删除事件演示 ===")
    
    # 这将触发: before_delete -> after_delete 事件链
    await user2.delete()
    
    # =================================================================
    # 5. 批量操作演示
    # =================================================================
    print("\n=== 5. 批量操作演示 ===")
    
    users = []
    for i in range(3):
        # 每个create都会触发完整的事件链
        u = await User.create(
            name=f"用户{i+1}",
            email=f"user{i+1}@example.com"
        )
        users.append(u)
    
    print(f"📊 批量创建完成，共创建 {len(users)} 个用户")
    
    # =================================================================
    # 6. 事件优先级演示
    # =================================================================
    print("\n=== 6. 事件优先级演示 ===")
    print("观察事件触发顺序：")
    
    try:
        # 创建一个邮箱格式错误的用户（高优先级验证器会先执行）
        await User.create(name="无效用户", email="invalid-email")
    except ValueError as e:
        print(f"❌ 被验证器阻止: {e}")
    
    print("\n✅ 事件系统演示完成!")


async def main():
    """主函数"""
    # 初始化FastORM
    fastorm = FastORM("sqlite+aiosqlite:///events_demo.db")
    
    # 创建表
    await fastorm.create_all()
    
    try:
        # 运行演示
        await demo_lifecycle_events()
        
    finally:
        # 清理
        await fastorm.close()


if __name__ == "__main__":
    asyncio.run(main()) 