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

from .engine import (
    BatchEngine,
    BatchContext,
    BatchConfig
)
from .operations import (
    BatchInsert,
    BatchUpdate,
    BatchDelete,
    BatchUpsert,
    BatchOperation
)
from .processors import (
    DataProcessor,
    ValidationProcessor,
    TransformationProcessor,
    ProcessorChain
)
from .manager import (
    BatchManager,
    BatchTransaction,
    BatchSession
)
from .monitor import (
    BatchMonitor,
    ProgressTracker,
    BatchStats
)
from .exceptions import (
    BatchError,
    BatchValidationError,
    BatchTransactionError,
    BatchTimeoutError,
    BatchMemoryError,
    convert_batch_error
)
from .decorators import (
    batch_operation,
    validate_batch,
    monitor_batch,
    retry_batch
)

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
    "retry_batch"
] 