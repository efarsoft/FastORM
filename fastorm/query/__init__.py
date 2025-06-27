"""
FastORM查询模块

包含查询构建器、分页、缓存、软删除和批量操作功能
"""

from .builder import QueryBuilder
from .pagination import Paginator
from .cache import QueryCache
from .soft_delete import SoftDeleteQueryBuilder

# 导入批量操作模块
from .batch import (
    BatchEngine, BatchConfig, BatchContext,
    BatchInsert, BatchUpdate, BatchDelete, BatchUpsert,
    BatchError, BatchValidationError, BatchTransactionError
)

__all__ = [
    # 查询构建器
    'QueryBuilder',
    
    # 分页
    'Paginator',
    
    # 缓存
    'QueryCache',
    
    # 软删除
    'SoftDeleteQueryBuilder',
    
    # 批量操作
    'BatchEngine',
    'BatchConfig', 
    'BatchContext',
    'BatchInsert',
    'BatchUpdate',
    'BatchDelete',
    'BatchUpsert',
    'BatchError',
    'BatchValidationError',
    'BatchTransactionError',
] 