"""
独立软删除功能演示

使用现有的数据库和模型演示软删除功能
"""
import asyncio
from typing import Optional

from sqlalchemy import String, Integer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from fastorm.model.model import Model
from fastorm.mixins.soft_delete import SoftDeleteMixin
from fastorm.mixins.timestamps import TimestampMixin
from fastorm.core.fastorm import FastORM


class SoftUser(SoftDeleteMixin, TimestampMixin, Model):
    """支持软删除的用户模型"""
    __tablename__ = 'soft_users'
    
    # 启用软删除
    soft_delete: bool = True
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


async def test_soft_delete_functionality():
    """测试软删除功能"""
    print("🧪 软删除功能独立测试")
    print("=" * 40)
    
    # 设置数据库
    engine = create_async_engine(
        "sqlite+aiosqlite:///soft_delete_standalone.db",
        echo=False  # 减少日志输出
    )
    
    # 设置FastORM
    fastorm = FastORM(
        database_url="sqlite+aiosqlite:///soft_delete_standalone.db",
        echo=False
    )
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)
        await conn.run_sync(Model.metadata.create_all)
    
    try:
        print("\n=== 1. 创建测试数据 ===")
        # 创建用户
        user1 = await SoftUser.create(name="张三", email="zhang@test.com", age=25)
        user2 = await SoftUser.create(name="李四", email="li@test.com", age=30)
        user3 = await SoftUser.create(name="王五", email="wang@test.com", age=35)
        
        print(f"✅ 创建用户: {user1.name}, {user2.name}, {user3.name}")
        
        # 验证总数
        total_users = await SoftUser.count()
        print(f"📊 当前用户总数: {total_users}")
        
        print("\n=== 2. 测试软删除查询方法 ===")
        
        # 测试 with_trashed()
        try:
            all_users_with_trashed = await SoftUser.with_trashed().get()
            print(f"✅ with_trashed(): {len(all_users_with_trashed)} 个用户")
        except Exception as e:
            print(f"❌ with_trashed() 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 only_trashed()  
        try:
            only_trashed_users = await SoftUser.only_trashed().get()
            print(f"✅ only_trashed(): {len(only_trashed_users)} 个用户")
        except Exception as e:
            print(f"❌ only_trashed() 失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试 without_trashed()
        try:
            without_trashed_users = await SoftUser.without_trashed().get()
            print(f"✅ without_trashed(): {len(without_trashed_users)} 个用户")
        except Exception as e:
            print(f"❌ without_trashed() 失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n=== 3. 执行软删除操作 ===")
        
        # 软删除一个用户
        print(f"🗑️ 软删除用户: {user1.name}")
        await user1.delete()
        
        print(f"   删除状态: {user1.is_deleted()}")
        print(f"   删除时间: {user1.get_deleted_at()}")
        
        print("\n=== 4. 软删除后查询验证 ===")
        
        # 默认查询（应该排除已删除）
        default_users = await SoftUser.query().get()
        print(f"📊 默认查询用户数: {len(default_users)}")
        
        # 包含已删除的查询
        all_users = await SoftUser.with_trashed().get()
        print(f"📊 包含已删除用户数: {len(all_users)}")
        
        # 仅已删除的查询
        deleted_users = await SoftUser.only_trashed().get()
        print(f"📊 仅已删除用户数: {len(deleted_users)}")
        
        # 显示每个用户的状态
        print("\n用户状态详情:")
        for user in all_users:
            status = "❌ 已删除" if user.is_deleted() else "✅ 活跃"
            print(f"  - {user.name}: {status}")
        
        print("\n=== 5. 测试恢复功能 ===")
        
        if deleted_users:
            user_to_restore = deleted_users[0]
            print(f"🔄 恢复用户: {user_to_restore.name}")
            
            await user_to_restore.restore()
            print("✅ 恢复完成")
            print(f"   删除状态: {user_to_restore.is_deleted()}")
            
            # 验证恢复结果
            active_users_after_restore = await SoftUser.query().get()
            print(f"📊 恢复后活跃用户数: {len(active_users_after_restore)}")
        
        print("\n=== 6. 测试物理删除 ===")
        
        # 再次软删除并物理删除
        await user2.delete()  # 先软删除
        print(f"🗑️ 软删除用户: {user2.name}")
        
        await user2.force_delete()  # 再物理删除
        print(f"💥 物理删除用户: {user2.name}")
        
        # 最终统计
        final_all = await SoftUser.with_trashed().get()
        final_active = await SoftUser.query().get()
        final_deleted = await SoftUser.only_trashed().get()
        
        print(f"\n📊 最终统计:")
        print(f"   总用户数: {len(final_all)}")
        print(f"   活跃用户数: {len(final_active)}")
        print(f"   已删除用户数: {len(final_deleted)}")
        
        print("\n✅ 软删除功能测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_soft_delete_functionality()) 