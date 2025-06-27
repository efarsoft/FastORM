"""
FastORM 模型级验证器

基于Pydantic 2.11的模型级验证器系统，提供：
- 跨字段验证
- 业务规则验证
- 条件验证
- 模型状态验证
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .exceptions import ModelValidationError

logger = logging.getLogger(__name__)


@dataclass
class ModelValidatorConfig:
    """模型验证器配置"""

    name: str
    description: str
    error_message: str
    mode: str = "after"  # before, after
    priority: int = 0


class ModelValidatorRegistry:
    """模型验证器注册表

    管理所有模型级验证器的注册、查询和执行
    """

    def __init__(self):
        self._validators: dict[str, list[Callable]] = {}
        self._configs: dict[str, ModelValidatorConfig] = {}

    def register(
        self,
        model_name: str,
        validator_name: str,
        validator: Callable,
        description: str = "",
        error_message: str = "",
        mode: str = "after",
        priority: int = 0,
    ) -> None:
        """注册模型验证器

        Args:
            model_name: 模型名称
            validator_name: 验证器名称
            validator: 验证器函数
            description: 描述
            error_message: 错误消息
            mode: 验证模式 (before/after)
            priority: 优先级
        """
        if model_name not in self._validators:
            self._validators[model_name] = []

        config = ModelValidatorConfig(
            name=validator_name,
            description=description,
            error_message=error_message or f"Model validation failed: {validator_name}",
            mode=mode,
            priority=priority,
        )

        # 按优先级插入
        validator_entry = (validator, config)
        self._validators[model_name].append(validator_entry)
        self._validators[model_name].sort(key=lambda x: x[1].priority)

        config_key = f"{model_name}:{validator_name}"
        self._configs[config_key] = config

        logger.debug(
            f"Registered model validator '{validator_name}' for model '{model_name}'"
        )

    def get_validators(self, model_name: str) -> list[tuple]:
        """获取模型的所有验证器"""
        return self._validators.get(model_name, [])

    def get_config(
        self, model_name: str, validator_name: str
    ) -> ModelValidatorConfig | None:
        """获取验证器配置"""
        config_key = f"{model_name}:{validator_name}"
        return self._configs.get(config_key)

    def list_models(self) -> list[str]:
        """列出所有有验证器的模型"""
        return list(self._validators.keys())


# 全局模型验证器注册表
_model_validator_registry = ModelValidatorRegistry()


def register_model_validator(
    model_name: str,
    validator_name: str,
    description: str = "",
    error_message: str = "",
    mode: str = "after",
    priority: int = 0,
):
    """模型验证器装饰器

    Args:
        model_name: 模型名称
        validator_name: 验证器名称
        description: 描述
        error_message: 错误消息
        mode: 验证模式
        priority: 优先级
    """

    def decorator(func: Callable) -> Callable:
        _model_validator_registry.register(
            model_name=model_name,
            validator_name=validator_name,
            validator=func,
            description=description,
            error_message=error_message,
            mode=mode,
            priority=priority,
        )
        return func

    return decorator


def get_model_validator_registry() -> ModelValidatorRegistry:
    """获取模型验证器注册表"""
    return _model_validator_registry


# =============================================================================
# 内置模型验证器
# =============================================================================


def validate_required_fields(*required_fields: str):
    """必填字段验证器工厂"""

    def validator(cls, values: dict[str, Any]) -> dict[str, Any]:
        """验证必填字段"""
        missing_fields = []

        for field_name in required_fields:
            value = values.get(field_name)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_fields.append(field_name)

        if missing_fields:
            raise ModelValidationError(
                model_name=cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                message=f"Missing required fields: {', '.join(missing_fields)}",
                context={"missing_fields": missing_fields},
            )

        return values

    return validator


def validate_mutually_exclusive(*field_groups: list[str]):
    """互斥字段验证器工厂"""

    def validator(cls, values: dict[str, Any]) -> dict[str, Any]:
        """验证互斥字段"""
        for group in field_groups:
            filled_fields = []
            for field_name in group:
                value = values.get(field_name)
                if value is not None and value != "":
                    filled_fields.append(field_name)

            if len(filled_fields) > 1:
                raise ModelValidationError(
                    model_name=cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                    message=f"Fields {group} are mutually exclusive, but {filled_fields} are all set",
                    context={
                        "mutually_exclusive_group": group,
                        "conflicting_fields": filled_fields,
                    },
                )

        return values

    return validator


def validate_conditional_required(condition_field: str, required_fields: list[str]):
    """条件必填验证器工厂"""

    def validator(cls, values: dict[str, Any]) -> dict[str, Any]:
        """验证条件必填"""
        condition_value = values.get(condition_field)

        # 如果条件字段有值，检查必填字段
        if condition_value is not None and condition_value != "":
            missing_fields = []

            for field_name in required_fields:
                value = values.get(field_name)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing_fields.append(field_name)

            if missing_fields:
                raise ModelValidationError(
                    model_name=cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                    message=(
                        f"When '{condition_field}' is set, "
                        f"the following fields are required: {', '.join(missing_fields)}"
                    ),
                    context={
                        "condition_field": condition_field,
                        "condition_value": condition_value,
                        "missing_required_fields": missing_fields,
                    },
                )

        return values

    return validator


def validate_field_comparison(field1: str, field2: str, comparison: str = "equal"):
    """字段比较验证器工厂"""

    def validator(cls, values: dict[str, Any]) -> dict[str, Any]:
        """验证字段比较"""
        value1 = values.get(field1)
        value2 = values.get(field2)

        # 如果任一字段为空，跳过验证
        if value1 is None or value2 is None:
            return values

        valid = False
        error_message = ""

        try:
            if comparison == "equal":
                valid = value1 == value2
                error_message = f"Field '{field1}' must equal '{field2}'"
            elif comparison == "not_equal":
                valid = value1 != value2
                error_message = f"Field '{field1}' must not equal '{field2}'"
            elif comparison == "greater":
                valid = value1 > value2
                error_message = f"Field '{field1}' must be greater than '{field2}'"
            elif comparison == "less":
                valid = value1 < value2
                error_message = f"Field '{field1}' must be less than '{field2}'"
            elif comparison == "greater_equal":
                valid = value1 >= value2
                error_message = (
                    f"Field '{field1}' must be greater than or equal to '{field2}'"
                )
            elif comparison == "less_equal":
                valid = value1 <= value2
                error_message = (
                    f"Field '{field1}' must be less than or equal to '{field2}'"
                )
            else:
                raise ValueError(f"Unknown comparison type: {comparison}")

            if not valid:
                raise ModelValidationError(
                    model_name=cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                    message=error_message,
                    context={
                        "field1": field1,
                        "field2": field2,
                        "value1": value1,
                        "value2": value2,
                        "comparison": comparison,
                    },
                )

        except (TypeError, ValueError) as e:
            raise ModelValidationError(
                model_name=cls.__name__ if hasattr(cls, "__name__") else "Unknown",
                message=f"Cannot compare fields '{field1}' and '{field2}': {e!s}",
                context={
                    "field1": field1,
                    "field2": field2,
                    "value1": value1,
                    "value2": value2,
                    "comparison": comparison,
                    "error": str(e),
                },
            )

        return values

    return validator


# =============================================================================
# 验证器组合器
# =============================================================================


class ModelValidatorChain:
    """模型验证器链"""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.validators: list[Callable] = []

    def add_validator(self, validator: Callable) -> "ModelValidatorChain":
        """添加验证器"""
        self.validators.append(validator)
        return self

    def add_required_fields(self, *fields: str) -> "ModelValidatorChain":
        """添加必填字段验证"""
        return self.add_validator(validate_required_fields(*fields))

    def add_mutually_exclusive(self, *field_groups: list[str]) -> "ModelValidatorChain":
        """添加互斥字段验证"""
        return self.add_validator(validate_mutually_exclusive(*field_groups))

    def add_conditional_required(
        self, condition_field: str, required_fields: list[str]
    ) -> "ModelValidatorChain":
        """添加条件必填验证"""
        return self.add_validator(
            validate_conditional_required(condition_field, required_fields)
        )

    def add_field_comparison(
        self, field1: str, field2: str, comparison: str = "equal"
    ) -> "ModelValidatorChain":
        """添加字段比较验证"""
        return self.add_validator(validate_field_comparison(field1, field2, comparison))

    def validate(self, cls: type, values: dict[str, Any]) -> dict[str, Any]:
        """执行验证链"""
        for validator in self.validators:
            values = validator(cls, values)
        return values


def create_model_validator_chain(model_name: str) -> ModelValidatorChain:
    """创建模型验证器链"""
    return ModelValidatorChain(model_name)
