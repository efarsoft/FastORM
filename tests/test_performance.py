"""
FastORM 性能监控功能测试

测试性能监控系统的生产环境需求功能：
- 查询性能分析器
- 性能监控器
- N+1查询检测器
- 指标收集器
- 性能报告器
"""

import pytest
import time
from unittest.mock import Mock, patch
from sqlalchemy import Column, Integer, String
from datetime import datetime, timedelta

from fastorm.model.model import Model
from fastorm.performance import (
    QueryProfiler,
    PerformanceMonitor,
    N1Detector,
    PerformanceReporter,
    MetricsCollector,
    profile_query,
    start_monitoring,
    stop_monitoring,
    get_performance_stats,
    get_slow_queries,
    clear_monitoring_data,
    start_metrics_collection,
    stop_metrics_collection,
    get_current_metrics,
)


class TestQueryProfiler:
    """查询性能分析器测试类"""
    
    def test_query_profiler_creation(self):
        """测试查询性能分析器创建"""
        profiler = QueryProfiler()
        
        assert profiler.is_enabled is True
        assert profiler.enable_stack_trace is False
        assert len(profiler.sessions) == 0
    
    def test_query_profiler_with_stack_trace(self):
        """测试带堆栈跟踪的查询性能分析器"""
        profiler = QueryProfiler(enable_stack_trace=True)
        
        assert profiler.enable_stack_trace is True
        assert profiler.is_enabled is True
    
    def test_query_profiler_enable_disable(self):
        """测试启用/禁用性能分析"""
        profiler = QueryProfiler()
        
        assert profiler.is_enabled is True
        
        profiler.disable()
        assert profiler.is_enabled is False
        
        profiler.enable()
        assert profiler.is_enabled is True
    
    def test_query_profiler_clear_sessions(self):
        """测试清理会话"""
        profiler = QueryProfiler()
        
        with profiler.profile("test_session"):
            pass
        
        assert len(profiler.sessions) == 1
        
        profiler.clear_sessions()
        assert len(profiler.sessions) == 0


class TestPerformanceMonitor:
    """性能监控器测试类"""
    
    def test_performance_monitor_creation(self):
        """测试性能监控器创建"""
        monitor = PerformanceMonitor()
        
        assert monitor.is_enabled is True
        assert monitor.slow_query_threshold == 1.0
        assert monitor.profiler is not None
        assert monitor.n1_detector is not None
    
    def test_performance_monitor_start_stop(self):
        """测试启动/停止监控"""
        monitor = PerformanceMonitor()
        
        monitor.stop_monitoring()
        assert monitor.is_enabled is False
        
        monitor.start_monitoring()
        assert monitor.is_enabled is True
    
    def test_performance_monitor_analyze_query(self):
        """测试分析查询"""
        monitor = PerformanceMonitor()
        
        # 分析正常查询
        monitor.analyze_query("SELECT * FROM users", 0.1)
        
        # 分析慢查询
        with patch('fastorm.performance.monitor.logger') as mock_logger:
            monitor.analyze_query("SELECT * FROM posts", 2.0)
            mock_logger.warning.assert_called_once()
    
    def test_performance_monitor_get_current_stats(self):
        """测试获取当前统计"""
        monitor = PerformanceMonitor()
        
        stats = monitor.get_current_stats()
        
        assert hasattr(stats, 'total_queries')
        assert hasattr(stats, 'slow_queries')
        assert hasattr(stats, 'failed_queries')


class TestN1Detector:
    """N+1查询检测器测试类"""
    
    def test_n1_detector_creation(self):
        """测试N+1检测器创建"""
        detector = N1Detector()
        
        assert detector.is_enabled is True
        assert detector.time_window == 60
        assert detector.threshold == 10
        assert len(detector.patterns) == 0
        assert len(detector.alerts) == 0
    
    def test_n1_detector_normalize_sql(self):
        """测试SQL标准化"""
        detector = N1Detector()
        
        sql = "SELECT * FROM users WHERE id = 123"
        template, table = detector.normalize_sql(sql)
        
        assert "?" in template  # 参数被替换为占位符
        assert table == "users"
    
    def test_n1_detector_enable_disable(self):
        """测试启用/禁用检测"""
        detector = N1Detector()
        
        assert detector.is_enabled is True
        
        detector.disable()
        assert detector.is_enabled is False
        
        detector.enable()
        assert detector.is_enabled is True


class TestMetricsCollector:
    """指标收集器测试类"""
    
    def test_metrics_collector_creation(self):
        """测试指标收集器创建"""
        collector = MetricsCollector()
        
        assert collector.collection_interval == 60
        assert collector._collecting is False
        assert collector._collector_thread is None
    
    def test_metrics_collector_start_stop(self):
        """测试启动/停止收集"""
        collector = MetricsCollector()
        
        collector.start_collection()
        assert collector._collecting is True
        assert collector._collector_thread is not None
        
        collector.stop_collection()
        assert collector._collecting is False


class TestPerformanceReporter:
    """性能报告器测试类"""
    
    def test_performance_reporter_creation(self):
        """测试性能报告器创建"""
        monitor = PerformanceMonitor()
        reporter = PerformanceReporter(monitor)
        
        assert reporter.monitor is monitor
    
    def test_performance_reporter_generate_summary(self):
        """测试生成摘要报告"""
        monitor = PerformanceMonitor()
        reporter = PerformanceReporter(monitor)
        
        summary = reporter.generate_summary_report()
        
        assert isinstance(summary, dict)
        assert "timestamp" in summary
        assert "monitoring_status" in summary
        assert "query_statistics" in summary


class TestGlobalFunctions:
    """全局函数测试类"""
    
    def test_start_stop_monitoring(self):
        """测试全局监控启停"""
        start_monitoring()
        stop_monitoring()
    
    def test_get_performance_stats(self):
        """测试获取性能统计"""
        stats = get_performance_stats()
        assert hasattr(stats, 'total_queries')
    
    def test_get_slow_queries(self):
        """测试获取慢查询"""
        slow_queries = get_slow_queries(limit=5)
        assert isinstance(slow_queries, list)
    
    def test_clear_monitoring_data(self):
        """测试清理监控数据"""
        clear_monitoring_data()
    
    def test_start_stop_metrics_collection(self):
        """测试指标收集启停"""
        start_metrics_collection(interval=30)
        stop_metrics_collection()
    
    def test_get_current_metrics(self):
        """测试获取当前指标"""
        metrics = get_current_metrics()
        assert isinstance(metrics, dict)
    
    def test_profile_query_function(self):
        """测试查询分析函数"""
        with profile_query("test_session") as session:
            assert session.session_id == "test_session"


class TestPerformanceOptimization:
    """性能优化测试类"""
    
    def test_performance_overhead(self):
        """测试性能监控的开销"""
        monitor = PerformanceMonitor()
        
        # 测试禁用状态下的开销
        monitor.stop_monitoring()
        start_time = time.time()
        
        for i in range(100):
            monitor.analyze_query(f"SELECT {i}", 0.001)
        
        disabled_time = time.time() - start_time
        
        # 测试启用状态下的开销
        monitor.start_monitoring()
        start_time = time.time()
        
        for i in range(100):
            monitor.analyze_query(f"SELECT {i}", 0.001)
        
        enabled_time = time.time() - start_time
        
        # 开销应该是可接受的
        overhead_ratio = enabled_time / disabled_time if disabled_time > 0 else 1
        assert overhead_ratio < 10  # 开销不应该超过10倍 