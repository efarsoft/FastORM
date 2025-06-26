"""
FastORM 快速开始示例

演示FastORM的基本用法和核心特性。
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

import fastorm
from fastorm import BaseModel, Database


# 1. 定义模型
class User(BaseModel):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    age: Mapped[Optional[int]]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Post(BaseModel):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
    user_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


async def main():
    """主函数演示FastORM用法"""
    
    # 2. 初始化数据库
    DATABASE_URL = "sqlite+aiosqlite:///./test.db"
    fastorm.init(DATABASE_URL, echo=True)
    
    # 3. 创建表（仅示例，生产环境请使用迁移工具）
    engine = Database.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    
    # 4. 使用数据库会话
    async with Database.session() as session:
        
        # 创建用户
        print("=== 创建用户 ===")
        user1 = await User.create(
            session,
            name="张三",
            email="zhang@example.com",
            age=25
        )
        print(f"创建用户: {user1.to_dict()}")
        
        user2 = await User.create(
            session,
            name="李四", 
            email="li@example.com",
            age=30
        )
        print(f"创建用户: {user2.to_dict()}")
        
        # 批量创建文章
        print("\n=== 创建文章 ===")
        post1 = await Post.create(
            session,
            title="FastORM入门",
            content="FastORM是一个现代化的Python ORM框架...",
            user_id=user1.id
        )
        
        post2 = await Post.create(
            session,
            title="SQLAlchemy 2.0新特性",
            content="SQLAlchemy 2.0带来了许多激动人心的新特性...",
            user_id=user1.id
        )
        
        post3 = await Post.create(
            session,
            title="异步编程最佳实践",
            content="在Python中使用异步编程可以显著提升性能...",
            user_id=user2.id
        )
        
        print(f"创建文章: {post1.title}")
        print(f"创建文章: {post2.title}")
        print(f"创建文章: {post3.title}")
        
        # 查询所有用户
        print("\n=== 查询所有用户 ===")
        all_users = await User.all(session)
        for user in all_users:
            print(f"用户: {user.name} ({user.email})")
        
        # 条件查询
        print("\n=== 条件查询 ===")
        young_users = await User.where("age", 25).get(session)
        for user in young_users:
            print(f"25岁用户: {user.name}")
        
        # 复杂查询
        print("\n=== 复杂查询 ===")
        adult_users = await User.query()\
            .where("age", 18)\
            .order_by("created_at", "desc")\
            .limit(10)\
            .get(session)
        
        print(f"成年用户数量: {len(adult_users)}")
        
        # 查询单个记录
        print("\n=== 查询单个记录 ===")
        user = await User.find(session, 1)
        if user:
            print(f"找到用户: {user.name}")
        
        # 分页查询
        print("\n=== 分页查询 ===")
        page_result = await Post.query().paginate(session, page=1, per_page=2)
        print(f"总文章数: {page_result['total']}")
        print(f"当前页: {page_result['page']}")
        print(f"总页数: {page_result['total_pages']}")
        for post in page_result['items']:
            print(f"文章: {post.title}")
        
        # 统计查询
        print("\n=== 统计查询 ===")
        user_count = await User.query().count(session)
        post_count = await Post.query().count(session)
        print(f"用户总数: {user_count}")
        print(f"文章总数: {post_count}")
        
        # 更新记录
        print("\n=== 更新记录 ===")
        user1.age = 26
        await user1.save(session)
        print(f"更新用户年龄: {user1.name} -> {user1.age}")
        
        # 删除记录
        print("\n=== 删除记录 ===")
        await post3.remove(session)
        print(f"删除文章: {post3.title}")
        
        # 验证删除
        remaining_posts = await Post.all(session)
        print(f"剩余文章数: {len(remaining_posts)}")
    
    # 5. 关闭数据库连接
    await Database.close()
    print("\n✅ 示例完成！")


if __name__ == "__main__":
    asyncio.run(main()) 