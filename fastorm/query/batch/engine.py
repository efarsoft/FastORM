"""
FastORM批量操作引擎模块

提供高性能的批量操作引擎，支持：
- 批量插入、更新、删除操作
- 事务管理和自动回滚
- 内存优化和流式处理
- 进度监控和错误处理
- 异步批量操作支持
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from collections.abc import Iterator
from contextlib import asynccontextmanager
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from typing import Any, Callable, Optional, Union

import psutil
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .exceptions import BatchError
from .exceptions import BatchMemoryError
from .exceptions import convert_batch_error


@dataclass
class BatchConfig:
    """批量操作配置"""

    # 批量处理配置
    batch_size: int = 1000
    max_batch_size: int = 10000
    chunk_size: int = 100

    # 性能配置
    enable_streaming: bool = True
    memory_limit_mb: float = 512.0
    prefetch_size: int = 100

    # 事务配置
    use_transactions: bool = True
    transaction_timeout: float = 300.0
    auto_commit: bool = True
    auto_rollback: bool = True

    # 异步配置
    async_timeout: float = 600.0
    max_concurrent_batches: int = 5

    # 重试配置
    enable_retry: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0

    # 验证配置
    validate_data: bool = True
    skip_invalid_records: bool = False

    # 监控配置
    enable_monitoring: bool = True
    progress_callback: Optional[Callable] = None

    # 优化配置
    disable_autoflush: bool = True
    disable_expire_on_commit: bool = True
    bulk_insert_mappings: bool = True

    def copy(self, **kwargs) -> "BatchConfig":
        """创建配置副本"""
        values = {
            "batch_size": self.batch_size,
            "max_batch_size": self.max_batch_size,
            "chunk_size": self.chunk_size,
            "enable_streaming": self.enable_streaming,
            "memory_limit_mb": self.memory_limit_mb,
            "prefetch_size": self.prefetch_size,
            "use_transactions": self.use_transactions,
            "transaction_timeout": self.transaction_timeout,
            "auto_commit": self.auto_commit,
            "auto_rollback": self.auto_rollback,
            "async_timeout": self.async_timeout,
            "max_concurrent_batches": self.max_concurrent_batches,
            "enable_retry": self.enable_retry,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "validate_data": self.validate_data,
            "skip_invalid_records": self.skip_invalid_records,
            "enable_monitoring": self.enable_monitoring,
            "progress_callback": self.progress_callback,
            "disable_autoflush": self.disable_autoflush,
            "disable_expire_on_commit": self.disable_expire_on_commit,
            "bulk_insert_mappings": self.bulk_insert_mappings,
        }
        values.update(kwargs)
        return BatchConfig(**values)


@dataclass
class BatchContext:
    """批量操作上下文"""

    # 操作信息
    operation_type: str  # insert, update, delete, upsert
    model_class: type
    table_name: str

    # 批量配置
    config: BatchConfig = field(default_factory=BatchConfig)

    # 执行状态
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    current_batch: int = 0

    # 时间跟踪
    start_time: float = field(default_factory=time.time)
    last_progress_time: float = field(default_factory=time.time)

    # 错误处理
    errors: list[BatchError] = field(default_factory=list)
    failed_data: list[dict[str, Any]] = field(default_factory=list)

    # 事务管理
    transaction_id: str | None = None
    rollback_attempted: bool = False
    rollback_successful: bool = False

    # 内存监控
    initial_memory_mb: float = field(
        default_factory=lambda: psutil.Process().memory_info().rss / 1024 / 1024
    )
    current_memory_mb: float = field(
        default_factory=lambda: psutil.Process().memory_info().rss / 1024 / 1024
    )

    # 异步支持
    semaphore: asyncio.Semaphore | None = None

    def add_error(self, error: BatchError) -> None:
        """添加错误"""
        self.errors.append(error)
        self.failed_records += 1

    def add_failed_data(self, data: dict[str, Any]) -> None:
        """添加失败数据"""
        self.failed_data.append(data)

    def update_progress(self, processed: int) -> None:
        """更新进度"""
        self.processed_records += processed
        self.last_progress_time = time.time()

        # 更新内存使用情况
        self.current_memory_mb = psutil.Process().memory_info().rss / 1024 / 1024

        # 检查内存限制
        if self.current_memory_mb > self.config.memory_limit_mb:
            raise BatchMemoryError(
                "内存使用超过限制",
                memory_used_mb=self.current_memory_mb,
                memory_limit_mb=self.config.memory_limit_mb,
                operation=self.operation_type,
                processed_count=self.processed_records,
            )

        # 调用进度回调
        if self.config.progress_callback:
            try:
                self.config.progress_callback(self.get_progress_info())
            except Exception:
                pass  # 忽略回调错误

    def get_progress_info(self) -> dict[str, Any]:
        """获取进度信息"""
        elapsed_time = time.time() - self.start_time
        progress_rate = self.processed_records / elapsed_time if elapsed_time > 0 else 0

        return {
            "operation": self.operation_type,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "failed_records": self.failed_records,
            "current_batch": self.current_batch,
            "progress_percentage": (
                (self.processed_records / self.total_records * 100)
                if self.total_records > 0
                else 0
            ),
            "elapsed_time": elapsed_time,
            "processing_rate": progress_rate,
            "memory_usage_mb": self.current_memory_mb,
            "estimated_time_remaining": (
                (self.total_records - self.processed_records) / progress_rate
                if progress_rate > 0
                else 0
            ),
        }

    def get_elapsed_time(self) -> float:
        """获取执行时间"""
        return time.time() - self.start_time

    def is_memory_warning(self) -> bool:
        """检查是否接近内存限制"""
        return self.current_memory_mb > (self.config.memory_limit_mb * 0.8)


class BatchEngine:
    """批量操作引擎"""

    def __init__(
        self, session: Session | AsyncSession, config: BatchConfig | None = None
    ):
        self.session = session
        self.config = config or BatchConfig()
        self.is_async = isinstance(session, AsyncSession)

        # 统计信息
        self._stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_records_processed": 0,
            "total_time_spent": 0.0,
            "average_processing_rate": 0.0,
        }

    async def batch_insert(
        self,
        model_class: type,
        data: list[dict[str, Any]] | AsyncGenerator[dict[str, Any], None],
        config: BatchConfig | None = None,
    ) -> dict[str, Any]:
        """批量插入操作"""

        effective_config = config or self.config
        context = BatchContext(
            operation_type="insert",
            model_class=model_class,
            table_name=model_class.__tablename__,
            config=effective_config,
        )

        if self.is_async:
            return await self._async_batch_insert(context, data)
        else:
            return self._sync_batch_insert(context, data)

    async def batch_update(
        self,
        model_class: type,
        data: list[dict[str, Any]] | AsyncGenerator[dict[str, Any], None],
        where_fields: list[str],
        config: BatchConfig | None = None,
    ) -> dict[str, Any]:
        """批量更新操作"""

        effective_config = config or self.config
        context = BatchContext(
            operation_type="update",
            model_class=model_class,
            table_name=model_class.__tablename__,
            config=effective_config,
        )
        context.where_fields = where_fields

        if self.is_async:
            return await self._async_batch_update(context, data)
        else:
            return self._sync_batch_update(context, data)

    async def batch_delete(
        self,
        model_class: type,
        conditions: list[dict[str, Any]] | AsyncGenerator[dict[str, Any], None],
        config: BatchConfig | None = None,
    ) -> dict[str, Any]:
        """批量删除操作"""

        effective_config = config or self.config
        context = BatchContext(
            operation_type="delete",
            model_class=model_class,
            table_name=model_class.__tablename__,
            config=effective_config,
        )

        if self.is_async:
            return await self._async_batch_delete(context, conditions)
        else:
            return self._sync_batch_delete(context, conditions)

    async def batch_upsert(
        self,
        model_class: type,
        data: list[dict[str, Any]] | AsyncGenerator[dict[str, Any], None],
        conflict_fields: list[str],
        config: BatchConfig | None = None,
    ) -> dict[str, Any]:
        """批量插入或更新操作"""

        effective_config = config or self.config
        context = BatchContext(
            operation_type="upsert",
            model_class=model_class,
            table_name=model_class.__tablename__,
            config=effective_config,
        )
        context.conflict_fields = conflict_fields

        if self.is_async:
            return await self._async_batch_upsert(context, data)
        else:
            return self._sync_batch_upsert(context, data)

    async def _async_batch_insert(
        self,
        context: BatchContext,
        data: list[dict[str, Any]] | AsyncGenerator[dict[str, Any], None],
    ) -> dict[str, Any]:
        """异步批量插入实现"""

        try:
            async with self._async_transaction_context(context):
                # 准备数据迭代器
                data_iterator = self._prepare_async_data_iterator(data, context)

                # 分批处理
                async for batch in self._chunk_async_data(
                    data_iterator, context.config.batch_size
                ):
                    await self._process_async_insert_batch(context, batch)
                    context.current_batch += 1

                if context.config.auto_commit:
                    await self.session.commit()

                return self._build_result(context)

        except Exception as e:
            error = convert_batch_error(
                e,
                "async_batch_insert",
                {"model": context.model_class.__name__, "table": context.table_name},
            )
            context.add_error(error)

            if context.config.auto_rollback:
                await self._attempt_async_rollback(context)

            raise error

    def _sync_batch_insert(
        self,
        context: BatchContext,
        data: list[dict[str, Any]] | Iterator[dict[str, Any]],
    ) -> dict[str, Any]:
        """同步批量插入实现"""

        try:
            with self._sync_transaction_context(context):
                # 准备数据迭代器
                data_iterator = self._prepare_sync_data_iterator(data, context)

                # 分批处理
                for batch in self._chunk_sync_data(
                    data_iterator, context.config.batch_size
                ):
                    self._process_sync_insert_batch(context, batch)
                    context.current_batch += 1

                if context.config.auto_commit:
                    self.session.commit()

                return self._build_result(context)

        except Exception as e:
            error = convert_batch_error(
                e,
                "sync_batch_insert",
                {"model": context.model_class.__name__, "table": context.table_name},
            )
            context.add_error(error)

            if context.config.auto_rollback:
                self._attempt_sync_rollback(context)

            raise error

    async def _process_async_insert_batch(
        self, context: BatchContext, batch: list[dict[str, Any]]
    ) -> None:
        """处理异步插入批次"""

        try:
            if context.config.bulk_insert_mappings:
                # 使用bulk_insert_mappings进行高性能插入
                await self.session.execute(insert(context.model_class.__table__), batch)
            else:
                # 使用传统方式
                instances = [context.model_class(**record) for record in batch]
                self.session.add_all(instances)

            context.update_progress(len(batch))

        except Exception as e:
            # 记录失败的批次
            for record in batch:
                context.add_failed_data(record)

            if not context.config.skip_invalid_records:
                raise

    def _process_sync_insert_batch(
        self, context: BatchContext, batch: list[dict[str, Any]]
    ) -> None:
        """处理同步插入批次"""

        try:
            if context.config.bulk_insert_mappings:
                # 使用bulk_insert_mappings进行高性能插入
                self.session.execute(insert(context.model_class.__table__), batch)
            else:
                # 使用传统方式
                instances = [context.model_class(**record) for record in batch]
                self.session.add_all(instances)

            context.update_progress(len(batch))

        except Exception as e:
            # 记录失败的批次
            for record in batch:
                context.add_failed_data(record)

            if not context.config.skip_invalid_records:
                raise

    @asynccontextmanager
    async def _async_transaction_context(self, context: BatchContext):
        """异步事务上下文管理器"""

        if context.config.use_transactions:
            # 配置session参数
            if context.config.disable_autoflush:
                self.session.autoflush = False
            if context.config.disable_expire_on_commit:
                self.session.expire_on_commit = False

            context.transaction_id = f"batch_{int(time.time() * 1000)}"

            try:
                yield
            except Exception:
                context.rollback_attempted = True
                try:
                    await self.session.rollback()
                    context.rollback_successful = True
                except Exception:
                    context.rollback_successful = False
                raise
        else:
            yield

    @contextmanager
    def _sync_transaction_context(self, context: BatchContext):
        """同步事务上下文管理器"""

        if context.config.use_transactions:
            # 配置session参数
            if context.config.disable_autoflush:
                self.session.autoflush = False
            if context.config.disable_expire_on_commit:
                self.session.expire_on_commit = False

            context.transaction_id = f"batch_{int(time.time() * 1000)}"

            try:
                yield
            except Exception:
                context.rollback_attempted = True
                try:
                    self.session.rollback()
                    context.rollback_successful = True
                except Exception:
                    context.rollback_successful = False
                raise
        else:
            yield

    async def _prepare_async_data_iterator(
        self,
        data: list[dict[str, Any]] | AsyncGenerator[dict[str, Any], None],
        context: BatchContext,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """准备异步数据迭代器"""

        if isinstance(data, list):
            context.total_records = len(data)
            for item in data:
                yield item
        else:
            # 异步生成器
            async for item in data:
                context.total_records += 1
                yield item

    def _prepare_sync_data_iterator(
        self,
        data: list[dict[str, Any]] | Iterator[dict[str, Any]],
        context: BatchContext,
    ) -> Iterator[dict[str, Any]]:
        """准备同步数据迭代器"""

        if isinstance(data, list):
            context.total_records = len(data)
            return iter(data)
        else:
            # 迭代器，无法预知总数
            return data

    async def _chunk_async_data(
        self, data_iterator: AsyncGenerator[dict[str, Any], None], chunk_size: int
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        """异步数据分块"""

        batch = []
        async for item in data_iterator:
            batch.append(item)
            if len(batch) >= chunk_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def _chunk_sync_data(
        self, data_iterator: Iterator[dict[str, Any]], chunk_size: int
    ) -> Iterator[list[dict[str, Any]]]:
        """同步数据分块"""

        batch = []
        for item in data_iterator:
            batch.append(item)
            if len(batch) >= chunk_size:
                yield batch
                batch = []

        if batch:
            yield batch

    async def _attempt_async_rollback(self, context: BatchContext) -> None:
        """尝试异步回滚"""

        context.rollback_attempted = True
        try:
            await self.session.rollback()
            context.rollback_successful = True
        except Exception:
            context.rollback_successful = False

    def _attempt_sync_rollback(self, context: BatchContext) -> None:
        """尝试同步回滚"""

        context.rollback_attempted = True
        try:
            self.session.rollback()
            context.rollback_successful = True
        except Exception:
            context.rollback_successful = False

    def _build_result(self, context: BatchContext) -> dict[str, Any]:
        """构建操作结果"""

        elapsed_time = context.get_elapsed_time()
        processing_rate = (
            context.processed_records / elapsed_time if elapsed_time > 0 else 0
        )

        # 更新统计信息
        self._stats["total_operations"] += 1
        self._stats["total_records_processed"] += context.processed_records
        self._stats["total_time_spent"] += elapsed_time

        if context.errors:
            self._stats["failed_operations"] += 1
        else:
            self._stats["successful_operations"] += 1

        self._stats["average_processing_rate"] = (
            self._stats["total_records_processed"] / self._stats["total_time_spent"]
            if self._stats["total_time_spent"] > 0
            else 0
        )

        return {
            "operation": context.operation_type,
            "model": context.model_class.__name__,
            "table": context.table_name,
            "total_records": context.total_records,
            "processed_records": context.processed_records,
            "failed_records": context.failed_records,
            "success_rate": (
                (context.processed_records - context.failed_records)
                / context.processed_records
                * 100
                if context.processed_records > 0
                else 0
            ),
            "elapsed_time": elapsed_time,
            "processing_rate": processing_rate,
            "memory_used_mb": context.current_memory_mb,
            "transaction_info": {
                "transaction_id": context.transaction_id,
                "rollback_attempted": context.rollback_attempted,
                "rollback_successful": context.rollback_successful,
            }
            if context.transaction_id
            else None,
            "errors": [error.get_error_summary() for error in context.errors],
            "config": {
                "batch_size": context.config.batch_size,
                "use_transactions": context.config.use_transactions,
                "streaming_enabled": context.config.enable_streaming,
            },
        }

    def get_stats(self) -> dict[str, Any]:
        """获取引擎统计信息"""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_records_processed": 0,
            "total_time_spent": 0.0,
            "average_processing_rate": 0.0,
        }

    # 其他批量操作方法的占位符实现
    async def _async_batch_update(self, context, data):
        """异步批量更新 - 待实现"""
        pass

    def _sync_batch_update(self, context, data):
        """同步批量更新 - 待实现"""
        pass

    async def _async_batch_delete(self, context, conditions):
        """异步批量删除 - 待实现"""
        pass

    def _sync_batch_delete(self, context, conditions):
        """同步批量删除 - 待实现"""
        pass

    async def _async_batch_upsert(self, context, data):
        """异步批量Upsert - 待实现"""
        pass

    def _sync_batch_upsert(self, context, data):
        """同步批量Upsert - 待实现"""
        pass
