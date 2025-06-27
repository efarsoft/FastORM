"""
FastORM批量操作系统模块

基于SQLAlchemy 2.0的高性能批量操作系统，提供：
- 批量插入、更新、删除操作
- 事务管理和回滚
- 数据验证和转换
- 进度监控和错误处理
- 异步批量操作支持
- 内存优化和流式处理
"""

from .decorators import batch_operation
from .decorators import monitor_batch
from .decorators import retry_batch
from .decorators import validate_batch
from .engine import BatchConfig
from .engine import BatchContext
from .engine import BatchEngine
from .exceptions import BatchError
from .exceptions import BatchMemoryError
from .exceptions import BatchTimeoutError
from .exceptions import BatchTransactionError
from .exceptions import BatchValidationError
from .exceptions import convert_batch_error
from .manager import BatchManager
from .manager import BatchSession
from .manager import BatchTransaction
from .monitor import BatchMonitor
from .monitor import BatchStats
from .monitor import ProgressTracker
from .operations import BatchDelete
from .operations import BatchInsert
from .operations import BatchOperation
from .operations import BatchUpdate
from .operations import BatchUpsert
from .processors import DataProcessor
from .processors import ProcessorChain
from .processors import TransformationProcessor
from .processors import ValidationProcessor

__all__ = [
    # 批量引擎
    "BatchEngine",
    "BatchContext",
    "BatchConfig",
    # 批量操作
    "BatchInsert",
    "BatchUpdate",
    "BatchDelete",
    "BatchUpsert",
    "BatchOperation",
    # 数据处理器
    "DataProcessor",
    "ValidationProcessor",
    "TransformationProcessor",
    "ProcessorChain",
    # 批量管理
    "BatchManager",
    "BatchTransaction",
    "BatchSession",
    # 监控
    "BatchMonitor",
    "ProgressTracker",
    "BatchStats",
    # 异常
    "BatchError",
    "BatchValidationError",
    "BatchTransactionError",
    "BatchTimeoutError",
    "BatchMemoryError",
    "convert_batch_error",
    # 装饰器
    "batch_operation",
    "validate_batch",
    "monitor_batch",
    "retry_batch",
]
