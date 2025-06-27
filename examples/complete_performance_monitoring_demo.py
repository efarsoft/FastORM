#!/usr/bin/env python3
"""
FastORM 完整性能监控系统演示

展示增强后的性能监控系统的所有功能：
1. 基础性能监控 (QueryProfiler, PerformanceMonitor, N1Detector)
2. 高级指标收集 (MetricsCollector, 系统资源监控)
3. 实时监控仪表板 (PerformanceDashboard)
4. 健康状况检查和报告生成
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
    # 核心监控组件
    QueryProfiler, PerformanceMonitor, N1Detector, PerformanceReporter,
    # 高级指标收集
    MetricsCollector, start_metrics_collection, stop_metrics_collection,
    get_current_metrics, get_health_report,
    record_connection_pool_metrics, record_cache_performance,
    # 仪表板功能
    PerformanceDashboard, start_interactive_dashboard, start_realtime_dashboard,
    # 便捷函数
    start_monitoring, stop_monitoring, get_performance_stats
)


# 测试模型
class User(Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100))
    
    posts: Mapped[List["Post"]] = relationship(back_populates="user")


class Post(Model):
    __tablename__ = 'posts'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    
    user: Mapped["User"] = relationship(back_populates="posts")


async def setup_database():
    """设置测试数据库"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///complete_performance_test.db", 
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all)
        await conn.run_sync(User.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # 插入测试数据
    async with async_session() as session:
        users = [User(name=f"用户{i}", email=f"user{i}@test.com") for i in range(1, 21)]
        session.add_all(users)
        await session.commit()
        
        posts = []
        for user in users:
            for j in range(1, 6):
                post = Post(
                    title=f"{user.name}的文章{j}",
                    content=f"文章内容{j}...",
                    user_id=user.id
                )
                posts.append(post)
        
        session.add_all(posts)
        await session.commit()
    
    return engine, async_session


async def demo_basic_monitoring():
    """演示基础监控功能"""
    print("🔍 1. 基础性能监控演示")
    print("=" * 60)
    
    engine, async_session = await setup_database()
    
    # 创建性能分析器
    profiler = QueryProfiler(enable_stack_trace=True)
    
    # 使用性能分析器
    with profiler.profile("basic_demo") as session_profile:
        async with async_session() as session:
            # 执行各种查询
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            result = await session.execute(text("SELECT * FROM users LIMIT 10"))
            users = result.fetchall()
            
            # 模拟慢查询
            await asyncio.sleep(0.15)
            result = await session.execute(
                text("SELECT u.*, COUNT(p.id) FROM users u LEFT JOIN posts p ON u.id = p.user_id GROUP BY u.id")
            )
            user_posts = result.fetchall()
    
    print(f"✅ 基础监控结果:")
    print(f"   会话ID: {session_profile.session_id}")
    print(f"   总查询数: {session_profile.total_queries}")
    print(f"   慢查询数: {session_profile.slow_queries}")
    print(f"   总执行时间: {session_profile.total_time:.3f}s")
    
    await engine.dispose()


async def demo_advanced_metrics():
    """演示高级指标收集"""
    print("\n📊 2. 高级指标收集演示")
    print("=" * 60)
    
    # 启动指标收集（短间隔用于演示）
    start_metrics_collection(interval=2)
    
    print("🚀 启动指标收集器...")
    time.sleep(3)  # 等待收集一些数据
    
    # 模拟连接池数据
    record_connection_pool_metrics(
        pool_size=20,
        checked_out=5,
        checked_in=15,
        overflow=0,
        invalid=0
    )
    
    # 模拟缓存性能数据
    record_cache_performance(
        total_requests=1000,
        cache_hits=850,
        cache_size=500,
        memory_usage=128.5
    )
    
    # 获取当前指标
    metrics = get_current_metrics()
    
    print("📈 当前系统指标:")
    if metrics.get('memory'):
        memory = metrics['memory']
        print(f"   🧠 内存使用: {memory['usage_percent']:.1f}% ({memory['used_mb']:.0f}MB)")
    
    if metrics.get('system'):
        system = metrics['system']
        print(f"   ⚡ CPU使用: {system['cpu_percent']:.1f}%")
    
    if metrics.get('cache'):
        cache = metrics['cache']
        print(f"   🗄️  缓存命中率: {cache['hit_ratio']:.2%}")
    
    if metrics.get('connection_pool'):
        pool = metrics['connection_pool']
        print(f"   🔗 连接池: {pool['checked_out']}/{pool['pool_size']}")
    
    # 生成健康报告
    health_report = get_health_report()
    print(f"\n🏥 系统健康状态: {health_report['health_status']}")
    if health_report.get('warnings'):
        print("⚠️  警告:")
        for warning in health_report['warnings']:
            print(f"     - {warning}")
    
    stop_metrics_collection()


async def demo_n1_detection():
    """演示N+1查询检测"""
    print("\n🚨 3. N+1查询检测演示")
    print("=" * 60)
    
    detector = N1Detector(time_window=30, threshold=3)
    
    print("🔄 模拟N+1查询模式...")
    
    # 模拟主查询
    detector.analyze_query("SELECT id, name FROM users LIMIT 10")
    
    # 模拟N+1查询 - 为每个用户查询其文章
    for user_id in range(1, 8):
        detector.analyze_query(f"SELECT * FROM posts WHERE user_id = {user_id}")
    
    # 获取警告
    alerts = detector.get_alerts()
    
    print(f"🚨 检测结果:")
    print(f"   警告数量: {len(alerts)}")
    
    for alert in alerts:
        print(f"   ⚠️  {alert.severity}: {alert.description}")
        print(f"       表: {alert.pattern.table_name}")
        print(f"       查询次数: {alert.pattern.count}")
        if alert.suggestions:
            print("       优化建议:")
            for suggestion in alert.suggestions[:2]:
                print(f"         - {suggestion}")


async def demo_integrated_monitoring():
    """演示完整集成监控"""
    print("\n🎯 4. 完整集成监控演示")
    print("=" * 60)
    
    engine, async_session = await setup_database()
    
    # 启动所有监控组件
    print("🚀 启动完整监控系统...")
    start_monitoring()
    start_metrics_collection(interval=2)
    
    # 创建性能监控器和报告器
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    reporter = PerformanceReporter(monitor)
    
    # 执行一系列操作以生成监控数据
    async with async_session() as session:
        print("📈 执行模拟业务操作...")
        
        # 1. 用户查询
        result = await session.execute(text("SELECT * FROM users"))
        users = result.fetchall()
        
        # 2. N+1查询模式（故意）
        for user_row in users[:8]:
            user_id = user_row[0]
            result = await session.execute(text(f"SELECT * FROM posts WHERE user_id = {user_id}"))
            posts = result.fetchall()
            await asyncio.sleep(0.01)  # 模拟处理时间
        
        # 3. 复杂查询
        await asyncio.sleep(0.1)  # 模拟慢查询
        result = await session.execute(
            text("""
            SELECT u.name, u.email, COUNT(p.id) as post_count,
                   AVG(LENGTH(p.content)) as avg_content_length
            FROM users u 
            LEFT JOIN posts p ON u.id = p.user_id 
            GROUP BY u.id, u.name, u.email
            ORDER BY post_count DESC
            """)
        )
        analytics = result.fetchall()
        
        # 4. 更多查询操作
        result = await session.execute(text("SELECT COUNT(*) FROM posts"))
        total_posts = result.scalar()
        
        result = await session.execute(text("SELECT title FROM posts ORDER BY id DESC LIMIT 5"))
        recent_posts = result.fetchall()
    
    # 等待一下让指标收集器收集数据
    time.sleep(3)
    
    # 获取综合统计
    stats = get_performance_stats()
    metrics = get_current_metrics()
    health = get_health_report()
    
    print("📊 集成监控结果摘要:")
    print(f"   总查询数: {stats.total_queries}")
    print(f"   慢查询数: {stats.slow_queries}")
    print(f"   N+1警告数: {stats.n1_alerts}")
    print(f"   平均执行时间: {stats.avg_execution_time:.3f}s")
    print(f"   系统健康状态: {health['health_status']}")
    
    # 生成详细报告
    detailed_report = reporter.generate_text_report(detailed=True)
    print(f"\n📋 详细报告预览:")
    report_lines = detailed_report.split('\n')
    for line in report_lines[:15]:  # 显示前15行
        print(f"   {line}")
    print("   ...")
    
    # 清理
    stop_monitoring()
    stop_metrics_collection()
    await engine.dispose()


def demo_dashboard_preview():
    """演示仪表板功能预览"""
    print("\n🖥️  5. 性能仪表板功能预览")
    print("=" * 60)
    
    # 创建仪表板实例
    dashboard = PerformanceDashboard()
    
    # 生成实时报告数据
    live_report = dashboard.generate_live_report()
    
    print("📊 仪表板数据预览:")
    print(f"   生成时间: {live_report['timestamp']}")
    print(f"   查询统计:")
    query_stats = live_report['query_statistics']
    print(f"     - 总查询数: {query_stats['total_queries']}")
    print(f"     - 慢查询数: {query_stats['slow_queries']}")
    print(f"     - 平均时间: {query_stats['avg_execution_time']:.3f}s")
    
    print(f"   系统状态: {live_report['health_status']}")
    print(f"   N+1警告数: {live_report['n1_alerts_count']}")
    
    # 导出仪表板数据
    export_filename = "dashboard_demo_export.json"
    dashboard.export_dashboard_data(export_filename)
    print(f"   ✅ 数据已导出到: {export_filename}")
    
    print("\n💡 仪表板功能说明:")
    print("   - 实时监控界面: start_realtime_dashboard()")
    print("   - 交互式控制台: start_interactive_dashboard()")
    print("   - 自定义刷新间隔和监控组件")
    print("   - 支持导出监控数据和生成报告")


async def main():
    """主演示函数"""
    print("🚀 FastORM 完整性能监控系统演示")
    print("=" * 80)
    print("展示增强后的性能监控系统的所有功能")
    print("=" * 80)
    
    try:
        await demo_basic_monitoring()
        await demo_advanced_metrics()
        await demo_n1_detection()
        await demo_integrated_monitoring()
        demo_dashboard_preview()
        
        print("\n🎉 完整性能监控系统演示完成！")
        print("=" * 80)
        print("✅ 新增功能亮点:")
        print("   1. 🧠 系统资源监控 - CPU、内存、磁盘、网络")
        print("   2. 🔗 连接池监控 - 连接状态和性能指标") 
        print("   3. 🗄️  缓存性能监控 - 命中率和内存使用")
        print("   4. 🏥 健康状况检查 - 自动警告和建议")
        print("   5. 🖥️  实时监控仪表板 - 可视化界面")
        print("   6. 📋 增强报告功能 - 多格式导出")
        
        print("\n🎯 使用建议:")
        print("   - 生产环境使用轻量级监控模式")
        print("   - 开发环境启用完整监控和仪表板")
        print("   - 定期检查健康报告和N+1警告")
        print("   - 使用仪表板进行实时性能调优")
        
        print("\n🚀 快速开始:")
        print("   # 启动基础监控")
        print("   from fastorm.performance import start_monitoring")
        print("   start_monitoring()")
        print()
        print("   # 启动完整监控+仪表板")
        print("   from fastorm.performance import start_interactive_dashboard")
        print("   start_interactive_dashboard()")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 