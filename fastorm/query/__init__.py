"""
FastORM查询模块

包含查询构建器、分页、缓存、软删除和批量操作功能
"""

from .batch import BatchConfig
from .batch import BatchContext
from .batch import BatchDelete

# 导入批量操作模块
from .batch import BatchEngine
from .batch import BatchError
from .batch import BatchInsert
from .batch import BatchTransactionError
from .batch import BatchUpdate
from .batch import BatchUpsert
from .batch import BatchValidationError
from .builder import QueryBuilder
from .cache import QueryCache
from .pagination import Paginator
from .soft_delete import SoftDeleteQueryBuilder

__all__ = [
    # 查询构建器
    "QueryBuilder",
    # 分页
    "Paginator",
    # 缓存
    "QueryCache",
    # 软删除
    "SoftDeleteQueryBuilder",
    # 批量操作
    "BatchEngine",
    "BatchConfig",
    "BatchContext",
    "BatchInsert",
    "BatchUpdate",
    "BatchDelete",
    "BatchUpsert",
    "BatchError",
    "BatchValidationError",
    "BatchTransactionError",
]
