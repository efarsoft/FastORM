"""
FastORM序列化异常模块

提供序列化过程中可能出现的各种异常类型
"""

from typing import Any

from pydantic import ValidationError as PydanticValidationError


class SerializationError(Exception):
    """序列化基础异常"""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        errors: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value
        self.errors = errors or []
        self.context = context or {}

    def __str__(self) -> str:
        if self.field:
            return f"序列化错误在字段 '{self.field}': {self.message}"
        return f"序列化错误: {self.message}"

    def add_error(self, error: dict[str, Any]) -> None:
        """添加错误信息"""
        self.errors.append(error)

    def get_error_summary(self) -> dict[str, Any]:
        """获取错误摘要"""
        return {
            "message": self.message,
            "field": self.field,
            "value": str(self.value) if self.value is not None else None,
            "error_count": len(self.errors),
            "context": self.context,
        }


class FieldSerializationError(SerializationError):
    """字段序列化异常"""

    def __init__(
        self,
        message: str,
        field: str,
        value: Any = None,
        serializer_name: str | None = None,
        field_type: str | None = None,
        **kwargs,
    ):
        super().__init__(message, field, value, **kwargs)
        self.serializer_name = serializer_name
        self.field_type = field_type

    def __str__(self) -> str:
        base_msg = f"字段 '{self.field}' 序列化失败: {self.message}"
        if self.serializer_name:
            base_msg += f" (序列化器: {self.serializer_name})"
        if self.field_type:
            base_msg += f" (字段类型: {self.field_type})"
        return base_msg


class RelationSerializationError(SerializationError):
    """关系序列化异常"""

    def __init__(
        self,
        message: str,
        relation_name: str,
        relation_type: str,
        target_model: str | None = None,
        **kwargs,
    ):
        super().__init__(message, field=relation_name, **kwargs)
        self.relation_name = relation_name
        self.relation_type = relation_type
        self.target_model = target_model

    def __str__(self) -> str:
        base_msg = f"关系 '{self.relation_name}' 序列化失败: {self.message}"
        if self.target_model:
            base_msg += f" (目标模型: {self.target_model})"
        relation_info = f" (关系类型: {self.relation_type})"
        return f"{base_msg}{relation_info}"


class FormatterError(SerializationError):
    """格式化器异常"""

    def __init__(self, message: str, formatter_name: str, format_type: str, **kwargs):
        super().__init__(message, **kwargs)
        self.formatter_name = formatter_name
        self.format_type = format_type

    def __str__(self) -> str:
        return (
            f"格式化器 '{self.formatter_name}' 错误: {self.message} "
            f"(格式: {self.format_type})"
        )


class DeserializationError(SerializationError):
    """反序列化异常"""

    def __init__(
        self,
        message: str,
        source_data: Any = None,
        target_model: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.source_data = source_data
        self.target_model = target_model

    def __str__(self) -> str:
        base_msg = f"反序列化失败: {self.message}"
        if self.target_model:
            base_msg += f" (目标模型: {self.target_model})"
        return base_msg


class AsyncSerializationError(SerializationError):
    """异步序列化异常"""

    def __init__(
        self,
        message: str,
        timeout: float | None = None,
        async_serializer: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.timeout = timeout
        self.async_serializer = async_serializer

    def __str__(self) -> str:
        base_msg = f"异步序列化失败: {self.message}"
        if self.async_serializer:
            base_msg += f" (序列化器: {self.async_serializer})"
        if self.timeout:
            base_msg += f" (超时: {self.timeout}s)"
        return base_msg


class CircularReferenceError(SerializationError):
    """循环引用异常"""

    def __init__(self, message: str, reference_path: list[str], **kwargs):
        super().__init__(message, **kwargs)
        self.reference_path = reference_path

    def __str__(self) -> str:
        path_str = " -> ".join(self.reference_path)
        return f"检测到循环引用: {self.message} (路径: {path_str})"


def convert_pydantic_serialization_error(
    error: PydanticValidationError, context: dict[str, Any] | None = None
) -> SerializationError:
    """将Pydantic序列化错误转换为FastORM序列化错误"""

    errors = []
    for err in error.errors():
        errors.append(
            {
                "type": err.get("type"),
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "input": err.get("input"),
                "ctx": err.get("ctx"),
            }
        )

    # 获取第一个错误的信息
    first_error = error.errors()[0] if error.errors() else {}
    field_path = first_error.get("loc", ())
    field_name = ".".join(str(loc) for loc in field_path) if field_path else None

    return SerializationError(
        message=f"Pydantic序列化错误: {error!s}",
        field=field_name,
        value=first_error.get("input"),
        errors=errors,
        context=context,
    )


def format_serialization_errors(
    errors: list[SerializationError], include_context: bool = True
) -> dict[str, Any]:
    """格式化序列化错误列表"""

    formatted_errors = []
    for error in errors:
        error_dict = {
            "type": error.__class__.__name__,
            "message": error.message,
            "field": error.field,
        }

        if hasattr(error, "serializer_name") and error.serializer_name:
            error_dict["serializer"] = error.serializer_name

        if hasattr(error, "relation_name") and error.relation_name:
            error_dict["relation"] = error.relation_name

        if hasattr(error, "formatter_name") and error.formatter_name:
            error_dict["formatter"] = error.formatter_name

        if include_context and error.context:
            error_dict["context"] = error.context

        formatted_errors.append(error_dict)

    return {
        "total_errors": len(errors),
        "error_summary": _get_error_summary(errors),
        "errors": formatted_errors,
    }


def _get_error_summary(errors: list[SerializationError]) -> dict[str, int]:
    """获取错误类型统计摘要"""

    summary = {}
    for error in errors:
        error_type = error.__class__.__name__
        summary[error_type] = summary.get(error_type, 0) + 1

    return summary
