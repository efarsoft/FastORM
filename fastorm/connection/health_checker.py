"""
FastORM 数据库健康检查和故障转移机制

提供数据库连接健康检查、故障检测和自动故障转移功能。
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.sql import text

if TYPE_CHECKING:
    from .database import Database

logger = logging.getLogger("fastorm.health_checker")


class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    response_time: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class DatabaseHealthChecker:
    """数据库健康检查器
    
    提供数据库连接健康检查、故障检测和自动故障转移功能。
    """
    
    def __init__(
        self,
        check_interval: int = 30,
        timeout: float = 5.0,
        max_retries: int = 3,
        failure_threshold: int = 3,
        recovery_threshold: int = 2
    ):
        """初始化健康检查器
        
        Args:
            check_interval: 检查间隔（秒）
            timeout: 单次检查超时时间（秒）
            max_retries: 最大重试次数
            failure_threshold: 连续失败阈值
            recovery_threshold: 连续成功恢复阈值
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        
        # 健康状态跟踪
        self._health_status: Dict[str, HealthStatus] = {}
        self._last_check_time: Dict[str, float] = {}
        self._consecutive_failures: Dict[str, int] = {}
        self._consecutive_successes: Dict[str, int] = {}
        self._check_results: Dict[str, HealthCheckResult] = {}
        
        # 故障转移状态
        self._failed_engines: Set[str] = set()
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
    
    async def check_engine_health(
        self, 
        engine: AsyncEngine,
        engine_name: str = "default"
    ) -> HealthCheckResult:
        """检查单个引擎的健康状态
        
        Args:
            engine: 数据库引擎
            engine_name: 引擎名称
            
        Returns:
            健康检查结果
        """
        start_time = time.time()
        
        try:
            # 执行简单的健康检查查询
            async with engine.begin() as conn:
                # 使用简单的SELECT 1查询检查连接
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            
            response_time = time.time() - start_time
            
            # 判断响应时间
            if response_time < 1.0:
                status = HealthStatus.HEALTHY
            elif response_time < 3.0:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                status=status,
                response_time=response_time,
                details={
                    "engine_name": engine_name,
                    "url": str(engine.url).replace(
                        engine.url.password or "", "***"
                    ) if engine.url.password else str(engine.url)
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.warning(
                f"Engine {engine_name} health check failed: {e}"
            )
            
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error=str(e),
                details={
                    "engine_name": engine_name,
                    "error_type": type(e).__name__
                }
            )
    
    async def check_all_engines(
        self, 
        engines: Dict[str, AsyncEngine]
    ) -> Dict[str, HealthCheckResult]:
        """检查所有引擎的健康状态
        
        Args:
            engines: 引擎字典
            
        Returns:
            所有引擎的健康检查结果
        """
        results = {}
        
        # 并发检查所有引擎
        tasks = [
            self.check_engine_health(engine, name)
            for name, engine in engines.items()
        ]
        
        if tasks:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (name, engine) in enumerate(engines.items()):
                result = check_results[i]
                
                if isinstance(result, Exception):
                    result = HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        response_time=self.timeout,
                        error=str(result),
                        details={"engine_name": name}
                    )
                
                results[name] = result
                self._update_health_status(name, result)
        
        return results
    
    def _update_health_status(
        self, 
        engine_name: str, 
        result: HealthCheckResult
    ) -> None:
        """更新引擎健康状态
        
        Args:
            engine_name: 引擎名称
            result: 健康检查结果
        """
        self._check_results[engine_name] = result
        self._last_check_time[engine_name] = result.timestamp
        
        if result.status == HealthStatus.HEALTHY:
            self._consecutive_failures[engine_name] = 0
            self._consecutive_successes[engine_name] = (
                self._consecutive_successes.get(engine_name, 0) + 1
            )
            
            # 检查是否从故障中恢复
            if (engine_name in self._failed_engines and 
                self._consecutive_successes[engine_name] >= self.recovery_threshold):
                self._failed_engines.discard(engine_name)
                logger.info(f"Engine {engine_name} recovered from failure")
                
        else:
            self._consecutive_successes[engine_name] = 0
            self._consecutive_failures[engine_name] = (
                self._consecutive_failures.get(engine_name, 0) + 1
            )
            
            # 检查是否需要标记为故障
            if (self._consecutive_failures[engine_name] >= self.failure_threshold):
                if engine_name not in self._failed_engines:
                    self._failed_engines.add(engine_name)
                    logger.error(f"Engine {engine_name} marked as failed")
        
        self._health_status[engine_name] = result.status
    
    def get_health_status(self, engine_name: str) -> HealthStatus:
        """获取引擎健康状态
        
        Args:
            engine_name: 引擎名称
            
        Returns:
            健康状态
        """
        return self._health_status.get(engine_name, HealthStatus.UNKNOWN)
    
    def is_engine_healthy(self, engine_name: str) -> bool:
        """检查引擎是否健康
        
        Args:
            engine_name: 引擎名称
            
        Returns:
            是否健康
        """
        return (
            engine_name not in self._failed_engines and
            self.get_health_status(engine_name) in {
                HealthStatus.HEALTHY, 
                HealthStatus.DEGRADED
            }
        )
    
    def get_healthy_engines(
        self, 
        engines: Dict[str, AsyncEngine]
    ) -> Dict[str, AsyncEngine]:
        """获取健康的引擎
        
        Args:
            engines: 所有引擎
            
        Returns:
            健康的引擎
        """
        return {
            name: engine 
            for name, engine in engines.items()
            if self.is_engine_healthy(name)
        }
    
    def get_failover_engine(
        self, 
        preferred_engines: list[str],
        available_engines: Dict[str, AsyncEngine]
    ) -> Optional[str]:
        """获取故障转移引擎
        
        Args:
            preferred_engines: 优先引擎列表
            available_engines: 可用引擎
            
        Returns:
            故障转移引擎名称
        """
        for engine_name in preferred_engines:
            if (engine_name in available_engines and 
                self.is_engine_healthy(engine_name)):
                return engine_name
        
        # 如果没有优先引擎可用，选择任何健康的引擎
        healthy_engines = self.get_healthy_engines(available_engines)
        if healthy_engines:
            return next(iter(healthy_engines.keys()))
        
        return None
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告
        
        Returns:
            详细的健康报告
        """
        return {
            "overall_status": self._get_overall_status(),
            "engines": {
                name: {
                    "status": status.value,
                    "last_check": self._last_check_time.get(name),
                    "consecutive_failures": self._consecutive_failures.get(name, 0),
                    "consecutive_successes": self._consecutive_successes.get(name, 0),
                    "is_failed": name in self._failed_engines,
                    "last_result": (
                        self._check_results[name].__dict__
                        if name in self._check_results else None
                    )
                }
                for name, status in self._health_status.items()
            },
            "failed_engines": list(self._failed_engines),
            "check_interval": self.check_interval,
            "failure_threshold": self.failure_threshold,
            "recovery_threshold": self.recovery_threshold
        }
    
    def _get_overall_status(self) -> str:
        """获取整体健康状态"""
        if not self._health_status:
            return HealthStatus.UNKNOWN.value
        
        statuses = list(self._health_status.values())
        
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY.value
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.DEGRADED.value
        else:
            return HealthStatus.DEGRADED.value
    
    async def start_monitoring(
        self, 
        engines_getter: callable
    ) -> None:
        """开始监控
        
        Args:
            engines_getter: 获取引擎字典的函数
        """
        if self._is_running:
            return
        
        self._is_running = True
        self._check_task = asyncio.create_task(
            self._monitoring_loop(engines_getter)
        )
        logger.info("Database health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """停止监控"""
        self._is_running = False
        
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None
        
        logger.info("Database health monitoring stopped")
    
    async def _monitoring_loop(self, engines_getter: callable) -> None:
        """监控循环"""
        while self._is_running:
            try:
                engines = engines_getter()
                if engines:
                    await self.check_all_engines(engines)
                    
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(min(self.check_interval, 10))


# 全局健康检查器实例
_health_checker: Optional[DatabaseHealthChecker] = None


def get_health_checker() -> DatabaseHealthChecker:
    """获取全局健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = DatabaseHealthChecker()
    return _health_checker


def setup_health_checker(**kwargs) -> DatabaseHealthChecker:
    """设置全局健康检查器"""
    global _health_checker
    _health_checker = DatabaseHealthChecker(**kwargs)
    return _health_checker


__all__ = [
    "HealthStatus",
    "HealthCheckResult", 
    "DatabaseHealthChecker",
    "get_health_checker",
    "setup_health_checker"
] 