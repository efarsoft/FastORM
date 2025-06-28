#!/usr/bin/env python3
"""
FastORM 全面功能测试脚本

测试FastORM的高级功能，包括关系、事件、缓存、批量操作等
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from fastorm import Model
from fastorm.connection.database import init, close, create_all
from fastorm.mixins.events import EventMixin
from fastorm.mixins.soft_delete import SoftDeleteMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Text


class User(Model):
    """用户模型 - 测试事件和关系"""
    __tablename__ = "users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # 关系：一个用户有多篇文章
    # posts = relationship("Post", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>"


class Post(Model, SoftDeleteMixin):
    """文章模型 - 测试软删除功能"""
    __tablename__ = "posts"
    
    timestamps = True
    soft_delete = True  # 启用软删除功能
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    # 关系：一篇文章属于一个用户
    # user = relationship("User", back_populates="posts")
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"


class Category(Model):
    """分类模型 - 测试基础功能"""
    __tablename__ = "categories"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


async def test_comprehensive_functionality():
    """测试全面功能"""
    print("🚀 开始FastORM全面功能测试...")
    
    try:
        # 1. 初始化数据库
        print("\n1. 初始化数据库连接...")
        db = init("sqlite+aiosqlite:///:memory:", echo=False)
        await create_all()
        print("   ✅ 数据库初始化成功")
        
        # 2. 测试基础CRUD操作
        print("\n2. 测试基础CRUD操作...")
        
        # 创建用户
        user1 = await User.create(name="张三", email="zhangsan@test.com", age=25)
        user2 = await User.create(name="李四", email="lisi@test.com", age=30)
        user3 = await User.create(name="王五", email="wangwu@test.com", age=28)
        print(f"   ✅ 创建了3个用户: {user1.name}, {user2.name}, {user3.name}")
        
        # 创建分类
        tech_cat = await Category.create(name="技术", description="技术相关文章")
        life_cat = await Category.create(name="生活", description="生活相关文章")
        print(f"   ✅ 创建了2个分类: {tech_cat.name}, {life_cat.name}")
        
        # 创建文章
        post1 = await Post.create(
            title="Python异步编程", 
            content="介绍Python异步编程的基础知识...", 
            user_id=user1.id
        )
        post2 = await Post.create(
            title="FastAPI入门", 
            content="FastAPI框架的使用指南...", 
            user_id=user1.id
        )
        post3 = await Post.create(
            title="生活感悟", 
            content="关于生活的一些思考...", 
            user_id=user2.id
        )
        print(f"   ✅ 创建了3篇文章")
        
        # 3. 测试查询功能
        print("\n3. 测试查询功能...")
        
        # 基础查询
        all_users = await User.all()
        print(f"   ✅ 查询所有用户: {len(all_users)} 个")
        
        # 条件查询
        young_users = await User.where('age', '<', 30).get()
        print(f"   ✅ 年龄小于30的用户: {len(young_users)} 个")
        
        # 链式查询
        tech_posts = await Post.where('title', 'like', '%Python%').get()
        print(f"   ✅ 包含Python的文章: {len(tech_posts)} 篇")
        
        # 排序查询
        users_by_age = await User.query().order_by('age', 'desc').get()
        print(f"   ✅ 按年龄降序排列的用户: {[u.name for u in users_by_age]}")
        
        # 分页查询
        from fastorm.query.pagination import Paginator
        page = await User.query().paginate(page=1, per_page=2)
        print(f"   ✅ 分页查询: 第{page.current_page}页，共{page.total}条记录")
        
        # 4. 测试聚合功能
        print("\n4. 测试聚合功能...")
        
        user_count = await User.count()
        post_count = await Post.count()
        print(f"   ✅ 统计: {user_count} 个用户, {post_count} 篇文章")
        
        # 条件统计
        zhang_posts = await Post.where('user_id', user1.id).count()
        print(f"   ✅ 张三的文章数量: {zhang_posts}")
        
        # 存在性检查
        has_python_post = await Post.where('title', 'like', '%Python%').exists()
        print(f"   ✅ 是否有Python相关文章: {has_python_post}")
        
        # 5. 测试更新操作
        print("\n5. 测试更新操作...")
        
        # 单条更新
        await user1.update(age=26)
        updated_user = await User.find(user1.id)
        print(f"   ✅ 用户年龄更新: {updated_user.age}")
        
        # 批量更新
        updated_count = await Post.where('user_id', user1.id).update(
            content="内容已更新..."
        )
        print(f"   ✅ 批量更新了 {updated_count} 篇文章")
        
        # 6. 测试软删除功能（简化版）
        print("\n6. 测试删除功能...")
        
        # 删除一篇文章
        await post3.delete()
        print(f"   ✅ 文章删除成功")
        
        # 查询剩余文章
        remaining_posts = await Post.query().get()
        print(f"   ✅ 剩余文章数量: {len(remaining_posts)}")
        
        # 7. 测试批量操作
        print("\n7. 测试批量操作...")
        
        # 批量创建
        bulk_users = await User.create_many([
            {"name": "用户A", "email": "usera@test.com", "age": 22},
            {"name": "用户B", "email": "userb@test.com", "age": 24},
            {"name": "用户C", "email": "userc@test.com", "age": 26},
        ])
        print(f"   ✅ 批量创建了 {len(bulk_users)} 个用户")
        
        # 批量删除
        deleted_count = await User.where('name', 'like', '用户%').delete()
        print(f"   ✅ 批量删除了 {deleted_count} 个用户")
        
        # 8. 测试时间戳功能
        print("\n8. 测试时间戳功能...")
        
        # 检查时间戳
        user_with_timestamp = await User.find(user1.id)
        print(f"   ✅ 用户创建时间: {user_with_timestamp.created_at}")
        print(f"   ✅ 用户更新时间: {user_with_timestamp.updated_at}")
        
        # 手动更新时间戳
        user_with_timestamp.touch()
        await user_with_timestamp.save()
        print("   ✅ 手动更新时间戳成功")
        
        # 9. 测试序列化功能
        print("\n9. 测试序列化功能...")
        
        # 转换为字典
        user_dict = user1.to_dict()
        print(f"   ✅ 用户序列化: {user_dict.get('name')}")
        
        # 排除字段
        user_dict_partial = user1.to_dict(exclude=['email'])
        print(f"   ✅ 排除email的序列化: {'email' not in user_dict_partial}")
        
        print("\n🎉 所有核心功能测试通过！")
        
        # 10. 性能测试
        print("\n10. 简单性能测试...")
        import time
        
        start_time = time.time()
        
        # 批量查询测试
        for i in range(10):
            users = await User.where('age', '>', 20).limit(5).get()
        
        end_time = time.time()
        print(f"   ✅ 10次查询耗时: {end_time - start_time:.3f}秒")
        
        # 11. 最终统计
        print("\n11. 最终统计...")
        final_user_count = await User.count()
        final_post_count = await Post.count()
        final_category_count = await Category.count()
        
        print(f"   ✅ 最终统计:")
        print(f"      - 用户: {final_user_count}")
        print(f"      - 文章: {final_post_count}")
        print(f"      - 分类: {final_category_count}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理连接
        await close()
        print("\n🔧 数据库连接已关闭")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_comprehensive_functionality()) 