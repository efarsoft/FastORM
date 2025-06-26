"""
FastORM 第七阶段演示：分页与查询优化

演示新功能：
1. 查询作用域系统（@scope、@global_scope）
2. 增强的分页功能
3. 批量操作（chunk、batch、each）
4. 游标分页
"""

import asyncio
import datetime
from typing import List
from decimal import Decimal

from sqlalchemy import String, DateTime, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from fastorm.model.model import Model
from fastorm.mixins.scopes import scope, global_scope
from fastorm.core.session_manager import init_db


class User(Model):
    """用户模型 - 演示作用域系统"""
    
    __tablename__ = 'demo_users'
    
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default='active')
    role: Mapped[str] = mapped_column(String(20), default='user')
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # =================================================================
    # 查询作用域演示
    # =================================================================
    
    @scope
    def active(self, query):
        """活跃用户作用域"""
        return query.where('status', 'active')
    
    @scope
    def by_role(self, query, role: str):
        """按角色过滤作用域"""
        return query.where('role', role)
    
    @scope
    def adults(self, query):
        """成年用户作用域"""
        return query.where('age', '>=', 18)
    
    @scope
    def high_balance(self, query, min_balance: Decimal = Decimal('1000')):
        """高余额用户作用域"""
        return query.where('balance', '>=', min_balance)
    
    @scope
    def recent(self, query, days: int = 30):
        """最近注册用户作用域"""
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        return query.where('created_at', '>=', cutoff_date)
    
    @global_scope('soft_delete')
    def apply_soft_delete_filter(self, query):
        """全局软删除过滤器"""
        return query.where('is_deleted', False)
    
    def __repr__(self):
        return f"User(id={self.id}, name='{self.name}', role='{self.role}')"


class Post(Model):
    """文章模型 - 演示关系和批量操作"""
    
    __tablename__ = 'demo_posts'
    
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int] = mapped_column()
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    
    @scope
    def published(self, query):
        """已发布文章作用域"""
        return query.where('published', True)
    
    @scope
    def by_user(self, query, user_id: int):
        """按用户过滤作用域"""
        return query.where('user_id', user_id)
    
    def __repr__(self):
        return f"Post(id={self.id}, title='{self.title[:30]}...')"


async def demo_scope_system():
    """演示作用域系统"""
    print("\n🎯 === 查询作用域系统演示 ===")
    
    # 1. 基础作用域使用
    print("\n1. 基础作用域使用:")
    
    # 活跃用户
    active_users = await User.query().active().get()
    print(f"活跃用户数量: {len(active_users)}")
    
    # 链式作用域
    admin_adults = await User.query().active().by_role('admin').adults().get()
    print(f"活跃的成年管理员数量: {len(admin_adults)}")
    
    # 带参数的作用域
    vip_users = await User.query().active().high_balance(Decimal('5000')).get()
    print(f"高余额VIP用户数量: {len(vip_users)}")
    
    # 2. 全局作用域演示
    print("\n2. 全局作用域演示:")
    
    # 正常查询（自动应用软删除过滤）
    normal_users = await User.query().get()
    print(f"正常查询用户数量: {len(normal_users)}")
    
    # 移除全局作用域
    all_users = await User.query().without_global_scope('soft_delete').get()
    print(f"包含已删除的用户数量: {len(all_users)}")
    
    # 3. 作用域与传统查询结合
    print("\n3. 作用域与传统查询结合:")
    
    complex_query = await (User.query()
                          .active()
                          .adults()
                          .where('email', 'like', '%@gmail.com')
                          .order_by('created_at', 'desc')
                          .limit(5)
                          .get())
    print(f"复杂查询结果数量: {len(complex_query)}")


async def demo_enhanced_pagination():
    """演示增强的分页功能"""
    print("\n📄 === 增强分页功能演示 ===")
    
    # 1. 标准分页器
    print("\n1. 标准分页器:")
    
    paginator = await (User.query()
                      .active()
                      .order_by('created_at', 'desc')
                      .paginate(page=1, per_page=5))
    
    print(f"总记录数: {paginator.total}")
    print(f"当前页: {paginator.current_page}/{paginator.last_page}")
    print(f"本页记录数: {len(paginator.items)}")
    print(f"是否有下一页: {paginator.has_next_page}")
    print(f"是否有上一页: {paginator.has_previous_page}")
    
    print("\n当前页用户:")
    for user in paginator:  # 支持迭代
        print(f"  - {user.name} ({user.role})")
    
    # 2. 简单分页器（不计算总数）
    print("\n2. 简单分页器:")
    
    simple_paginator = await (User.query()
                             .active()
                             .simple_paginate(page=1, per_page=3))
    
    print(f"当前页: {simple_paginator.current_page}")
    print(f"本页记录数: {len(simple_paginator.items)}")
    print(f"是否有更多: {simple_paginator.has_more}")
    
    # 3. 分页器序列化
    print("\n3. 分页器数据:")
    
    page_data = paginator.to_simple_dict()
    print(f"序列化数据键: {list(page_data.keys())}")


async def demo_batch_operations():
    """演示批量操作"""
    print("\n⚡ === 批量操作演示 ===")
    
    # 1. 分块处理演示
    print("\n1. 分块处理:")
    
    async def process_user_chunk(users: List[User]):
        """处理用户块的示例函数"""
        print(f"  处理 {len(users)} 个用户的块")
        for user in users:
            # 模拟处理逻辑
            if user.balance < 100:
                print(f"    用户 {user.name} 余额不足")
    
    total_processed = await (User.query()
                           .active()
                           .chunk(3, process_user_chunk))
    print(f"分块处理完成，总共处理了 {total_processed} 个用户")
    
    # 2. 逐个处理演示
    print("\n2. 逐个处理:")
    
    async def process_single_user(user: User):
        """处理单个用户的示例函数"""
        if user.role == 'admin':
            print(f"  发送管理员通知给: {user.name}")
    
    admin_processed = await (User.query()
                           .by_role('admin')
                           .each(process_single_user, chunk_size=2))
    print(f"逐个处理完成，处理了 {admin_processed} 个管理员")
    
    # 3. 批量更新演示
    print("\n3. 批量更新:")
    
    # 批量更新低余额用户的状态
    updated_count = await (User.query()
                         .where('balance', '<', 100)
                         .batch()
                         .batch_update({'status': 'low_balance'}))
    print(f"批量更新了 {updated_count} 个低余额用户")
    
    # 4. 批量插入演示
    print("\n4. 批量插入:")
    
    new_posts_data = [
        {
            'title': f'批量文章 {i}',
            'content': f'这是第 {i} 篇批量创建的文章',
            'user_id': 1,
            'published': i % 2 == 0  # 偶数篇发布
        }
        for i in range(1, 6)
    ]
    
    new_posts = await Post.query().batch().batch_insert(new_posts_data)
    print(f"批量创建了 {len(new_posts)} 篇文章")


async def demo_cursor_pagination():
    """演示游标分页"""
    print("\n🔄 === 游标分页演示 ===")
    
    # 1. 首次查询
    print("\n1. 首次游标分页:")
    
    first_page = await (User.query()
                       .active()
                       .batch()
                       .cursor_paginate(
                           cursor_column='id',
                           limit=3
                       ))
    
    print(f"首页数据量: {len(first_page['data'])}")
    print(f"下一个游标: {first_page['next_cursor']}")
    print(f"是否有更多: {first_page['has_more']}")
    
    # 2. 获取下一页
    if first_page['has_more']:
        print("\n2. 获取下一页:")
        
        next_page = await (User.query()
                          .active()
                          .batch()
                          .cursor_paginate(
                              cursor_column='id',
                              cursor_value=first_page['next_cursor'],
                              limit=3
                          ))
        
        print(f"下一页数据量: {len(next_page['data'])}")
        print(f"下一个游标: {next_page['next_cursor']}")


async def create_sample_data():
    """创建示例数据"""
    print("📝 创建示例数据...")
    
    # 创建用户
    users_data = [
        {
            'name': 'Alice Admin',
            'email': 'alice@company.com',
            'age': 25,
            'role': 'admin',
            'balance': Decimal('5000.00'),
            'status': 'active'
        },
        {
            'name': 'Bob User',
            'email': 'bob@gmail.com',
            'age': 17,
            'role': 'user',
            'balance': Decimal('50.00'),
            'status': 'active'
        },
        {
            'name': 'Charlie Mod',
            'email': 'charlie@company.com',
            'age': 30,
            'role': 'moderator',
            'balance': Decimal('1500.00'),
            'status': 'active'
        },
        {
            'name': 'David User',
            'email': 'david@yahoo.com',
            'age': 22,
            'role': 'user',
            'balance': Decimal('200.00'),
            'status': 'inactive'
        },
        {
            'name': 'Eve Admin',
            'email': 'eve@company.com',
            'age': 28,
            'role': 'admin',
            'balance': Decimal('8000.00'),
            'status': 'active'
        },
        {
            'name': 'Frank User',
            'email': 'frank@gmail.com',
            'age': 35,
            'role': 'user',
            'balance': Decimal('80.00'),
            'status': 'active'
        },
        {
            'name': 'Grace Deleted',
            'email': 'grace@company.com',
            'age': 26,
            'role': 'user',
            'balance': Decimal('300.00'),
            'status': 'active',
            'is_deleted': True  # 软删除
        }
    ]
    
    for user_data in users_data:
        await User.create(**user_data)
    
    print(f"✅ 创建了 {len(users_data)} 个用户")


async def main():
    """主演示函数"""
    print("🚀 FastORM 第七阶段演示：分页与查询优化")
    print("=" * 60)
    
    # 初始化数据库
    await init_db("sqlite+aiosqlite:///stage_7_demo.db", echo=False)
    
    # 创建表
    from fastorm.core.session_manager import get_engine
    engine = get_engine()
    
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)
        await conn.run_sync(Model.metadata.create_all)
    
    try:
        # 创建示例数据
        await create_sample_data()
        
        # 演示各个功能
        await demo_scope_system()
        await demo_enhanced_pagination()
        await demo_batch_operations()
        await demo_cursor_pagination()
        
        print("\n🎉 第七阶段演示完成！")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 