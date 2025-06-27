"""
查询性能分析器

提供查询执行时间统计、SQL语句分析、内存使用监控等功能
"""

import logging
import threading
import time
from collections.abc import AsyncIterator
from collections.abc import Iterator
from contextlib import asynccontextmanager
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

# SQLAlchemy imports
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class QueryInfo:
    """查询信息数据类"""

    sql: str
    params: dict[str, Any]
    start_time: datetime
    end_time: datetime | None = None
    duration: float | None = None
    error: str | None = None
    stack_trace: str | None = None
    session_id: str | None = None

    def finish(self, error: str | None = None) -> None:
        """完成查询记录"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.error = error

    @property
    def is_slow(self) -> bool:
        """判断是否为慢查询（超过1秒）"""
        return self.duration is not None and self.duration > 1.0

    @property
    def is_success(self) -> bool:
        """判断查询是否成功"""
        return self.error is None


@dataclass
class ProfileSession:
    """性能分析会话"""

    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    queries: list[QueryInfo] = field(default_factory=list)
    total_queries: int = 0
    slow_queries: int = 0
    failed_queries: int = 0
    total_time: float = 0.0

    def add_query(self, query_info: QueryInfo) -> None:
        """添加查询信息"""
        self.queries.append(query_info)
        self.total_queries += 1

        if query_info.duration:
            self.total_time += query_info.duration

        if query_info.is_slow:
            self.slow_queries += 1

        if not query_info.is_success:
            self.failed_queries += 1

    @property
    def avg_query_time(self) -> float:
        """平均查询时间"""
        if self.total_queries > 0:
            return self.total_time / self.total_queries
        return 0.0

    @property
    def duration(self) -> float:
        """会话总时长"""
        return (datetime.now() - self.start_time).total_seconds()


class QueryProfiler:
    """查询性能分析器"""

    def __init__(self, enable_stack_trace: bool = False):
        self.enable_stack_trace = enable_stack_trace
        self.sessions: dict[str, ProfileSession] = {}
        self._current_session: str | None = None
        self._lock = threading.Lock()
        self._enabled = True

        # 注册SQLAlchemy事件监听器
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """设置SQLAlchemy事件监听器"""

        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            if not self._enabled or not self._current_session:
                return

            # 记录查询开始信息
            query_info = QueryInfo(
                sql=statement,
                params=parameters if not executemany else {},
                start_time=datetime.now(),
                session_id=self._current_session,
            )

            # 添加堆栈跟踪
            if self.enable_stack_trace:
                import traceback

                query_info.stack_trace = "".join(traceback.format_stack()[:-2])

            # 存储到上下文中
            context._fastorm_query_info = query_info

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            if not self._enabled or not self._current_session:
                return

            # 获取查询信息并完成记录
            query_info = getattr(context, "_fastorm_query_info", None)
            if query_info:
                query_info.finish()

                # 添加到当前会话
                with self._lock:
                    session = self.sessions.get(self._current_session)
                    if session:
                        session.add_query(query_info)

        @event.listens_for(Engine, "handle_error")
        def handle_error(exception_context):
            if not self._enabled or not self._current_session:
                return

            # 记录查询错误
            query_info = getattr(
                exception_context.execution_context, "_fastorm_query_info", None
            )
            if query_info:
                error_msg = str(exception_context.original_exception)
                query_info.finish(error=error_msg)

                # 添加到当前会话
                with self._lock:
                    session = self.sessions.get(self._current_session)
                    if session:
                        session.add_query(query_info)

    @contextmanager
    def profile(self, session_id: str | None = None) -> Iterator[ProfileSession]:
        """性能分析上下文管理器"""
        if not session_id:
            session_id = f"profile_{int(time.time() * 1000)}"

        # 创建新会话
        session = ProfileSession(session_id=session_id)

        with self._lock:
            self.sessions[session_id] = session
            old_session = self._current_session
            self._current_session = session_id

        try:
            yield session
        finally:
            with self._lock:
                self._current_session = old_session

    @asynccontextmanager
    async def async_profile(
        self, session_id: str | None = None
    ) -> AsyncIterator[ProfileSession]:
        """异步性能分析上下文管理器"""
        if not session_id:
            session_id = f"async_profile_{int(time.time() * 1000)}"

        # 创建新会话
        session = ProfileSession(session_id=session_id)

        with self._lock:
            self.sessions[session_id] = session
            old_session = self._current_session
            self._current_session = session_id

        try:
            yield session
        finally:
            with self._lock:
                self._current_session = old_session

    def get_session(self, session_id: str) -> ProfileSession | None:
        """获取分析会话"""
        return self.sessions.get(session_id)

    def get_all_sessions(self) -> dict[str, ProfileSession]:
        """获取所有分析会话"""
        return self.sessions.copy()

    def clear_sessions(self) -> None:
        """清空所有会话"""
        with self._lock:
            self.sessions.clear()

    def enable(self) -> None:
        """启用性能分析"""
        self._enabled = True

    def disable(self) -> None:
        """禁用性能分析"""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """检查是否已启用"""
        return self._enabled


# 全局性能分析器实例
_global_profiler = QueryProfiler()


def profile_query(session_id: str | None = None):
    """便捷的查询性能分析函数"""
    return _global_profiler.profile(session_id)


async def async_profile_query(
    session_id: str | None = None,
) -> AsyncIterator[ProfileSession]:
    """便捷的异步查询性能分析函数"""
    async with _global_profiler.async_profile(session_id) as session:
        yield session


def get_global_profiler() -> QueryProfiler:
    """获取全局性能分析器"""
    return _global_profiler


def enable_profiling() -> None:
    """启用全局性能分析"""
    _global_profiler.enable()


def disable_profiling() -> None:
    """禁用全局性能分析"""
    _global_profiler.disable()
