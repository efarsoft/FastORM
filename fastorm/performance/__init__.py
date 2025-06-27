"""
FastORM Performance Monitoring Module

提供查询性能分析、N+1查询检测、慢查询监控等功能

核心组件：
- QueryProfiler: 查询性能分析器
- PerformanceMonitor: 全局性能监控器
- N1Detector: N+1查询检测器
- PerformanceReporter: 性能报告生成器
"""

from .dashboard import PerformanceDashboard
from .dashboard import start_interactive_dashboard
from .dashboard import start_realtime_dashboard
from .detector import N1Detector
from .detector import detect_n1_queries
from .detector import get_n1_alerts
from .detector import get_query_patterns
from .metrics import MetricsCollector
from .metrics import get_current_metrics
from .metrics import get_health_report
from .metrics import global_metrics_collector
from .metrics import record_cache_performance
from .metrics import record_connection_pool_metrics
from .metrics import start_metrics_collection
from .metrics import stop_metrics_collection
from .monitor import GlobalMonitor
from .monitor import PerformanceMonitor
from .monitor import analyze_query
from .monitor import clear_monitoring_data
from .monitor import get_failed_queries
from .monitor import get_performance_stats
from .monitor import get_slow_queries
from .monitor import start_monitoring
from .monitor import stop_monitoring
from .profiler import QueryProfiler
from .profiler import profile_query
from .reporter import PerformanceReporter
from .reporter import generate_report
from .reporter import print_performance_summary
from .reporter import save_report

__all__ = [
    # 核心类
    "QueryProfiler",
    "PerformanceMonitor",
    "N1Detector",
    "PerformanceReporter",
    "MetricsCollector",
    "PerformanceDashboard",
    # 便捷函数
    "profile_query",
    "detect_n1_queries",
    "generate_report",
    "start_monitoring",
    "stop_monitoring",
    "get_performance_stats",
    "get_slow_queries",
    "get_failed_queries",
    "clear_monitoring_data",
    "analyze_query",
    "get_n1_alerts",
    "get_query_patterns",
    "print_performance_summary",
    "save_report",
    # 指标收集功能
    "start_metrics_collection",
    "stop_metrics_collection",
    "get_current_metrics",
    "get_health_report",
    "record_connection_pool_metrics",
    "record_cache_performance",
    # 仪表板功能
    "start_interactive_dashboard",
    "start_realtime_dashboard",
    # 全局实例
    "GlobalMonitor",
    "global_metrics_collector",
]

# 版本信息
__version__ = "1.0.0"
