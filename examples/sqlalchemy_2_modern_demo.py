"""
FastORM SQLAlchemy 2.0 现代化Demo

展示FastORM对SQLAlchemy 2.0新语法和特性的完整支持。
"""

import asyncio
import sys
import os
from typing import List, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Integer, String, Text, DateTime, Boolean, ForeignKey, 
    Table, Column, Index, UniqueConstraint
)
from sqlalchemy.sql import func

from fastorm import FastORM
from fastorm.model.model import Model
from fastorm.relations.mixins import RelationMixin
from fastorm.relations import HasOne, HasMany, BelongsTo, BelongsToMany
from fastorm.mixins import TimestampMixin

# 配置数据库 - SQLAlchemy 2.0语法
fastorm = FastORM("sqlite+aiosqlite:///modern_demo.db")

# 多对多中间表 - SQLAlchemy 2.0风格
user_roles = Table(
    'user_roles',
    Model.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('assigned_at', DateTime, default=func.now()),
    # 添加索引优化
    Index('idx_user_roles_user_id', 'user_id'),
    Index('idx_user_roles_role_id', 'role_id'),
)


class User(Model, RelationMixin, TimestampMixin):
    """用户模型 - 完全使用SQLAlchemy 2.0语法"""
    __tablename__ = "users"
    
    # 启用时间戳
    timestamps = True
    
    # 主键和基本字段 - 使用Mapped[]类型注解
    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="用户ID")
    username: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        unique=True,
        comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        unique=True,
        comment="邮箱"
    )
    
    # 可选字段
    first_name: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True,
        comment="名字"
    )
    
    # 状态字段
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True,
        comment="是否激活"
    )
    
    # 关系定义 - Eloquent风格
    posts = HasMany("Post")
    roles = BelongsToMany("Role", pivot_table="user_roles")


class Role(Model, RelationMixin, TimestampMixin):
    """角色模型"""
    __tablename__ = "roles"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        unique=True,
        comment="角色名"
    )
    
    # 关系
    users = BelongsToMany("User", pivot_table="user_roles")


class Post(Model, RelationMixin, TimestampMixin):
    """文章模型"""
    __tablename__ = "posts"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id"),
        nullable=False,
        comment="作者ID"
    )
    
    # 内容字段
    title: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="标题"
    )
    content: Mapped[str] = mapped_column(Text, comment="内容")
    
    # 关系
    author = BelongsTo("User", foreign_key="user_id")


async def demo_sqlalchemy_2_features():
    """演示SQLAlchemy 2.0特性"""
    print("🚀 SQLAlchemy 2.0现代化特性演示")
    print("=" * 50)
    
    # 1. 创建用户
    print("1️⃣ 创建用户")
    user = await User.create(
        username="john_doe",
        email="john@example.com",
        first_name="John",
        is_active=True
    )
    print(f"✅ 创建用户: {user.username} (ID: {user.id})")
    print(f"   创建时间: {user.created_at}")
    
    # 2. 创建角色
    print("\n2️⃣ 创建角色系统")
    admin_role = await Role.create(
        name="admin"
    )
    editor_role = await Role.create(
        name="editor"
    )
    
    # 分配角色
    await user.roles.attach([admin_role.id, editor_role.id])
    user_roles = await user.roles.load()
    role_names = [role.name for role in user_roles]
    print(f"✅ 分配角色: {role_names}")
    
    # 3. 创建文章
    print("\n3️⃣ 创建文章")
    post = await Post.create(
        title="Getting Started with FastORM",
        content="FastORM is a modern Python ORM...",
        user_id=user.id
    )
    
    print(f"✅ 创建文章: {post.title}")
    
    # 4. 复杂查询演示
    print("\n4️⃣ 复杂查询演示")
    
    # 预加载关系
    posts_with_author = await Post.query().with_("author").get()
    print(f"✅ 预加载查询: {len(posts_with_author)} 篇文章")
    
    # 统计查询
    total_users = await User.query().count()
    total_posts = await Post.query().count()
    
    print(f"✅ 统计查询:")
    print(f"   用户总数: {total_users}")
    print(f"   文章总数: {total_posts}")
    
    return {
        'user': user,
        'post': post,
        'total_users': total_users,
        'total_posts': total_posts
    }


async def main():
    """主函数"""
    print("🧪 FastORM SQLAlchemy 2.0 现代化功能演示")
    print("=" * 60)
    
    # 初始化数据库
    await fastorm.create_all()
    
    try:
        # 运行演示
        result = await demo_sqlalchemy_2_features()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("\n📊 最终统计:")
        print(f"   - 用户总数: {result['total_users']}")
        print(f"   - 文章总数: {result['total_posts']}")
        print("\n🚀 FastORM已完美集成SQLAlchemy 2.0的现代化特性!")
        print("   ✅ Mapped[]类型注解")
        print("   ✅ 现代化关系管理")  
        print("   ✅ 自动时间戳")
        print("   ✅ 复杂查询构建")
        print("   ✅ 预加载优化")
        print("   ✅ Laravel风格API")
        print("   ✅ 字符串模型解析")
        print("   ✅ Registry集成")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 