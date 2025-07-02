"""
FastORM SQL注入检查机制

提供SQL注入风险的检测、预防和监控功能。
确保"现代如FastAPI"的安全标准。
"""

from __future__ import annotations

import ast
import re
from typing import Any, Callable, TypeVar, cast
from functools import wraps
import logging

from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause

logger = logging.getLogger("fastorm.security")

F = TypeVar("F", bound=Callable[..., Any])


class SQLInjectionError(Exception):
    """SQL注入风险错误"""
    pass


class SecurityWarning(UserWarning):
    """安全警告"""
    pass


def validate_sql_text(sql: str, allow_parameters: bool = True) -> None:
    """验证SQL文本的安全性
    
    Args:
        sql: SQL字符串
        allow_parameters: 是否允许参数占位符
        
    Raises:
        SQLInjectionError: 发现潜在的SQL注入风险
    """
    # 检查危险的SQL注入模式
    dangerous_patterns = [
        r"['\"].*[\+\s]*['\"]",  # 字符串拼接
        r"f['\"].*\{.*\}.*['\"]",  # f-string格式化
        r"['\"].*%s.*['\"]",  # 字符串格式化
        r"['\"].*\.format\(.*\).*['\"]",  # .format()格式化
        r"exec\s*\(",  # 动态执行
        r"eval\s*\(",  # 动态求值
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            raise SQLInjectionError(
                f"检测到潜在的SQL注入风险: {pattern} "
                f"在SQL: {sql[:100]}..."
            )
    
    # 检查是否有未绑定的变量
    if not allow_parameters:
        # 查找所有占位符
        placeholders = re.findall(r':\w+', sql)
        if placeholders:
            logger.warning(
                f"SQL文本包含参数占位符但不允许参数: {placeholders}"
            )


def safe_text(sql: str, parameters: dict[str, Any] | None = None) -> TextClause:
    """安全的text()包装器
    
    Args:
        sql: SQL字符串
        parameters: 参数字典
        
    Returns:
        安全的TextClause对象
        
    Raises:
        SQLInjectionError: 发现SQL注入风险
    """
    # 验证SQL安全性
    validate_sql_text(sql, allow_parameters=parameters is not None)
    
    # 记录SQL使用情况（用于安全审计）
    logger.debug(f"Safe SQL execution: {sql[:100]}...")
    
    if parameters:
        return text(sql).bindparam(**parameters)
    else:
        return text(sql)


def require_safe_sql(func: F) -> F:
    """装饰器：要求函数中的SQL操作必须安全
    
    用于装饰可能包含SQL操作的函数，确保其安全性。
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 记录进入安全检查模式
        logger.debug(f"进入安全SQL检查模式: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"安全SQL检查通过: {func.__name__}")
            return result
        except SQLInjectionError:
            logger.error(f"SQL注入风险被阻止: {func.__name__}")
            raise
        except Exception as e:
            logger.error(f"安全SQL检查中发生错误: {func.__name__}: {e}")
            raise
    
    return cast(F, wrapper)


class SQLSecurityAuditor:
    """SQL安全审计器
    
    监控和记录所有SQL操作，检测潜在的安全风险。
    """
    
    def __init__(self):
        self.sql_operations: list[dict[str, Any]] = []
        self.security_warnings: list[dict[str, Any]] = []
        self.injection_attempts: list[dict[str, Any]] = []
    
    def log_sql_operation(
        self, 
        sql: str, 
        parameters: dict[str, Any] | None = None,
        operation_type: str = "unknown",
        source: str = "unknown"
    ) -> None:
        """记录SQL操作
        
        Args:
            sql: SQL字符串
            parameters: 参数
            operation_type: 操作类型
            source: 来源
        """
        operation = {
            "timestamp": __import__("time").time(),
            "sql": sql,
            "parameters": parameters,
            "operation_type": operation_type,
            "source": source,
            "sql_length": len(sql),
            "has_parameters": parameters is not None,
        }
        
        self.sql_operations.append(operation)
        
        # 检查潜在的安全问题
        try:
            validate_sql_text(sql, allow_parameters=parameters is not None)
        except SQLInjectionError as e:
            self.injection_attempts.append({
                "timestamp": operation["timestamp"],
                "error": str(e),
                "sql": sql,
                "source": source,
            })
            logger.warning(f"记录到SQL注入尝试: {e}")
    
    def get_security_report(self) -> dict[str, Any]:
        """获取安全报告
        
        Returns:
            包含安全统计信息的字典
        """
        total_operations = len(self.sql_operations)
        parameterized_operations = sum(
            1 for op in self.sql_operations if op["has_parameters"]
        )
        
        return {
            "total_sql_operations": total_operations,
            "parameterized_operations": parameterized_operations,
            "parameterization_rate": (
                parameterized_operations / total_operations * 100
                if total_operations > 0 else 0
            ),
            "security_warnings": len(self.security_warnings),
            "injection_attempts": len(self.injection_attempts),
            "recent_injection_attempts": self.injection_attempts[-10:],
        }


# 全局安全审计器实例
_security_auditor = SQLSecurityAuditor()


def get_security_auditor() -> SQLSecurityAuditor:
    """获取全局安全审计器实例"""
    return _security_auditor


def check_source_code_security(source_path: str) -> dict[str, Any]:
    """检查源代码中的SQL安全问题
    
    Args:
        source_path: 源代码文件路径
        
    Returns:
        包含安全检查结果的字典
    """
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        return {"error": f"无法读取文件: {e}"}
    
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"语法错误: {e}"}
    
    issues = []
    
    class SecurityVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            # 检查text()调用
            if (isinstance(node.func, ast.Name) and 
                node.func.id == "text" and 
                node.args):
                
                first_arg = node.args[0]
                
                # 检查f-string
                if isinstance(first_arg, ast.JoinedStr):
                    issues.append({
                        "type": "sql_injection_risk",
                        "line": node.lineno,
                        "message": "使用f-string进行SQL拼接存在注入风险",
                        "severity": "high"
                    })
                
                # 检查字符串格式化
                elif (isinstance(first_arg, ast.Call) and
                      isinstance(first_arg.func, ast.Attribute) and
                      first_arg.func.attr == "format"):
                    issues.append({
                        "type": "sql_injection_risk", 
                        "line": node.lineno,
                        "message": "使用.format()进行SQL拼接存在注入风险",
                        "severity": "high"
                    })
            
            self.generic_visit(node)
    
    visitor = SecurityVisitor()
    visitor.visit(tree)
    
    return {
        "file": source_path,
        "issues_found": len(issues),
        "issues": issues,
        "status": "safe" if not issues else "has_risks"
    } 