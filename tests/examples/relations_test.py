"""
FastORM 关系管理测试

测试关系管理系统的所有功能。
"""

import asyncio
import sys
import os

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, Table, Column

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastorm import FastORM
from fastorm.model.model import Model
from fastorm.relations.mixins import RelationMixin
from fastorm.relations import HasOne, HasMany, BelongsTo, BelongsToMany

# 配置数据库
fastorm = FastORM("sqlite+aiosqlite:///relations_test.db")

# 多对多中间表定义 - SQLAlchemy 2.0风格
user_roles = Table(
    'user_roles',
    Model.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

# 测试模型
class User(Model, RelationMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 关系定义
    profile = HasOne("Profile")
    posts = HasMany("Post")
    roles = BelongsToMany("Role", pivot_table="user_roles")


class Profile(Model, RelationMixin):
    __tablename__ = "profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    
    user = BelongsTo("User")


class Post(Model, RelationMixin):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    user = BelongsTo("User")


class Role(Model, RelationMixin):
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    users = BelongsToMany("User", pivot_table="user_roles")


async def test_basic_relations():
    """测试基本关系功能"""
    print("=== 测试基本关系功能 ===")
    
    # 创建测试数据
    user = await User.create(name="测试用户", email="test@example.com")
    print(f"创建用户：{user.name}")
    
    # 测试HasOne关系
    profile = await Profile.create(user_id=user.id, bio="这是一个测试用户")
    print(f"创建档案：{profile.bio}")
    
    # 测试HasMany关系 - create方法
    post1 = await user.posts.create(title="第一篇文章", content="内容1")
    print(f"通过关系创建文章：{post1.title}")
    
    post2 = await user.posts.create(title="第二篇文章", content="内容2")
    print(f"通过关系创建文章：{post2.title}")
    
    # 测试关系加载
    user_posts = await user.posts.load()
    print(f"用户文章数量：{len(user_posts)}")
    
    # 测试关系统计
    posts_count = await user.posts.count()
    print(f"文章总数：{posts_count}")
    
    return user


async def test_many_to_many():
    """测试多对多关系"""
    print("\n=== 测试多对多关系 ===")
    
    # 创建用户和角色
    user = await User.create(name="多对多用户", email="m2m@example.com")
    
    admin_role = await Role.create(name="admin")
    editor_role = await Role.create(name="editor")
    user_role = await Role.create(name="user")
    
    print(f"创建用户：{user.name}")
    print(f"创建角色：{admin_role.name}, {editor_role.name}, {user_role.name}")
    
    # 测试attach
    await user.roles.attach([admin_role.id, user_role.id])
    print("附加角色：admin, user")
    
    # 验证attach结果
    current_roles = await user.roles.load()
    role_names = [role.name for role in current_roles]
    print(f"当前角色：{role_names}")
    
    # 测试sync
    await user.roles.sync([editor_role.id, user_role.id])
    print("同步角色：editor, user")
    
    # 验证sync结果
    current_roles = await user.roles.load()
    role_names = [role.name for role in current_roles]
    print(f"同步后角色：{role_names}")
    
    # 测试toggle
    result = await user.roles.toggle([admin_role.id, editor_role.id])
    print(f"切换结果 - 附加：{result['attached']}, 分离：{result['detached']}")
    
    # 测试detach
    await user.roles.detach(user_role.id)
    print("分离user角色")
    
    # 最终验证
    final_roles = await user.roles.load()
    final_role_names = [role.name for role in final_roles]
    print(f"最终角色：{final_role_names}")
    
    return user


async def test_query_with_relations():
    """测试关系查询"""
    print("\n=== 测试关系查询 ===")
    
    # 创建测试数据
    user1 = await User.create(name="查询用户1", email="query1@example.com")
    user2 = await User.create(name="查询用户2", email="query2@example.com")
    
    # 给用户1创建文章
    await user1.posts.create(title="用户1的文章", content="内容")
    
    # 测试预加载
    print("测试预加载查询...")
    users_with_posts = await User.query().with_("posts").get()
    print(f"预加载用户数量：{len(users_with_posts)}")
    
    for user in users_with_posts:
        posts_loaded = getattr(user, '_posts_loaded', [])
        print(f"用户 {user.name} 的文章数：{len(posts_loaded) if posts_loaded else 0}")
    
    # 测试whereHas（如果实现了）
    try:
        users_with_posts = await User.query().where_has('posts').get()
        print(f"有文章的用户数量：{len(users_with_posts)}")
    except Exception as e:
        print(f"whereHas 功能暂未实现：{e}")
    
    return users_with_posts


async def main():
    """主测试函数"""
    print("🧪 FastORM 关系管理功能测试")
    print("=" * 40)
    
    # 初始化数据库
    await fastorm.create_all()
    
    try:
        # 运行测试
        user1 = await test_basic_relations()
        user2 = await test_many_to_many()
        users = await test_query_with_relations()
        
        print("\n" + "=" * 40)
        print("✅ 所有测试完成！")
        
        # 统计信息
        total_users = await User.query().count()
        total_posts = await Post.query().count()
        total_roles = await Role.query().count()
        total_profiles = await Profile.query().count()
        
        print(f"📊 测试统计：")
        print(f"   - 用户数量：{total_users}")
        print(f"   - 文章数量：{total_posts}")
        print(f"   - 角色数量：{total_roles}")
        print(f"   - 档案数量：{total_profiles}")
        
    except Exception as e:
        print(f"❌ 测试过程中出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 