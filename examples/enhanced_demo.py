#!/usr/bin/env python3
"""
FastORM 增强演示

展示 FastORM 的所有核心功能，包括：
1. 简洁的API（ThinkORM级别）
2. 完整的Mixins系统（时间戳、软删除、批量赋值、事件）
3. 关系管理系统（一对一、一对多、多对多）
4. Laravel风格的关系操作（attach/detach/sync）
5. 关系查询（with预加载、whereHas等）
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from fastorm import FastORM
from fastorm.model.model import Model
from fastorm.mixins import TimestampMixin, SoftDeleteMixin, FillableMixin, EventMixin
from fastorm.relations import HasOne, HasMany, BelongsTo, BelongsToMany

# 配置数据库
fastorm = FastORM("sqlite+aiosqlite:///enhanced_demo.db")


# ===================================================================
# 模型定义 - 集成所有Mixins和关系
# ===================================================================

class User(Model, TimestampMixin, SoftDeleteMixin, FillableMixin, EventMixin):
    """用户模型 - 展示所有功能"""
    __tablename__ = "users"
    
    # 字段定义
    id: int
    name: str
    email: str
    age: Optional[int] = None
    status: str = "active"
    
    # 批量赋值控制
    fillable = ["name", "email", "age", "status"]
    hidden = ["deleted_at"]
    
    # 时间戳
    timestamps = True
    
    # 关系定义
    profile = HasOne("Profile", foreign_key="user_id")
    posts = HasMany("Post", foreign_key="user_id")
    roles = BelongsToMany("Role", pivot_table="user_roles", 
                         foreign_key="user_id", related_key="role_id")
    
    # 事件处理器
    def on_before_insert(self):
        print(f"用户 {self.name} 即将被创建")
    
    def on_after_insert(self):
        print(f"用户 {self.name} 已创建，ID: {self.id}")
    
    def on_before_update(self):
        print(f"用户 {self.name} 即将被更新")
    
    def on_after_update(self):
        print(f"用户 {self.name} 已更新")


class Profile(Model, TimestampMixin):
    """用户档案模型"""
    __tablename__ = "profiles"
    
    id: int
    user_id: int
    bio: Optional[str] = None
    avatar: Optional[str] = None
    website: Optional[str] = None
    
    timestamps = True
    
    # 反向关系
    user = BelongsTo("User", foreign_key="user_id")


class Post(Model, TimestampMixin, SoftDeleteMixin):
    """文章模型"""
    __tablename__ = "posts"
    
    id: int
    user_id: int
    title: str
    content: str
    published: bool = False
    published_at: Optional[datetime] = None
    
    timestamps = True
    
    # 关系
    user = BelongsTo("User", foreign_key="user_id")
    tags = BelongsToMany("Tag", pivot_table="post_tags",
                        foreign_key="post_id", related_key="tag_id")


class Role(Model):
    """角色模型"""
    __tablename__ = "roles"
    
    id: int
    name: str
    description: Optional[str] = None
    
    # 反向多对多关系
    users = BelongsToMany("User", pivot_table="user_roles",
                         foreign_key="role_id", related_key="user_id")


class Tag(Model):
    """标签模型"""
    __tablename__ = "tags"
    
    id: int
    name: str
    color: Optional[str] = None
    
    # 反向关系
    posts = BelongsToMany("Post", pivot_table="post_tags",
                         foreign_key="tag_id", related_key="post_id")


# ===================================================================
# 演示功能
# ===================================================================

async def demo_1_basic_crud():
    """演示1：基础CRUD - 展示简洁性"""
    print("\n=== 演示1：基础CRUD操作 ===")
    
    # 创建用户 - 无需session参数
    user = await User.create(
        name="张三",
        email="zhangsan@example.com",
        age=25,
        status="active"
    )
    print(f"创建用户：{user.name}, ID: {user.id}")
    
    # 查找用户
    found_user = await User.find(user.id)
    print(f"查找用户：{found_user.name}")
    
    # 更新用户
    found_user.age = 26
    await found_user.save()
    print(f"更新用户年龄：{found_user.age}")
    
    # 查询构建器
    active_users = await User.query().where("status", "active").get()
    print(f"活跃用户数量：{len(active_users)}")
    
    return user


async def demo_2_fillable_control():
    """演示2：批量赋值控制"""
    print("\n=== 演示2：批量赋值控制 ===")
    
    # 安全的批量赋值
    safe_data = {
        "name": "李四",
        "email": "lisi@example.com",
        "age": 30,
        "password": "secret123",  # 这个不在fillable中，会被过滤
        "admin": True             # 这个也会被过滤
    }
    
    user = await User.create(**safe_data)
    print(f"安全创建用户：{user.name}")
    print(f"过滤了不安全字段，只保留：{user.get_fillable_attributes()}")
    
    return user


async def demo_3_timestamps():
    """演示3：自动时间戳"""
    print("\n=== 演示3：自动时间戳管理 ===")
    
    user = await User.create(name="王五", email="wangwu@example.com")
    print(f"创建时间：{user.created_at}")
    print(f"更新时间：{user.updated_at}")
    
    # 稍等一下再更新
    await asyncio.sleep(0.1)
    
    user.age = 28
    await user.save()
    print(f"更新后时间：{user.updated_at}")
    
    # 手动触摸时间戳
    await user.touch()
    print(f"触摸后时间：{user.updated_at}")
    
    return user


async def demo_4_soft_delete():
    """演示4：软删除功能"""
    print("\n=== 演示4：软删除功能 ===")
    
    user = await User.create(name="赵六", email="zhaoliu@example.com")
    print(f"创建用户：{user.name}")
    
    # 软删除
    await user.delete()
    print(f"软删除用户，删除时间：{user.deleted_at}")
    
    # 验证普通查询找不到
    found = await User.find(user.id)
    print(f"普通查询结果：{found}")  # None
    
    # 包含已删除的查询
    found_with_deleted = await User.query().with_trashed().find(user.id)
    print(f"包含已删除查询：{found_with_deleted.name if found_with_deleted else None}")
    
    # 恢复用户
    if found_with_deleted:
        await found_with_deleted.restore()
        print(f"恢复用户：{found_with_deleted.name}")
    
    return user


async def demo_5_events():
    """演示5：事件系统"""
    print("\n=== 演示5：事件系统触发 ===")
    
    # 事件会在创建、更新时自动触发
    user = await User.create(name="孙七", email="sunqi@example.com")
    
    user.age = 35
    await user.save()
    
    return user


async def demo_6_relationships():
    """演示6：关系管理系统"""
    print("\n=== 演示6：关系管理系统 ===")
    
    # 创建用户
    user = await User.create(name="周八", email="zhouba@example.com")
    
    # 创建用户档案（一对一关系）
    profile = await Profile.create(
        user_id=user.id,
        bio="这是一个测试用户",
        avatar="avatar.jpg"
    )
    print(f"创建档案：{profile.bio}")
    
    # 通过关系创建文章（一对多关系）
    post1 = await user.posts.create(
        title="第一篇文章",
        content="这是第一篇文章的内容",
        published=True
    )
    print(f"通过关系创建文章：{post1.title}")
    
    post2 = await user.posts.create(
        title="第二篇文章", 
        content="这是第二篇文章的内容",
        published=False
    )
    print(f"通过关系创建文章：{post2.title}")
    
    # 加载关系数据
    user_posts = await user.posts.load()
    print(f"用户的文章数量：{len(user_posts)}")
    
    # 统计关系数据
    posts_count = await user.posts.count()
    print(f"文章总数：{posts_count}")
    
    return user, [post1, post2]


async def demo_7_many_to_many():
    """演示7：多对多关系（Laravel风格操作）"""
    print("\n=== 演示7：多对多关系操作 ===")
    
    # 创建用户和角色
    user = await User.create(name="吴九", email="wujiu@example.com")
    
    admin_role = await Role.create(name="admin", description="管理员")
    editor_role = await Role.create(name="editor", description="编辑")
    user_role = await Role.create(name="user", description="普通用户")
    
    print(f"创建用户：{user.name}")
    print(f"创建角色：{admin_role.name}, {editor_role.name}, {user_role.name}")
    
    # attach - 附加角色
    await user.roles.attach([admin_role.id, user_role.id])
    print("附加角色：admin, user")
    
    # 加载当前角色
    current_roles = await user.roles.load()
    role_names = [role.name for role in current_roles]
    print(f"当前角色：{role_names}")
    
    # sync - 同步角色（会替换现有角色）
    await user.roles.sync([editor_role.id, user_role.id])
    print("同步角色：editor, user")
    
    # 验证同步结果
    current_roles = await user.roles.load()
    role_names = [role.name for role in current_roles]
    print(f"同步后角色：{role_names}")
    
    # toggle - 切换角色
    result = await user.roles.toggle([admin_role.id, editor_role.id])
    print(f"切换结果 - 附加：{result['attached']}, 分离：{result['detached']}")
    
    # detach - 分离指定角色
    await user.roles.detach(user_role.id)
    print("分离user角色")
    
    # 最终角色状态
    final_roles = await user.roles.load()
    final_role_names = [role.name for role in final_roles]
    print(f"最终角色：{final_role_names}")
    
    return user


async def demo_8_query_relations():
    """演示8：关系查询和预加载"""
    print("\n=== 演示8：关系查询和预加载 ===")
    
    # 创建测试数据
    user1 = await User.create(name="测试用户1", email="test1@example.com")
    user2 = await User.create(name="测试用户2", email="test2@example.com")
    
    # 给用户1创建文章
    await user1.posts.create(title="已发布文章", content="内容", published=True)
    await user1.posts.create(title="草稿文章", content="内容", published=False)
    
    # 给用户2只创建档案
    await Profile.create(user_id=user2.id, bio="只有档案的用户")
    
    # 预加载查询 - 避免N+1问题
    print("预加载用户及其文章和档案...")
    users_with_relations = await User.query().with_(["posts", "profile"]).get()
    
    for user in users_with_relations:
        print(f"用户：{user.name}")
        # 这里不会触发额外的数据库查询
        user_posts = getattr(user, '_posts_loaded', [])
        user_profile = getattr(user, '_profile_loaded', None)
        print(f"  文章数量：{len(user_posts) if user_posts else 0}")
        print(f"  有档案：{'是' if user_profile else '否'}")
    
    # whereHas - 查询有特定关系的记录
    print("\n查询有已发布文章的用户...")
    users_with_published_posts = await User.query().where_has(
        'posts',
        lambda q: q.where('published', True)
    ).get()
    
    for user in users_with_published_posts:
        print(f"有已发布文章的用户：{user.name}")
    
    # whereDoesntHave - 查询没有特定关系的记录
    print("\n查询没有文章的用户...")
    users_without_posts = await User.query().where_doesnt_have('posts').get()
    
    for user in users_without_posts:
        print(f"没有文章的用户：{user.name}")
    
    return users_with_relations


async def demo_9_advanced_queries():
    """演示9：高级查询功能"""
    print("\n=== 演示9：高级查询功能 ===")
    
    # 复杂查询组合
    adult_active_users = await (User.query()
                               .where('age', '>=', 18)
                               .where('status', 'active')
                               .where_not_null('email')
                               .order_by('created_at', 'desc')
                               .limit(5)
                               .get())
    
    print(f"成年活跃用户数量：{len(adult_active_users)}")
    
    # 分页查询
    page_result = await User.query().paginate(page=1, per_page=3)
    print(f"分页结果：总数 {page_result['total']}, 当前页 {page_result['page']}")
    print(f"当前页用户：{[user.name for user in page_result['items']]}")
    
    # 统计查询
    total_users = await User.query().count()
    active_users_count = await User.query().where('status', 'active').count()
    
    print(f"用户总数：{total_users}")
    print(f"活跃用户数：{active_users_count}")
    
    # 存在性检查
    has_admin = await User.query().where('name', 'like', '%admin%').exists()
    print(f"是否有管理员用户：{has_admin}")
    
    return page_result


async def main():
    """主演示函数"""
    print("🚀 FastORM 增强功能演示")
    print("=" * 50)
    
    # 初始化数据库
    await fastorm.create_all()
    
    try:
        # 基础功能演示
        user1 = await demo_1_basic_crud()
        user2 = await demo_2_fillable_control()
        user3 = await demo_3_timestamps()
        user4 = await demo_4_soft_delete()
        user5 = await demo_5_events()
        
        # 关系功能演示
        user6, posts = await demo_6_relationships()
        user7 = await demo_7_many_to_many()
        users_with_relations = await demo_8_query_relations()
        page_result = await demo_9_advanced_queries()
        
        print("\n" + "=" * 50)
        print("✅ 所有演示完成！")
        print(f"📊 演示统计：")
        print(f"   - 创建用户数量：{await User.query().count()}")
        print(f"   - 创建文章数量：{await Post.query().count()}")
        print(f"   - 创建角色数量：{await Role.query().count()}")
        print(f"   - 创建档案数量：{await Profile.query().count()}")
        
        print(f"\n🎉 FastORM 已实现：")
        print(f"   ✅ ThinkORM级别的简洁API")
        print(f"   ✅ Eloquent级别的优雅特性")
        print(f"   ✅ FastAPI现代化集成")
        print(f"   ✅ 完整的关系管理系统")
        print(f"   ✅ Laravel风格的关系操作")
        print(f"   ✅ 强大的查询构建器")
        
    except Exception as e:
        print(f"❌ 演示过程中出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 