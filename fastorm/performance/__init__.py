"""
FastORM Performance Monitoring Module

提供查询性能分析、N+1查询检测、慢查询监控等功能

核心组件：
- QueryProfiler: 查询性能分析器
- PerformanceMonitor: 全局性能监控器  
- N1Detector: N+1查询检测器
- PerformanceReporter: 性能报告生成器
"""

from .profiler import QueryProfiler, profile_query
from .monitor import (
    PerformanceMonitor, GlobalMonitor,
    start_monitoring, stop_monitoring, get_performance_stats,
    get_slow_queries, get_failed_queries, clear_monitoring_data,
    analyze_query
)
from .detector import (
    N1Detector, detect_n1_queries, 
    get_n1_alerts, get_query_patterns
)
from .reporter import (
    PerformanceReporter, generate_report,
    print_performance_summary, save_report
)

__all__ = [
    # 核心类
    'QueryProfiler',
    'PerformanceMonitor', 
    'N1Detector',
    'PerformanceReporter',
    
    # 便捷函数
    'profile_query',
    'detect_n1_queries', 
    'generate_report',
    'start_monitoring',
    'stop_monitoring',
    'get_performance_stats',
    'get_slow_queries',
    'get_failed_queries',
    'clear_monitoring_data',
    'analyze_query',
    'get_n1_alerts',
    'get_query_patterns',
    'print_performance_summary',
    'save_report',
    
    # 全局实例
    'GlobalMonitor',
]

# 版本信息
__version__ = '1.0.0' 