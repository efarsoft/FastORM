"""
FastORM 验证规则

提供可复用的验证规则定义和管理系统
"""

from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """验证规则定义"""
    name: str
    description: str
    rule_func: Callable[[Any], bool]
    error_message: str
    parameters: Optional[Dict[str, Any]] = None
    
    def validate(self, value: Any) -> bool:
        """执行验证规则"""
        try:
            return self.rule_func(value)
        except Exception as e:
            logger.error(f"Error executing validation rule '{self.name}': {e}")
            return False
    
    def get_error_message(self, value: Any = None) -> str:
        """获取错误消息"""
        if self.parameters and "{" in self.error_message:
            try:
                return self.error_message.format(**self.parameters, value=value)
            except (KeyError, ValueError):
                pass
        return self.error_message


class ValidationRuleRegistry:
    """验证规则注册表"""
    
    def __init__(self):
        self._rules: Dict[str, ValidationRule] = {}
    
    def register(self, rule: ValidationRule) -> None:
        """注册验证规则"""
        self._rules[rule.name] = rule
        logger.debug(f"Registered validation rule: {rule.name}")
    
    def get_rule(self, name: str) -> Optional[ValidationRule]:
        """获取验证规则"""
        return self._rules.get(name)
    
    def list_rules(self) -> List[str]:
        """列出所有规则名称"""
        return list(self._rules.keys())
    
    def validate(self, rule_name: str, value: Any) -> bool:
        """使用规则验证值"""
        rule = self.get_rule(rule_name)
        if rule:
            return rule.validate(value)
        return False


# 全局规则注册表
_rule_registry = ValidationRuleRegistry()


def create_validation_rule(
    name: str,
    rule_func: Callable[[Any], bool],
    description: str = "",
    error_message: str = "",
    parameters: Optional[Dict[str, Any]] = None
) -> ValidationRule:
    """创建验证规则"""
    rule = ValidationRule(
        name=name,
        description=description,
        rule_func=rule_func,
        error_message=error_message or f"Validation rule '{name}' failed",
        parameters=parameters
    )
    _rule_registry.register(rule)
    return rule


def get_validation_rule_registry() -> ValidationRuleRegistry:
    """获取验证规则注册表"""
    return _rule_registry


# =============================================================================
# 内置验证规则
# =============================================================================

# 字符串验证规则
create_validation_rule(
    name="not_empty",
    rule_func=lambda x: x is not None and str(x).strip() != "",
    description="验证值不为空",
    error_message="Value cannot be empty"
)

create_validation_rule(
    name="is_string",
    rule_func=lambda x: isinstance(x, str),
    description="验证值是字符串",
    error_message="Value must be a string"
)

create_validation_rule(
    name="is_numeric",
    rule_func=lambda x: isinstance(x, (int, float)),
    description="验证值是数字",
    error_message="Value must be numeric"
)

create_validation_rule(
    name="is_positive",
    rule_func=lambda x: isinstance(x, (int, float)) and x > 0,
    description="验证值是正数",
    error_message="Value must be positive"
)

create_validation_rule(
    name="is_non_negative",
    rule_func=lambda x: isinstance(x, (int, float)) and x >= 0,
    description="验证值是非负数",
    error_message="Value must be non-negative"
)


def create_length_rule(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> ValidationRule:
    """创建长度验证规则"""
    def rule_func(value: Any) -> bool:
        if not hasattr(value, '__len__'):
            return False
        
        length = len(value)
        
        if min_length is not None and length < min_length:
            return False
        
        if max_length is not None and length > max_length:
            return False
        
        return True
    
    # 构建错误消息
    if min_length is not None and max_length is not None:
        error_msg = f"Length must be between {min_length} and {max_length}"
    elif min_length is not None:
        error_msg = f"Length must be at least {min_length}"
    elif max_length is not None:
        error_msg = f"Length must be at most {max_length}"
    else:
        error_msg = "Invalid length"
    
    rule_name = f"length_{min_length or 'any'}_{max_length or 'any'}"
    
    return create_validation_rule(
        name=rule_name,
        rule_func=rule_func,
        description=f"验证长度范围: {min_length}-{max_length}",
        error_message=error_msg,
        parameters={"min_length": min_length, "max_length": max_length}
    )


def create_range_rule(
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None
) -> ValidationRule:
    """创建数值范围验证规则"""
    def rule_func(value: Any) -> bool:
        if not isinstance(value, (int, float)):
            return False
        
        if min_value is not None and value < min_value:
            return False
        
        if max_value is not None and value > max_value:
            return False
        
        return True
    
    # 构建错误消息
    if min_value is not None and max_value is not None:
        error_msg = f"Value must be between {min_value} and {max_value}"
    elif min_value is not None:
        error_msg = f"Value must be at least {min_value}"
    elif max_value is not None:
        error_msg = f"Value must be at most {max_value}"
    else:
        error_msg = "Invalid value range"
    
    rule_name = f"range_{min_value or 'any'}_{max_value or 'any'}"
    
    return create_validation_rule(
        name=rule_name,
        rule_func=rule_func,
        description=f"验证数值范围: {min_value}-{max_value}",
        error_message=error_msg,
        parameters={"min_value": min_value, "max_value": max_value}
    )


class RuleChain:
    """规则链
    
    允许组合多个验证规则
    """
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
    
    def add_rule(self, rule: ValidationRule) -> 'RuleChain':
        """添加规则"""
        self.rules.append(rule)
        return self
    
    def add_rule_by_name(self, rule_name: str) -> 'RuleChain':
        """通过名称添加规则"""
        rule = _rule_registry.get_rule(rule_name)
        if rule:
            self.rules.append(rule)
        return self
    
    def validate(self, value: Any) -> tuple[bool, List[str]]:
        """验证值，返回是否通过和错误消息列表"""
        errors = []
        
        for rule in self.rules:
            if not rule.validate(value):
                errors.append(rule.get_error_message(value))
        
        return len(errors) == 0, errors
    
    def validate_strict(self, value: Any) -> bool:
        """严格验证，任何规则失败都返回False"""
        for rule in self.rules:
            if not rule.validate(value):
                return False
        return True


def create_rule_chain() -> RuleChain:
    """创建规则链"""
    return RuleChain()
