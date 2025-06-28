"""
调试软删除功能
"""

import asyncio
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from fastorm import Model, FastORM


class DebugSoftDeleteUser(Model):
    """调试软删除用户模型"""
    __tablename__ = "debug_soft_delete_users"
    
    # 启用软删除功能
    soft_delete = True
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


async def debug_soft_delete():
    """调试软删除功能"""
    # 初始化FastORM
    fastorm = FastORM()
    await fastorm.init(
        database_url="sqlite+aiosqlite:///debug_test.db",
        echo=True  # 打印SQL语句
    )
    
    # 创建表
    await fastorm.create_tables()
    
    print("=== 创建用户 ===")
    user = await DebugSoftDeleteUser.create(
        name="Debug User",
        email="debug@test.com"
    )
    print(f"Created user: {user.id}, deleted_at: {user.deleted_at}")
    print(f"Is deleted: {user.is_deleted()}")
    
    print("\n=== 软删除前查询 ===")
    found_user = await DebugSoftDeleteUser.find(user.id)
    print(f"Found user before delete: {found_user}")
    
    print("\n=== 执行软删除 ===")
    await user.delete()
    print(f"After delete - deleted_at: {user.deleted_at}")
    print(f"Is deleted: {user.is_deleted()}")
    
    print("\n=== 软删除后查询 ===")
    found_user = await DebugSoftDeleteUser.find(user.id)
    print(f"Found user after delete: {found_user}")
    
    print("\n=== 使用with_trashed查询 ===")
    try:
        trashed_user = await DebugSoftDeleteUser.with_trashed().where('id', user.id).first()
        print(f"Found with with_trashed: {trashed_user}")
    except Exception as e:
        print(f"Error with with_trashed: {e}")
    
    print("\n=== 使用普通where查询 ===")
    try:
        where_user = await DebugSoftDeleteUser.where('id', user.id).first()
        print(f"Found with where: {where_user}")
    except Exception as e:
        print(f"Error with where: {e}")
        
    # 关闭连接
    await fastorm.close()


if __name__ == "__main__":
    asyncio.run(debug_soft_delete()) 