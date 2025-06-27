"""
性能指标收集器

收集系统级性能指标，包括：
- 内存使用情况
- 连接池状态
- 缓存命中率
- 系统资源使用
"""

import gc
import threading
import time
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryMetrics:
    """内存使用指标"""
    used_memory: float  # MB
    available_memory: float  # MB
    memory_percent: float
    swap_used: float  # MB
    swap_percent: float
    gc_collections: Dict[int, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConnectionPoolMetrics:
    """连接池指标"""
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int
    pool_recreated: int = 0
    pool_errors: int = 0
    avg_connection_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CacheMetrics:
    """缓存性能指标"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    max_cache_size: int = 0
    evictions: int = 0
    memory_usage: float = 0.0  # MB
    avg_response_time: float = 0.0  # ms
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def hit_ratio(self) -> float:
        """缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests


@dataclass
class SystemMetrics:
    """系统资源指标"""
    cpu_percent: float
    cpu_count: int
    load_average: Optional[List[float]]  # 1, 5, 15分钟平均负载
    disk_usage: Dict[str, float]  # 磁盘使用率
    network_io: Dict[str, int]  # 网络IO
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self, collection_interval: int = 60):
        """
        初始化指标收集器
        
        Args:
            collection_interval: 收集间隔（秒）
        """
        self.collection_interval = collection_interval
        self._memory_metrics: List[MemoryMetrics] = []
        self._connection_metrics: List[ConnectionPoolMetrics] = []
        self._cache_metrics: List[CacheMetrics] = []
        self._system_metrics: List[SystemMetrics] = []
        self._collecting = False
        self._collector_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 限制历史数据量（保留最近24小时）
        self._max_history = 24 * 3600 // collection_interval
    
    def start_collection(self) -> None:
        """开始收集指标"""
        if self._collecting:
            return
        
        self._collecting = True
        self._collector_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self._collector_thread.start()
        logger.info("性能指标收集已启动")
    
    def stop_collection(self) -> None:
        """停止收集指标"""
        if not self._collecting:
            return
        
        self._collecting = False
        if self._collector_thread:
            self._collector_thread.join(timeout=5)
        logger.info("性能指标收集已停止")
    
    def _collection_loop(self) -> None:
        """指标收集循环"""
        while self._collecting:
            try:
                self._collect_all_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"指标收集错误: {e}")
    
    def _collect_all_metrics(self) -> None:
        """收集所有指标"""
        with self._lock:
            # 收集内存指标
            try:
                memory_metrics = self._collect_memory_metrics()
                self._memory_metrics.append(memory_metrics)
                if len(self._memory_metrics) > self._max_history:
                    self._memory_metrics.pop(0)
            except Exception as e:
                logger.error(f"内存指标收集错误: {e}")
            
            # 收集系统指标
            try:
                system_metrics = self._collect_system_metrics()
                self._system_metrics.append(system_metrics)
                if len(self._system_metrics) > self._max_history:
                    self._system_metrics.pop(0)
            except Exception as e:
                logger.error(f"系统指标收集错误: {e}")
    
    def _collect_memory_metrics(self) -> MemoryMetrics:
        """收集内存指标"""
        # 系统内存
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # GC统计
        gc_stats = {}
        for i in range(3):
            gc_stats[i] = gc.get_count()[i]
        
        return MemoryMetrics(
            used_memory=memory.used / (1024 * 1024),  # 转换为MB
            available_memory=memory.available / (1024 * 1024),
            memory_percent=memory.percent,
            swap_used=swap.used / (1024 * 1024),
            swap_percent=swap.percent,
            gc_collections=gc_stats
        )
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 负载平均值（Unix系统）
        load_avg = None
        try:
            load_avg = list(psutil.getloadavg())
        except AttributeError:
            # Windows系统不支持
            pass
        
        # 磁盘使用率
        disk_usage = {}
        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.device] = usage.percent
                except PermissionError:
                    continue
        except Exception as e:
            logger.warning(f"磁盘使用率收集失败: {e}")
        
        # 网络IO
        network_io = {}
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                network_io = {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
        except Exception as e:
            logger.warning(f"网络IO收集失败: {e}")
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            load_average=load_avg,
            disk_usage=disk_usage,
            network_io=network_io
        )
    
    def record_connection_metrics(self, pool_metrics: ConnectionPoolMetrics) -> None:
        """记录连接池指标"""
        with self._lock:
            self._connection_metrics.append(pool_metrics)
            if len(self._connection_metrics) > self._max_history:
                self._connection_metrics.pop(0)
    
    def record_cache_metrics(self, cache_metrics: CacheMetrics) -> None:
        """记录缓存指标"""
        with self._lock:
            self._cache_metrics.append(cache_metrics)
            if len(self._cache_metrics) > self._max_history:
                self._cache_metrics.pop(0)
    
    def get_memory_metrics(self, last_minutes: int = 60) -> List[MemoryMetrics]:
        """获取内存指标"""
        cutoff = datetime.now() - timedelta(minutes=last_minutes)
        with self._lock:
            return [
                m for m in self._memory_metrics 
                if m.timestamp > cutoff
            ]
    
    def get_system_metrics(self, last_minutes: int = 60) -> List[SystemMetrics]:
        """获取系统指标"""
        cutoff = datetime.now() - timedelta(minutes=last_minutes)
        with self._lock:
            return [
                m for m in self._system_metrics 
                if m.timestamp > cutoff
            ]
    
    def get_connection_metrics(self, last_minutes: int = 60) -> List[ConnectionPoolMetrics]:
        """获取连接池指标"""
        cutoff = datetime.now() - timedelta(minutes=last_minutes)
        with self._lock:
            return [
                m for m in self._connection_metrics 
                if m.timestamp > cutoff
            ]
    
    def get_cache_metrics(self, last_minutes: int = 60) -> List[CacheMetrics]:
        """获取缓存指标"""
        cutoff = datetime.now() - timedelta(minutes=last_minutes)
        with self._lock:
            return [
                m for m in self._cache_metrics 
                if m.timestamp > cutoff
            ]
    
    def get_current_metrics_summary(self) -> Dict[str, Any]:
        """获取当前指标摘要"""
        with self._lock:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'memory': None,
                'system': None,
                'connection_pool': None,
                'cache': None
            }
            
            # 最新内存指标
            if self._memory_metrics:
                latest_memory = self._memory_metrics[-1]
                summary['memory'] = {
                    'used_mb': round(latest_memory.used_memory, 2),
                    'available_mb': round(latest_memory.available_memory, 2),
                    'usage_percent': latest_memory.memory_percent,
                    'swap_usage_percent': latest_memory.swap_percent,
                    'gc_collections': latest_memory.gc_collections
                }
            
            # 最新系统指标
            if self._system_metrics:
                latest_system = self._system_metrics[-1]
                summary['system'] = {
                    'cpu_percent': latest_system.cpu_percent,
                    'cpu_count': latest_system.cpu_count,
                    'load_average': latest_system.load_average,
                    'disk_usage': latest_system.disk_usage,
                    'network_io': latest_system.network_io
                }
            
            # 最新连接池指标
            if self._connection_metrics:
                latest_conn = self._connection_metrics[-1]
                summary['connection_pool'] = {
                    'pool_size': latest_conn.pool_size,
                    'checked_out': latest_conn.checked_out,
                    'checked_in': latest_conn.checked_in,
                    'overflow': latest_conn.overflow,
                    'invalid': latest_conn.invalid,
                    'avg_connection_time': latest_conn.avg_connection_time
                }
            
            # 最新缓存指标
            if self._cache_metrics:
                latest_cache = self._cache_metrics[-1]
                summary['cache'] = {
                    'hit_ratio': round(latest_cache.hit_ratio, 4),
                    'total_requests': latest_cache.total_requests,
                    'cache_size': latest_cache.cache_size,
                    'memory_usage_mb': round(latest_cache.memory_usage, 2),
                    'avg_response_time_ms': latest_cache.avg_response_time
                }
            
            return summary
    
    def clear_metrics(self) -> None:
        """清空所有指标"""
        with self._lock:
            self._memory_metrics.clear()
            self._connection_metrics.clear()
            self._cache_metrics.clear()
            self._system_metrics.clear()
        logger.info("性能指标已清空")
    
    def generate_health_report(self) -> Dict[str, Any]:
        """生成健康状况报告"""
        summary = self.get_current_metrics_summary()
        
        health_status = "healthy"
        warnings = []
        
        # 检查内存使用
        if summary.get('memory'):
            memory = summary['memory']
            if memory['usage_percent'] > 90:
                health_status = "critical"
                warnings.append("内存使用率过高 (>90%)")
            elif memory['usage_percent'] > 80:
                health_status = "warning"
                warnings.append("内存使用率较高 (>80%)")
        
        # 检查CPU使用
        if summary.get('system'):
            system = summary['system']
            if system['cpu_percent'] > 90:
                health_status = "critical"
                warnings.append("CPU使用率过高 (>90%)")
            elif system['cpu_percent'] > 80:
                health_status = "warning"
                warnings.append("CPU使用率较高 (>80%)")
        
        # 检查缓存命中率
        if summary.get('cache'):
            cache = summary['cache']
            if cache['hit_ratio'] < 0.5:
                if health_status != "critical":
                    health_status = "warning"
                warnings.append(f"缓存命中率较低 ({cache['hit_ratio']:.2%})")
        
        return {
            'health_status': health_status,
            'warnings': warnings,
            'metrics_summary': summary,
            'generated_at': datetime.now().isoformat()
        }


# 全局指标收集器实例
global_metrics_collector = MetricsCollector()


def start_metrics_collection(interval: int = 60) -> None:
    """启动全局指标收集"""
    global_metrics_collector.collection_interval = interval
    global_metrics_collector.start_collection()


def stop_metrics_collection() -> None:
    """停止全局指标收集"""
    global_metrics_collector.stop_collection()


def get_current_metrics() -> Dict[str, Any]:
    """获取当前性能指标"""
    return global_metrics_collector.get_current_metrics_summary()


def get_health_report() -> Dict[str, Any]:
    """获取系统健康报告"""
    return global_metrics_collector.generate_health_report()


def record_connection_pool_metrics(pool_size: int, checked_out: int, 
                                 checked_in: int, overflow: int = 0,
                                 invalid: int = 0) -> None:
    """记录连接池指标"""
    metrics = ConnectionPoolMetrics(
        pool_size=pool_size,
        checked_out=checked_out,
        checked_in=checked_in,
        overflow=overflow,
        invalid=invalid
    )
    global_metrics_collector.record_connection_metrics(metrics)


def record_cache_performance(total_requests: int, cache_hits: int,
                           cache_size: int, memory_usage: float = 0.0) -> None:
    """记录缓存性能指标"""
    metrics = CacheMetrics(
        total_requests=total_requests,
        cache_hits=cache_hits,
        cache_misses=total_requests - cache_hits,
        cache_size=cache_size,
        memory_usage=memory_usage
    )
    global_metrics_collector.record_cache_metrics(metrics) 