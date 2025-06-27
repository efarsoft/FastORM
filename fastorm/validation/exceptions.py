"""
FastORM 验证异常系统

基于Pydantic 2.11的现代异常处理机制
"""

from typing import Any, Dict, List, Optional
from pydantic import ValidationError as PydanticValidationError


class ValidationError(Exception):
    """基础验证异常类"""
    
    def __init__(
        self, 
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value
        self.errors = errors or []
    
    def __str__(self) -> str:
        if self.field:
            return f"Validation error in field '{self.field}': {self.message}"
        return f"Validation error: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": "validation_error",
            "message": self.message,
            "field": self.field,
            "value": self.value,
            "errors": self.errors
        }


class FieldValidationError(ValidationError):
    """字段验证异常"""
    
    def __init__(
        self,
        field: str,
        value: Any,
        message: str,
        validator_name: Optional[str] = None,
        constraint: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            field=field,
            value=value
        )
        self.validator_name = validator_name
        self.constraint = constraint
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            "type": "field_validation_error",
            "validator_name": self.validator_name,
            "constraint": self.constraint
        })
        return result


class ModelValidationError(ValidationError):
    """模型级验证异常"""
    
    def __init__(
        self,
        model_name: str,
        message: str,
        field_errors: Optional[List[FieldValidationError]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message)
        self.model_name = model_name
        self.field_errors = field_errors or []
        self.context = context or {}
    
    def add_field_error(self, error: FieldValidationError) -> None:
        """添加字段错误"""
        self.field_errors.append(error)
    
    def has_field_errors(self) -> bool:
        """是否有字段错误"""
        return len(self.field_errors) > 0
    
    def get_field_errors(self, field: str) -> List[FieldValidationError]:
        """获取特定字段的错误"""
        return [
            error for error in self.field_errors 
            if error.field == field
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            "type": "model_validation_error",
            "model_name": self.model_name,
            "field_errors": [error.to_dict() for error in self.field_errors],
            "context": self.context
        })
        return result
    
    def __str__(self) -> str:
        base_message = (
            f"Model validation error in {self.model_name}: {self.message}"
        )
        if self.field_errors:
            field_messages = [str(error) for error in self.field_errors]
            error_list = "\n".join(f"  - {msg}" for msg in field_messages)
            return f"{base_message}\nField errors:\n{error_list}"
        return base_message


class AsyncValidationError(ValidationError):
    """异步验证异常"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        async_validator_name: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        super().__init__(message=message, field=field, value=value)
        self.async_validator_name = async_validator_name
        self.timeout = timeout
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            "type": "async_validation_error",
            "async_validator_name": self.async_validator_name,
            "timeout": self.timeout
        })
        return result


def convert_pydantic_error(
    pydantic_error: PydanticValidationError
) -> ModelValidationError:
    """将Pydantic验证错误转换为FastORM验证错误
    
    Args:
        pydantic_error: Pydantic验证错误
        
    Returns:
        FastORM模型验证错误
    """
    field_errors = []
    
    for error in pydantic_error.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_error = FieldValidationError(
            field=field_path,
            value=error.get("input"),
            message=error["msg"],
            validator_name=error["type"],
            constraint=error.get("ctx")
        )
        field_errors.append(field_error)
    
    return ModelValidationError(
        model_name="Unknown",
        message=f"Validation failed with {len(field_errors)} errors",
        field_errors=field_errors
    )


def format_validation_errors(
    errors: List[ValidationError]
) -> Dict[str, Any]:
    """格式化验证错误为统一输出格式
    
    Args:
        errors: 验证错误列表
        
    Returns:
        格式化的错误信息
    """
    return {
        "validation_failed": True,
        "error_count": len(errors),
        "errors": [error.to_dict() for error in errors],
        "summary": _create_error_summary(errors)
    }


def _create_error_summary(errors: List[ValidationError]) -> Dict[str, Any]:
    """创建错误摘要"""
    field_errors = {}
    model_errors = []
    
    for error in errors:
        if isinstance(error, FieldValidationError):
            if error.field not in field_errors:
                field_errors[error.field] = []
            field_errors[error.field].append(error.message)
        elif isinstance(error, ModelValidationError):
            model_errors.append(error.message)
    
    return {
        "field_errors": field_errors,
        "model_errors": model_errors,
        "total_field_errors": len(field_errors),
        "total_model_errors": len(model_errors)
    } 