"""
FastORM Stage 9: 性能监控系统演示

展示查询性能分析、N+1查询检测、性能报告生成等功能
"""

import asyncio
import time
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_query_profiler():
    """演示查询性能分析器"""
    print("\n" + "="*60)
    print("🔍 查询性能分析器演示")
    print("="*60)
    
    from fastorm.performance import QueryProfiler, profile_query
    
    # 创建性能分析器
    profiler = QueryProfiler(enable_stack_trace=True)
    
    print("1. 基本性能分析")
    with profiler.profile("demo_session") as session:
        # 模拟一些查询
        print(f"   开始分析会话: {session.session_id}")
        
        # 模拟查询1
        profiler._current_session = session.session_id
        time.sleep(0.1)  # 模拟查询执行时间
        
        # 模拟查询2
        time.sleep(0.2)
        
        print(f"   会话时长: {session.duration:.3f}s")
        print(f"   查询总数: {session.total_queries}")
    
    print("\n2. 异步性能分析")
    async with profiler.async_profile("async_demo") as session:
        print(f"   异步会话: {session.session_id}")
        await asyncio.sleep(0.05)  # 模拟异步查询
        print(f"   异步查询完成")
    
    print("\n3. 便捷函数使用")
    with profile_query("convenience_demo") as session:
        print(f"   便捷函数会话: {session.session_id}")
        time.sleep(0.03)
    
    # 获取所有会话统计
    all_sessions = profiler.get_all_sessions()
    print(f"\n📊 分析结果:")
    print(f"   总会话数: {len(all_sessions)}")
    for sid, session in all_sessions.items():
        print(f"   会话 {sid}: {session.total_queries} 查询, "
              f"{session.total_time:.3f}s 总时间")
    
    return profiler


async def demo_n1_detector():
    """演示N+1查询检测器"""
    print("\n" + "="*60)
    print("🚨 N+1查询检测器演示")
    print("="*60)
    
    from fastorm.performance import N1Detector, detect_n1_queries
    
    # 创建N+1检测器
    detector = N1Detector(time_window=30, threshold=5)
    
    print("1. 模拟N+1查询模式")
    
    # 模拟正常查询
    detector.analyze_query(
        "SELECT * FROM users WHERE status = 'active' LIMIT 10"
    )
    
    # 模拟N+1查询 - 主查询
    detector.analyze_query(
        "SELECT id, name FROM posts WHERE user_id IN (1, 2, 3, 4, 5)"
    )
    
    # 模拟N+1查询 - 重复的相似查询
    user_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for user_id in user_ids:
        sql = f"SELECT * FROM user_profiles WHERE user_id = {user_id}"
        detector.analyze_query(sql)
        
        # 模拟另一种N+1模式
        sql2 = f"SELECT COUNT(*) FROM posts WHERE author_id = {user_id}"
        detector.analyze_query(sql2)
    
    print("2. 分析检测结果")
    
    # 获取查询模式
    patterns = detector.get_patterns(min_count=3)
    print(f"\n📈 查询模式统计:")
    for i, pattern in enumerate(patterns[:5], 1):
        print(f"   {i}. 表: {pattern.table_name}")
        print(f"      查询次数: {pattern.count}")
        print(f"      SQL模板: {pattern.sql_template[:80]}...")
    
    # 获取N+1警告
    alerts = detector.get_alerts()
    print(f"\n⚠️ N+1查询警告 ({len(alerts)} 个):")
    for i, alert in enumerate(alerts[:3], 1):
        print(f"   {i}. {alert.description}")
        print(f"      严重程度: {alert.severity}")
        print(f"      是否严重: {'是' if alert.is_critical else '否'}")
        if alert.suggestions:
            print(f"      建议: {alert.suggestions[0]}")
    
    print("\n3. 便捷函数使用")
    from fastorm.performance import (
        get_n1_alerts, get_query_patterns
    )
    
    critical_alerts = get_n1_alerts("CRITICAL")
    print(f"   严重警告数量: {len(critical_alerts)}")
    
    frequent_patterns = get_query_patterns(min_count=5)
    print(f"   高频查询模式: {len(frequent_patterns)}")
    
    return detector


async def demo_performance_monitor():
    """演示全局性能监控器"""
    print("\n" + "="*60)
    print("📊 全局性能监控器演示")
    print("="*60)
    
    from fastorm.performance import (
        PerformanceMonitor, start_monitoring, stop_monitoring,
        get_performance_stats, get_slow_queries
    )
    
    # 创建性能监控器
    monitor = PerformanceMonitor(
        enable_profiling=True,
        enable_n1_detection=True,
        slow_query_threshold=0.1
    )
    
    print("1. 启动性能监控")
    monitor.start_monitoring()
    print(f"   监控状态: {'启用' if monitor.is_enabled else '禁用'}")
    print(f"   性能分析: {'启用' if monitor.is_profiling_enabled else '禁用'}")
    print(f"   N+1检测: {'启用' if monitor.is_n1_detection_enabled else '禁用'}")
    
    print("\n2. 模拟数据库操作")
    
    # 模拟一些查询操作
    queries = [
        ("SELECT * FROM users", 0.05),
        ("SELECT * FROM posts WHERE user_id = 1", 0.15),  # 慢查询
        ("UPDATE users SET login_count = login_count + 1", 0.08),
        ("SELECT COUNT(*) FROM comments", 0.02),
        ("SELECT * FROM user_profiles WHERE user_id = 2", 0.12),  # 慢查询
    ]
    
    for sql, duration in queries:
        monitor.analyze_query(sql, duration)
        await asyncio.sleep(0.01)  # 模拟间隔
    
    # 模拟一些失败查询
    monitor.analyze_query(
        "SELECT * FROM non_existent_table", 
        0.05, 
        error="Table 'non_existent_table' doesn't exist"
    )
    
    print("   模拟查询执行完成")
    
    print("\n3. 获取性能统计")
    stats = monitor.get_current_stats()
    print(f"   总查询数: {stats.total_queries}")
    print(f"   慢查询数: {stats.slow_queries}")
    print(f"   失败查询数: {stats.failed_queries}")
    print(f"   平均执行时间: {stats.avg_execution_time:.4f}s")
    print(f"   总执行时间: {stats.total_execution_time:.3f}s")
    print(f"   N+1警告数: {stats.n1_alerts}")
    
    print("\n4. 查询详情分析")
    
    # 获取慢查询
    slow_queries = monitor.get_slow_queries(3)
    print(f"   慢查询 ({len(slow_queries)} 个):")
    for i, query in enumerate(slow_queries, 1):
        print(f"     {i}. {query.sql[:50]}... ({query.duration:.3f}s)")
    
    # 获取失败查询
    failed_queries = monitor.get_failed_queries(3)
    print(f"   失败查询 ({len(failed_queries)} 个):")
    for i, query in enumerate(failed_queries, 1):
        print(f"     {i}. {query.sql[:50]}...")
        print(f"        错误: {query.error}")
    
    print("\n5. 便捷函数测试")
    start_monitoring()  # 全局监控
    print("   全局监控已启动")
    
    global_stats = get_performance_stats()
    print(f"   全局统计 - 总查询: {global_stats.total_queries}")
    
    stop_monitoring()
    print("   全局监控已停止")
    
    return monitor


async def demo_performance_reporter():
    """演示性能报告生成器"""
    print("\n" + "="*60)
    print("📋 性能报告生成器演示")
    print("="*60)
    
    from fastorm.performance import (
        PerformanceReporter, generate_report, 
        print_performance_summary, save_report
    )
    from fastorm.performance.monitor import GlobalMonitor
    
    # 使用全局监控器的数据
    reporter = PerformanceReporter(GlobalMonitor)
    
    print("1. 生成摘要报告")
    summary_json = reporter.generate_json_report(detailed=False)
    print("   JSON摘要报告已生成")
    print(f"   报告长度: {len(summary_json)} 字符")
    
    print("\n2. 生成详细报告")
    detailed_text = reporter.generate_text_report(detailed=True)
    print("   文本详细报告已生成")
    print(f"   报告行数: {len(detailed_text.split('\n'))} 行")
    
    print("\n3. 控制台输出演示")
    print("   --- 性能摘要报告 ---")
    reporter.print_summary()
    
    print("\n4. 便捷函数使用")
    
    # 生成JSON报告
    json_report = generate_report(detailed=False, format="json")
    print(f"   便捷JSON报告: {len(json_report)} 字符")
    
    # 生成文本报告
    text_report = generate_report(detailed=True, format="txt")
    print(f"   便捷文本报告: {len(text_report.split('\n'))} 行")
    
    print("\n5. 保存报告到文件")
    try:
        # 保存JSON报告
        save_report("performance_summary.json", format="json", detailed=False)
        print("   ✅ JSON摘要报告已保存")
        
        # 保存详细文本报告
        save_report("performance_detailed.txt", format="txt", detailed=True)
        print("   ✅ 详细文本报告已保存")
        
    except Exception as e:
        print(f"   ❌ 保存报告失败: {e}")
    
    return reporter


async def demo_integration_example():
    """演示集成使用示例"""
    print("\n" + "="*60)
    print("🚀 集成使用示例")
    print("="*60)
    
    from fastorm.performance import (
        start_monitoring, profile_query, 
        get_performance_stats, print_performance_summary
    )
    
    print("1. 启动全局监控")
    start_monitoring()
    
    print("\n2. 业务代码中的性能分析")
    
    # 模拟用户查询功能
    async def get_user_with_posts(user_id: int):
        """模拟获取用户及其文章的功能"""
        with profile_query(f"user_posts_{user_id}") as session:
            print(f"   查询用户 {user_id} 的基本信息...")
            await asyncio.sleep(0.05)  # 模拟查询用户
            
            print(f"   查询用户 {user_id} 的文章列表...")
            await asyncio.sleep(0.08)  # 模拟查询文章
            
            print(f"   查询用户 {user_id} 的评论统计...")
            await asyncio.sleep(0.03)  # 模拟查询评论
            
            return {
                "user_id": user_id,
                "query_count": session.total_queries,
                "total_time": session.total_time
            }
    
    # 模拟批量用户查询（可能触发N+1）
    print("   执行批量用户查询...")
    results = []
    for user_id in range(1, 6):
        result = await get_user_with_posts(user_id)
        results.append(result)
        print(f"     用户 {user_id}: {result['total_time']:.3f}s")
    
    print("\n3. 性能分析结果")
    stats = get_performance_stats()
    print(f"   总查询数: {stats.total_queries}")
    print(f"   平均查询时间: {stats.avg_execution_time:.4f}s")
    print(f"   检测到的N+1问题: {stats.n1_alerts} 个")
    
    print("\n4. 生成性能报告")
    print_performance_summary()
    
    print("\n✅ 集成演示完成!")
    
    return results


async def main():
    """主演示函数"""
    print("🚀 FastORM Stage 9: 性能监控系统全面演示")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 演示各个组件
        profiler = await demo_query_profiler()
        detector = await demo_n1_detector()
        monitor = await demo_performance_monitor()
        reporter = await demo_performance_reporter()
        
        # 集成演示
        results = await demo_integration_example()
        
        print("\n" + "="*80)
        print("🎉 第九阶段演示完成!")
        print("="*80)
        print("\n📋 演示总结:")
        print("✅ 查询性能分析器 - 实时查询时间统计")
        print("✅ N+1查询检测器 - 自动发现性能问题")
        print("✅ 全局性能监控器 - 综合性能管理")
        print("✅ 性能报告生成器 - 详细报告输出")
        print("✅ 集成使用示例 - 实际业务场景")
        
        print(f"\n完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "profiler": profiler,
            "detector": detector,
            "monitor": monitor,
            "reporter": reporter,
            "integration_results": results
        }
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 运行演示
    demo_results = asyncio.run(main())
    
    if demo_results:
        print("\n🎯 演示成功完成！")
        print("性能监控系统已经可以投入使用。")
    else:
        print("\n❌ 演示过程中遇到问题，请检查错误信息。") 