 #!/usr/bin/env python3
"""
FastORM 时间戳功能演示

展示内置在Model基类中的自动时间戳管理功能
"""

import asyncio
from datetime import datetime
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from fastorm import Model, Database


# =============================================================================
# 1. 基本时间戳使用
# =============================================================================

class User(Model):
    """用户模型 - 启用时间戳"""
    __tablename__ = "users"
    
    # 启用时间戳功能
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


# =============================================================================
# 2. 自定义时间戳字段名
# =============================================================================

class Post(Model):
    """文章模型 - 自定义时间戳字段名"""
    __tablename__ = "posts"
    
    # 启用时间戳并自定义字段名
    timestamps = True
    created_at_column = "created_time"  # 自定义创建时间字段名
    updated_at_column = "updated_time"  # 自定义更新时间字段名
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=True)


# =============================================================================
# 3. 不使用时间戳的模型
# =============================================================================

class Category(Model):
    """分类模型 - 不使用时间戳"""
    __tablename__ = "categories"
    
    # 明确关闭时间戳功能
    timestamps = False
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


async def main():
    """主演示函数"""
    print("🎯 FastORM 时间戳功能演示")
    print("=" * 60)
    
    # 初始化数据库（使用内存SQLite）
    await Database.init("sqlite+aiosqlite:///:memory:", echo=False)
    
    # 创建表
    await Database.create_tables()
    
    # =================================================================
    # 演示1：基本时间戳功能
    # =================================================================
    print("\n📅 演示1：基本时间戳功能")
    print("-" * 30)
    
    # 创建用户 - 自动设置时间戳
    user = await User.create(
        name="张三",
        email="zhangsan@example.com"
    )
    
    print(f"用户创建完成:")
    print(f"  ID: {user.id}")
    print(f"  姓名: {user.name}")
    print(f"  创建时间: {user.get_created_at()}")
    print(f"  更新时间: {user.get_updated_at()}")
    
    # 更新用户 - 自动更新时间戳
    await user.update(name="张三丰")
    
    print(f"\n用户更新后:")
    print(f"  姓名: {user.name}")
    print(f"  创建时间: {user.get_created_at()}")
    print(f"  更新时间: {user.get_updated_at()}")
    
    # =================================================================
    # 演示2：自定义时间戳字段名
    # =================================================================
    print("\n🔧 演示2：自定义时间戳字段名")
    print("-" * 30)
    
    post = await Post.create(
        title="FastORM使用指南",
        content="这是一篇关于FastORM的使用指南..."
    )
    
    print(f"文章创建完成:")
    print(f"  标题: {post.title}")
    print(f"  自定义创建时间字段 ({post.created_at_column}): {post.get_created_at()}")
    print(f"  自定义更新时间字段 ({post.updated_at_column}): {post.get_updated_at()}")
    
    # =================================================================
    # 演示3：不使用时间戳的模型
    # =================================================================
    print("\n❌ 演示3：不使用时间戳的模型")
    print("-" * 30)
    
    category = await Category.create(name="技术文章")
    
    print(f"分类创建完成:")
    print(f"  名称: {category.name}")
    print(f"  时间戳启用: {category.is_timestamps_enabled()}")
    print(f"  创建时间: {category.get_created_at()}")
    print(f"  更新时间: {category.get_updated_at()}")
    
    # =================================================================
    # 演示4：全局时间戳控制
    # =================================================================
    print("\n🌍 演示4：全局时间戳控制")
    print("-" * 30)
    
    # 全局关闭时间戳
    print("全局关闭时间戳...")
    Model.set_global_timestamps(False)
    
    # 即使模型启用了timestamps=True，也不会生效
    user2 = await User.create(
        name="李四",
        email="lisi@example.com"
    )
    
    print(f"全局关闭后创建的用户:")
    print(f"  时间戳启用: {user2.is_timestamps_enabled()}")
    print(f"  创建时间: {user2.get_created_at()}")
    
    # 重新启用全局时间戳
    print("\n重新启用全局时间戳...")
    Model.set_global_timestamps(True)
    
    user3 = await User.create(
        name="王五",
        email="wangwu@example.com"
    )
    
    print(f"全局重启后创建的用户:")
    print(f"  时间戳启用: {user3.is_timestamps_enabled()}")
    print(f"  创建时间: {user3.get_created_at()}")
    
    # =================================================================
    # 演示5：手动时间戳操作
    # =================================================================
    print("\n🔧 演示5：手动时间戳操作")
    print("-" * 30)
    
    # 手动更新时间戳
    print(f"touch前更新时间: {user3.get_updated_at()}")
    
    # 等待一小段时间以看到差别
    await asyncio.sleep(0.01)
    
    user3.touch()  # 手动更新时间戳
    await user3.save()
    
    print(f"touch后更新时间: {user3.get_updated_at()}")
    
    # =================================================================
    # 演示6：查询时间戳字段
    # =================================================================
    print("\n🔍 演示6：查询时间戳字段")
    print("-" * 30)
    
    # 查询最近创建的用户
    recent_users = await User.where('created_at', '>', 
                                  datetime.now().replace(hour=0, minute=0, second=0))\
                            .limit(3).get()
    
    print(f"今天创建的用户数量: {len(recent_users)}")
    for user in recent_users:
        print(f"  {user.name}: {user.get_created_at()}")
    
    print("\n🎉 时间戳功能演示完成！")
    print("=" * 60)
    
    # 清理
    await Database.close()


# =============================================================================
# 时间戳功能特性总结
# =============================================================================

def print_features():
    """打印时间戳功能特性"""
    print("\n📋 FastORM 时间戳功能特性:")
    print("✅ 1. 自动时间戳管理 - 无需手动维护created_at和updated_at")
    print("✅ 2. 模型级控制 - 每个模型可独立启用/关闭时间戳")
    print("✅ 3. 全局控制 - 可全局启用/关闭所有模型的时间戳功能")
    print("✅ 4. 自定义字段名 - 可自定义时间戳字段的名称")
    print("✅ 5. 自动创建字段 - 启用时间戳的模型自动添加时间戳字段")
    print("✅ 6. 事件集成 - 与Model的create/update方法无缝集成")
    print("✅ 7. 手动控制 - 提供touch()等方法手动操作时间戳")
    print("✅ 8. 类型安全 - 使用SQLAlchemy 2.0的类型系统")
    print("\n🎯 设计理念: 让复杂的事情变简单，让简单的事情变优雅")


if __name__ == "__main__":
    print_features()
    asyncio.run(main())