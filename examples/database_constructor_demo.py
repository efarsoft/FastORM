"""
FastORM 纯构造式Database演示

演示新的纯构造式Database API - 简洁、明了、无混淆。
"""

import asyncio
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, select
from fastorm import Database, Model


class User(Model):
    """用户模型"""
    __tablename__ = "users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


async def single_database_demo():
    """单数据库演示"""
    print("🏗️ FastORM 纯构造式Database演示")
    print("=" * 50)
    
    # 🎯 纯构造式 - 简洁明了
    print("\n📦 单数据库初始化:")
    db = Database("sqlite+aiosqlite:///:memory:", echo=False)
    
    # 创建表
    print("正在创建表...")
    await db.create_all()
    print("✅ 表创建完成")
    
    # 查看连接信息
    info = db.get_connection_info()
    print(f"🔌 连接模式: {info['mode']}")
    print(f"🔌 可用引擎: {info['engines']}")
    
    # 写操作
    async with db.write_session() as session:
        user = User(name="张三", email="zhangsan@example.com")
        session.add(user)
        # write_session 自动提交
        print(f"👤 创建用户: {user.name}")
    
    # 读操作
    async with db.read_session() as session:
        result = await session.execute(
            select(User).where(User.name == "张三")
        )
        user = result.scalar_one_or_none()
        if user:
            print(f"🔍 查询到用户: {user.name} ({user.email})")
    
    # 事务操作
    async with db.transaction() as session:
        user = User(name="李四", email="lisi@example.com")
        session.add(user)
        await session.commit()  # 事务需要手动提交
        print(f"💾 事务创建用户: {user.name}")
    
    # 关闭连接
    await db.close()
    print("✅ 数据库连接已关闭")


async def read_write_split_demo():
    """读写分离演示"""
    print("\n🔀 读写分离演示:")
    print("=" * 30)
    
    # 读写分离配置
    config = {
        "write": "sqlite+aiosqlite:///master.db",
        "read": "sqlite+aiosqlite:///slave.db"
    }
    
    db = Database(config)
    await db.create_all()
    
    info = db.get_connection_info()
    print(f"✅ 连接模式: {info['mode']}")
    print(f"✅ 可用引擎: {info['engines']}")
    
    # 写操作（主库）
    async with db.write_session() as session:
        user = User(name="王五", email="wangwu@example.com")
        session.add(user)
        print("✅ 写操作完成（主库）")
    
    # 读操作（从库）
    async with db.read_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"✅ 读操作完成（从库），用户数: {len(users)}")
    
    await db.close()
    print("✅ 读写分离连接已关闭")


async def multiple_databases_demo():
    """多数据库实例演示"""
    print("\n🗃️ 多数据库实例演示:")
    print("=" * 30)
    
    # 创建多个数据库实例
    user_db = Database("sqlite+aiosqlite:///users.db", echo=False)
    log_db = Database("sqlite+aiosqlite:///logs.db", echo=False)
    
    await user_db.create_all()
    await log_db.create_all()
    
    print("✅ 两个数据库实例创建完成")
    
    # 在不同数据库中操作
    async with user_db.session() as session:
        user = User(name="赵六", email="zhaoliu@example.com")
        session.add(user)
        print("👤 用户数据写入 users.db")
    
    # 清理资源
    await user_db.close()
    await log_db.close()
    print("✅ 多数据库连接已关闭")


async def main():
    """主演示函数"""
    await single_database_demo()
    await read_write_split_demo()
    await multiple_databases_demo()
    
    print("\n🎉 所有演示完成！")
    print("\n💡 新API优势:")
    print("   ✅ 纯构造式 - 无静态方法困扰")
    print("   ✅ 职责清晰 - 一个实例管理一套连接")
    print("   ✅ 类型安全 - IDE友好，无歧义")
    print("   ✅ 资源管理 - 明确的生命周期")
    print("   ✅ 多实例 - 支持同时操作多个数据库")
    print("\n📖 基本用法:")
    print("   db = Database(url)      # 创建实例")
    print("   await db.create_all()   # 创建表")
    print("   async with db.session(): # 使用会话")
    print("   await db.close()        # 关闭连接")


if __name__ == "__main__":
    asyncio.run(main()) 