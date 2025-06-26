"""
性能监控器

全局性能监控，整合查询分析和N+1检测功能
"""

import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

from .profiler import QueryProfiler, ProfileSession, QueryInfo
from .detector import N1Detector, N1QueryAlert, QueryPattern

logger = logging.getLogger(__name__)


@dataclass
class PerformanceStats:
    """性能统计数据"""
    total_queries: int = 0
    slow_queries: int = 0
    failed_queries: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    n1_alerts: int = 0
    most_frequent_queries: List[QueryPattern] = field(default_factory=list)
    latest_alerts: List[N1QueryAlert] = field(default_factory=list)
    
    def update_from_profiler(self, profiler: QueryProfiler) -> None:
        """从性能分析器更新统计数据"""
        sessions = profiler.get_all_sessions()
        
        self.total_queries = sum(s.total_queries for s in sessions.values())
        self.slow_queries = sum(s.slow_queries for s in sessions.values())
        self.failed_queries = sum(s.failed_queries for s in sessions.values())
        self.total_execution_time = sum(s.total_time for s in sessions.values())
        
        if self.total_queries > 0:
            self.avg_execution_time = (
                self.total_execution_time / self.total_queries
            )
    
    def update_from_detector(self, detector: N1Detector) -> None:
        """从N+1检测器更新统计数据"""
        self.n1_alerts = len(detector.get_alerts())
        self.most_frequent_queries = detector.get_patterns(min_count=5)[:10]
        self.latest_alerts = detector.get_alerts()[:5]


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, 
                 enable_profiling: bool = True,
                 enable_n1_detection: bool = True,
                 slow_query_threshold: float = 1.0):
        """
        初始化性能监控器
        
        Args:
            enable_profiling: 启用查询性能分析
            enable_n1_detection: 启用N+1查询检测
            slow_query_threshold: 慢查询阈值（秒）
        """
        self.slow_query_threshold = slow_query_threshold
        self._lock = threading.Lock()
        self._enabled = True
        
        # 初始化组件
        self.profiler = QueryProfiler(enable_stack_trace=False)
        self.n1_detector = N1Detector(time_window=60, threshold=10)
        
        # 控制组件启用状态
        if not enable_profiling:
            self.profiler.disable()
        if not enable_n1_detection:
            self.n1_detector.disable()
        
        # 性能统计
        self.stats = PerformanceStats()
        self._last_stats_update = datetime.now()
    
    def start_monitoring(self) -> None:
        """开始监控"""
        with self._lock:
            self._enabled = True
            self.profiler.enable()
            self.n1_detector.enable()
        
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        with self._lock:
            self._enabled = False
            self.profiler.disable()
            self.n1_detector.disable()
        
        logger.info("Performance monitoring stopped")
    
    def analyze_query(self, sql: str, execution_time: float,
                     error: Optional[str] = None) -> None:
        """分析单个查询"""
        if not self._enabled:
            return
        
        # N+1检测
        self.n1_detector.analyze_query(sql)
        
        # 慢查询检测
        if execution_time > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected: {execution_time:.3f}s - {sql[:100]}..."
            )
    
    def get_current_stats(self) -> PerformanceStats:
        """获取当前性能统计"""
        with self._lock:
            # 定期更新统计数据（避免频繁计算）
            now = datetime.now()
            if (now - self._last_stats_update).seconds > 10:
                self.stats.update_from_profiler(self.profiler)
                self.stats.update_from_detector(self.n1_detector)
                self._last_stats_update = now
        
        return self.stats
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryInfo]:
        """获取慢查询列表"""
        all_queries = []
        
        # 收集所有会话的查询
        sessions = self.profiler.get_all_sessions()
        for session in sessions.values():
            all_queries.extend(session.queries)
        
        # 筛选慢查询并排序
        slow_queries = [
            q for q in all_queries 
            if q.is_slow and q.duration is not None
        ]
        slow_queries.sort(key=lambda x: x.duration or 0, reverse=True)
        
        return slow_queries[:limit]
    
    def get_failed_queries(self, limit: int = 10) -> List[QueryInfo]:
        """获取失败查询列表"""
        all_queries = []
        
        # 收集所有会话的查询
        sessions = self.profiler.get_all_sessions()
        for session in sessions.values():
            all_queries.extend(session.queries)
        
        # 筛选失败查询并排序
        failed_queries = [
            q for q in all_queries 
            if not q.is_success
        ]
        failed_queries.sort(key=lambda x: x.start_time, reverse=True)
        
        return failed_queries[:limit]
    
    def get_n1_alerts(self, severity: Optional[str] = None) -> List[N1QueryAlert]:
        """获取N+1查询警告"""
        return self.n1_detector.get_alerts(severity)
    
    def clear_data(self) -> None:
        """清空监控数据"""
        with self._lock:
            self.profiler.clear_sessions()
            self.n1_detector.clear_alerts()
            self.n1_detector.clear_patterns()
            self.stats = PerformanceStats()
        
        logger.info("Performance monitoring data cleared")
    
    def enable_profiling(self) -> None:
        """启用性能分析"""
        self.profiler.enable()
    
    def disable_profiling(self) -> None:
        """禁用性能分析"""
        self.profiler.disable()
    
    def enable_n1_detection(self) -> None:
        """启用N+1检测"""
        self.n1_detector.enable()
    
    def disable_n1_detection(self) -> None:
        """禁用N+1检测"""
        self.n1_detector.disable()
    
    @property
    def is_enabled(self) -> bool:
        """检查是否已启用"""
        return self._enabled
    
    @property
    def is_profiling_enabled(self) -> bool:
        """检查性能分析是否已启用"""
        return self.profiler.is_enabled
    
    @property
    def is_n1_detection_enabled(self) -> bool:
        """检查N+1检测是否已启用"""
        return self.n1_detector.is_enabled


# 全局性能监控器实例
GlobalMonitor = PerformanceMonitor()


def start_monitoring() -> None:
    """启动全局性能监控"""
    GlobalMonitor.start_monitoring()


def stop_monitoring() -> None:
    """停止全局性能监控"""
    GlobalMonitor.stop_monitoring()


def get_performance_stats() -> PerformanceStats:
    """获取性能统计"""
    return GlobalMonitor.get_current_stats()


def get_slow_queries(limit: int = 10) -> List[QueryInfo]:
    """获取慢查询"""
    return GlobalMonitor.get_slow_queries(limit)


def get_failed_queries(limit: int = 10) -> List[QueryInfo]:
    """获取失败查询"""
    return GlobalMonitor.get_failed_queries(limit)


def clear_monitoring_data() -> None:
    """清空监控数据"""
    GlobalMonitor.clear_data()


def analyze_query(sql: str, execution_time: float,
                 error: Optional[str] = None) -> None:
    """分析查询性能"""
    GlobalMonitor.analyze_query(sql, execution_time, error) 