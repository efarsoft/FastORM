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

from .engine import BatchConfig
from .engine import BatchContext
from .engine import BatchEngine
from .exceptions import BatchError
from .exceptions import BatchMemoryError
from .exceptions import BatchTimeoutError
from .exceptions import BatchTransactionError
from .exceptions import BatchValidationError
from .exceptions import convert_batch_error
from .operations import BatchDelete
from .operations import BatchInsert
from .operations import BatchOperation
from .operations import BatchUpdate
from .operations import BatchUpsert

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
    # 异常
    "BatchError",
    "BatchValidationError",
    "BatchTransactionError",
    "BatchTimeoutError",
    "BatchMemoryError",
    "convert_batch_error",
]
