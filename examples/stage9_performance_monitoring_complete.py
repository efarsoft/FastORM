#!/usr/bin/env python3
"""
FastORM第九阶段：性能监控系统完整演示

展示性能监控系统的所有核心功能：
1. 查询性能分析器 (QueryProfiler)
2. 性能监控器 (PerformanceMonitor)  
3. N+1查询检测器 (N1Detector)
4. 性能报告生成器 (PerformanceReporter)
"""

import asyncio
import time
from typing import List

# SQLAlchemy 2.0 imports
from sqlalchemy import String, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# FastORM imports
from fastorm import Model
from fastorm.performance import (
    QueryProfiler, PerformanceMonitor, N1Detector, PerformanceReporter,
    start_monitoring, stop_monitoring, get_performance_stats
)


# 测试模型
class User(Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100))
    
    # 关系定义
    posts: Mapped[List["Post"]] = relationship(back_populates="user")


class Post(Model):
    __tablename__ = 'posts'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    
    # 关系定义
    user: Mapped["User"] = relationship(back_populates="posts")


async def setup_test_database():
    """设置测试数据库和数据"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///performance_test.db", 
        echo=False
    )
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all)
        await conn.run_sync(User.metadata.create_all)
    
    # 创建会话工厂
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # 插入测试数据
    async with async_session() as session:
        # 创建用户
        users = [
            User(name=f"用户{i}", email=f"user{i}@example.com")
            for i in range(1, 11)
        ]
        session.add_all(users)
        await session.commit()
        
        # 为每个用户创建文章
        posts = []
        for user in users:
            for j in range(1, 6):  # 每个用户5篇文章
                post = Post(
                    title=f"用户{user.name}的文章{j}",
                    content=f"这是{user.name}写的第{j}篇文章的内容...",
                    user_id=user.id
                )
                posts.append(post)
        
        session.add_all(posts)
        await session.commit()
    
    return engine, async_session


async def demo_query_profiler():
    """演示查询性能分析器"""
    print("🔍 1. 查询性能分析器演示")
    print("-" * 50)
    
    engine, async_session = await setup_test_database()
    profiler = QueryProfiler(enable_stack_trace=True)
    
    # 使用性能分析器
    with profiler.profile("demo_session") as session_profile:
        async with async_session() as session:
            # 执行一些查询
            result = await session.execute(
                text("SELECT * FROM users WHERE id < 5")
            )
            users = result.fetchall()
            
            # 模拟一个慢查询
            await asyncio.sleep(0.1)
            result = await session.execute(
                text("SELECT COUNT(*) FROM posts")
            )
            count = result.scalar()
    
    # 分析结果
    print(f"✅ 会话ID: {session_profile.session_id}")
    print(f"📊 总查询数: {session_profile.total_queries}")
    print(f"🐌 慢查询数: {session_profile.slow_queries}")
    print(f"⏱️  总执行时间: {session_profile.total_time:.3f}s")
    print(f"⚡ 平均查询时间: {session_profile.avg_query_time:.3f}s")
    
    # 显示查询详情
    print("\n🔍 查询详情:")
    for i, query in enumerate(session_profile.queries, 1):
        status = "🐌 慢查询" if query.is_slow else "⚡ 正常"
        print(f"  {i}. {status} - {query.duration:.3f}s")
        print(f"     SQL: {query.sql[:60]}...")
    
    await engine.dispose()


async def demo_n1_detector():
    """演示N+1查询检测器"""
    print("\n🚨 2. N+1查询检测器演示")
    print("-" * 50)
    
    detector = N1Detector(time_window=30, threshold=5)
    
    # 模拟N+1查询模式
    print("🔄 模拟N+1查询模式...")
    
    # 主查询
    detector.analyze_query("SELECT * FROM users")
    
    # N+1查询模式 - 为每个用户查询文章
    for user_id in range(1, 8):
        detector.analyze_query(f"SELECT * FROM posts WHERE user_id = {user_id}")
    
    # 检查警告
    alerts = detector.get_alerts()
    print(f"🚨 生成警告数: {len(alerts)}")
    
    for alert in alerts:
        print(f"\n⚠️  {alert.severity}: {alert.description}")
        print(f"📊 查询次数: {alert.pattern.count}")
        print(f"🗂️  相关表: {alert.pattern.table_name}")
        print("💡 优化建议:")
        for suggestion in alert.suggestions:
            print(f"   - {suggestion}")
    
    # 显示查询模式统计
    patterns = detector.get_patterns(min_count=2)
    print(f"\n📈 检测到 {len(patterns)} 个查询模式:")
    for pattern in patterns:
        print(f"  🔄 表: {pattern.table_name} - 执行次数: {pattern.count}")


async def demo_performance_monitor():
    """演示性能监控器"""
    print("\n📊 3. 性能监控器演示")
    print("-" * 50)
    
    # 使用全局性能监控
    start_monitoring()
    
    engine, async_session = await setup_test_database()
    
    # 模拟各种查询操作
    async with async_session() as session:
        # 正常查询
        result = await session.execute(text("SELECT * FROM users LIMIT 5"))
        users = result.fetchall()
        
        # 模拟慢查询
        await asyncio.sleep(0.2)
        result = await session.execute(
            text("SELECT u.*, p.title FROM users u LEFT JOIN posts p ON u.id = p.user_id")
        )
        data = result.fetchall()
        
        # 模拟N+1查询
        for i in range(1, 6):
            result = await session.execute(
                text(f"SELECT * FROM posts WHERE user_id = {i}")
            )
            posts = result.fetchall()
    
    # 获取性能统计
    stats = get_performance_stats()
    
    print(f"📊 性能统计摘要:")
    print(f"   总查询数: {stats.total_queries}")
    print(f"   慢查询数: {stats.slow_queries}") 
    print(f"   平均执行时间: {stats.avg_execution_time:.3f}s")
    print(f"   N+1警告数: {stats.n1_alerts}")
    
    stop_monitoring()
    await engine.dispose()


async def demo_performance_reporter():
    """演示性能报告生成器"""
    print("\n📋 4. 性能报告生成器演示")
    print("-" * 50)
    
    # 创建监控器和报告器
    monitor = PerformanceMonitor()
    reporter = PerformanceReporter(monitor)
    
    monitor.start_monitoring()
    
    # 模拟一些查询活动
    engine, async_session = await setup_test_database()
    
    async with async_session() as session:
        # 执行多种类型的查询
        queries = [
            "SELECT * FROM users",
            "SELECT * FROM posts WHERE user_id = 1",
            "SELECT * FROM posts WHERE user_id = 2", 
            "SELECT * FROM posts WHERE user_id = 3",
            "SELECT COUNT(*) FROM users",
            "SELECT COUNT(*) FROM posts"
        ]
        
        for sql in queries:
            try:
                result = await session.execute(text(sql))
                data = result.fetchall()
                # 模拟查询时间
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"查询错误: {e}")
    
    # 生成报告
    print("📊 生成摘要报告:")
    summary_report = reporter.generate_summary_report()
    print(f"   监控状态: {'启用' if summary_report['monitoring_status']['enabled'] else '禁用'}")
    print(f"   总查询数: {summary_report['query_statistics']['total_queries']}")
    print(f"   N+1警告: {summary_report['n1_alerts']['total_alerts']}")
    
    # 生成文本报告
    print("\n📄 生成文本格式报告:")
    text_report = reporter.generate_text_report(detailed=False)
    print(text_report[:500] + "..." if len(text_report) > 500 else text_report)
    
    # 保存JSON报告
    try:
        reporter.save_report("performance_report.json", format="json", detailed=True)
        print("✅ 详细报告已保存到 performance_report.json")
    except Exception as e:
        print(f"⚠️  保存报告时出错: {e}")
    
    monitor.stop_monitoring()
    await engine.dispose()


async def demo_integration_scenario():
    """演示完整集成场景"""
    print("\n🎯 5. 完整集成场景演示")
    print("-" * 50)
    
    # 创建性能监控组件
    profiler = QueryProfiler()
    monitor = PerformanceMonitor()
    reporter = PerformanceReporter(monitor)
    
    print("🚀 启动性能监控...")
    monitor.start_monitoring()
    
    engine, async_session = await setup_test_database()
    
    # 使用性能分析器包装数据库操作
    with profiler.profile("integration_demo") as session_profile:
        async with async_session() as session:
            print("📈 执行模拟业务操作...")
            
            # 1. 用户列表查询
            result = await session.execute(text("SELECT * FROM users"))
            users = result.fetchall()
            
            # 2. 为每个用户查询文章 (故意制造N+1)
            for user_row in users[:5]:
                user_id = user_row[0]  # 假设第一列是ID
                result = await session.execute(
                    text(f"SELECT * FROM posts WHERE user_id = {user_id}")
                )
                posts = result.fetchall()
                
                # 模拟处理时间
                await asyncio.sleep(0.02)
            
            # 3. 模拟一个慢查询
            await asyncio.sleep(0.15)
            result = await session.execute(
                text("""
                SELECT u.name, COUNT(p.id) as post_count 
                FROM users u 
                LEFT JOIN posts p ON u.id = p.user_id 
                GROUP BY u.id, u.name
                """)
            )
            stats = result.fetchall()
    
    # 分析结果
    print("🔍 性能分析结果:")
    print(f"   会话查询数: {session_profile.total_queries}")
    print(f"   慢查询数: {session_profile.slow_queries}")
    print(f"   总执行时间: {session_profile.total_time:.3f}s")
    
    # 获取N+1警告
    n1_alerts = monitor.get_n1_alerts()
    if n1_alerts:
        print(f"🚨 检测到 {len(n1_alerts)} 个N+1查询警告")
        for alert in n1_alerts[:2]:  # 显示前2个
            print(f"   ⚠️  {alert.description}")
    
    # 生成最终报告
    print("\n📋 生成集成测试报告:")
    final_report = reporter.generate_text_report(detailed=True)
    
    # 显示报告摘要
    lines = final_report.split('\n')
    summary_lines = []
    in_summary = False
    for line in lines:
        if 'Query Statistics:' in line:
            in_summary = True
        if in_summary:
            summary_lines.append(line)
            if line.strip() == '':
                break
    
    print('\n'.join(summary_lines))
    
    monitor.stop_monitoring()
    await engine.dispose()
    print("✅ 性能监控系统集成测试完成")


async def main():
    """主演示函数"""
    print("🚀 FastORM 性能监控系统完整演示")
    print("=" * 60)
    
    try:
        await demo_query_profiler()
        await demo_n1_detector()
        await demo_performance_monitor()
        await demo_performance_reporter()
        await demo_integration_scenario()
        
        print("\n🎉 性能监控系统演示完成！")
        print("=" * 60)
        print("✅ 核心功能:")
        print("   1. 🔍 查询性能分析 - 详细的SQL执行统计")
        print("   2. 🚨 N+1查询检测 - 自动发现性能问题") 
        print("   3. 📊 实时性能监控 - 全局性能统计")
        print("   4. 📋 报告生成 - 多格式性能报告")
        print("   5. 🎯 完整集成 - 无缝集成到FastORM")
        
        print("\n🎯 使用建议:")
        print("   - 开发环境启用详细监控和N+1检测")
        print("   - 生产环境使用轻量级监控模式")
        print("   - 定期生成性能报告进行优化")
        print("   - 关注慢查询和N+1查询警告")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 