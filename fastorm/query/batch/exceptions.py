"""
FastORM批量操作异常模块

提供批量操作过程中可能出现的各种异常类型
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.exc import SQLAlchemyError


class BatchError(Exception):
    """批量操作基础异常"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        batch_size: Optional[int] = None,
        processed_count: int = 0,
        failed_records: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.batch_size = batch_size
        self.processed_count = processed_count
        self.failed_records = failed_records or []
        self.context = context or {}
    
    def __str__(self) -> str:
        base_msg = f"批量操作错误: {self.message}"
        if self.operation:
            base_msg += f" (操作: {self.operation})"
        if self.batch_size:
            base_msg += f" (批量大小: {self.batch_size})"
        if self.processed_count > 0:
            base_msg += f" (已处理: {self.processed_count})"
        return base_msg
    
    def add_failed_record(self, record: Dict[str, Any]) -> None:
        """添加失败记录"""
        self.failed_records.append(record)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        return {
            'message': self.message,
            'operation': self.operation,
            'batch_size': self.batch_size,
            'processed_count': self.processed_count,
            'failed_count': len(self.failed_records),
            'context': self.context
        }


class BatchValidationError(BatchError):
    """批量验证异常"""
    
    def __init__(
        self,
        message: str,
        validation_errors: List[Dict[str, Any]],
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        error_count = len(self.validation_errors)
        return f"{base_msg} (验证错误数量: {error_count})"
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证错误摘要"""
        error_types = {}
        for error in self.validation_errors:
            error_type = error.get('type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': len(self.validation_errors),
            'error_types': error_types,
            'sample_errors': self.validation_errors[:5]  # 显示前5个错误
        }


class BatchTransactionError(BatchError):
    """批量事务异常"""
    
    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        rollback_attempted: bool = False,
        rollback_successful: bool = False,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.transaction_id = transaction_id
        self.rollback_attempted = rollback_attempted
        self.rollback_successful = rollback_successful
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.transaction_id:
            base_msg += f" (事务ID: {self.transaction_id})"
        if self.rollback_attempted:
            status = "成功" if self.rollback_successful else "失败"
            base_msg += f" (回滚: {status})"
        return base_msg


class BatchTimeoutError(BatchError):
    """批量操作超时异常"""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        elapsed_seconds: float,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        return (f"{base_msg} (超时: {self.timeout_seconds}s, "
                f"已用时: {self.elapsed_seconds:.2f}s)")


class BatchMemoryError(BatchError):
    """批量操作内存异常"""
    
    def __init__(
        self,
        message: str,
        memory_used_mb: Optional[float] = None,
        memory_limit_mb: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.memory_used_mb = memory_used_mb
        self.memory_limit_mb = memory_limit_mb
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.memory_used_mb and self.memory_limit_mb:
            base_msg += (f" (内存使用: {self.memory_used_mb:.1f}MB/"
                        f"{self.memory_limit_mb:.1f}MB)")
        return base_msg


class BatchIntegrityError(BatchError):
    """批量操作完整性异常"""
    
    def __init__(
        self,
        message: str,
        constraint_name: Optional[str] = None,
        violating_records: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.constraint_name = constraint_name
        self.violating_records = violating_records or []
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.constraint_name:
            base_msg += f" (约束: {self.constraint_name})"
        if self.violating_records:
            base_msg += f" (违反记录数: {len(self.violating_records)})"
        return base_msg


class BatchPermissionError(BatchError):
    """批量操作权限异常"""
    
    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required_permission = required_permission
        self.user_id = user_id
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.required_permission:
            base_msg += f" (需要权限: {self.required_permission})"
        if self.user_id:
            base_msg += f" (用户: {self.user_id})"
        return base_msg


class BatchConcurrencyError(BatchError):
    """批量操作并发异常"""
    
    def __init__(
        self,
        message: str,
        concurrent_operations: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.concurrent_operations = concurrent_operations
        self.max_concurrent = max_concurrent
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.concurrent_operations and self.max_concurrent:
            base_msg += (f" (并发操作: {self.concurrent_operations}/"
                        f"{self.max_concurrent})")
        return base_msg


def convert_batch_error(
    error: Exception,
    operation: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> BatchError:
    """将通用异常转换为批量操作异常"""
    
    if isinstance(error, BatchError):
        return error
    
    # SQLAlchemy错误
    if isinstance(error, SQLAlchemyError):
        error_message = str(error)
        
        # 完整性约束错误
        if "integrity constraint" in error_message.lower():
            return BatchIntegrityError(
                f"数据完整性错误: {error_message}",
                operation=operation,
                context=context
            )
        
        # 超时错误
        if "timeout" in error_message.lower():
            return BatchTimeoutError(
                f"数据库操作超时: {error_message}",
                timeout_seconds=0,
                elapsed_seconds=0,
                operation=operation,
                context=context
            )
        
        # 其他SQLAlchemy错误
        return BatchError(
            f"数据库操作错误: {error_message}",
            operation=operation,
            context=context
        )
    
    # 内存错误
    if isinstance(error, MemoryError):
        return BatchMemoryError(
            f"内存不足: {str(error)}",
            operation=operation,
            context=context
        )
    
    # 超时错误
    if isinstance(error, TimeoutError):
        return BatchTimeoutError(
            f"操作超时: {str(error)}",
            timeout_seconds=0,
            elapsed_seconds=0,
            operation=operation,
            context=context
        )
    
    # 权限错误
    if isinstance(error, PermissionError):
        return BatchPermissionError(
            f"权限不足: {str(error)}",
            operation=operation,
            context=context
        )
    
    # 通用错误
    return BatchError(
        f"批量操作失败: {str(error)}",
        operation=operation,
        context=context
    )


def format_batch_errors(
    errors: List[BatchError],
    include_details: bool = True
) -> Dict[str, Any]:
    """格式化批量错误列表"""
    
    formatted_errors = []
    error_summary = {}
    
    for error in errors:
        error_type = error.__class__.__name__
        error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        error_dict = {
            'type': error_type,
            'message': error.message,
            'operation': error.operation,
            'processed_count': error.processed_count
        }
        
        if include_details:
            if hasattr(error, 'validation_errors'):
                error_dict['validation_summary'] = error.get_validation_summary()
            
            if hasattr(error, 'transaction_id'):
                error_dict['transaction_id'] = error.transaction_id
                error_dict['rollback_status'] = {
                    'attempted': error.rollback_attempted,
                    'successful': error.rollback_successful
                }
            
            if hasattr(error, 'timeout_seconds'):
                error_dict['timeout_info'] = {
                    'timeout': error.timeout_seconds,
                    'elapsed': error.elapsed_seconds
                }
            
            if error.context:
                error_dict['context'] = error.context
        
        formatted_errors.append(error_dict)
    
    return {
        'total_errors': len(errors),
        'error_summary': error_summary,
        'errors': formatted_errors
    }


def get_error_recovery_suggestions(error: BatchError) -> List[str]:
    """获取错误恢复建议"""
    
    suggestions = []
    
    if isinstance(error, BatchValidationError):
        suggestions.extend([
            "检查输入数据格式和完整性",
            "验证必填字段是否完整",
            "确认数据类型匹配"
        ])
    
    elif isinstance(error, BatchTransactionError):
        suggestions.extend([
            "检查数据库连接状态",
            "减少批量大小以降低事务复杂度",
            "考虑使用分块处理"
        ])
    
    elif isinstance(error, BatchTimeoutError):
        suggestions.extend([
            "增加操作超时时间",
            "减少批量处理大小",
            "优化数据库查询性能",
            "检查数据库服务器性能"
        ])
    
    elif isinstance(error, BatchMemoryError):
        suggestions.extend([
            "减少批量处理大小",
            "启用流式处理模式",
            "释放不必要的内存引用",
            "考虑分批处理数据"
        ])
    
    elif isinstance(error, BatchIntegrityError):
        suggestions.extend([
            "检查数据完整性约束",
            "验证外键关系",
            "确认唯一性约束",
            "预处理重复数据"
        ])
    
    elif isinstance(error, BatchConcurrencyError):
        suggestions.extend([
            "减少并发操作数量",
            "增加重试机制",
            "使用排队系统处理请求"
        ])
    
    else:
        suggestions.extend([
            "检查错误详情和上下文",
            "验证输入参数",
            "查看系统日志获取更多信息"
        ])
    
    return suggestions 