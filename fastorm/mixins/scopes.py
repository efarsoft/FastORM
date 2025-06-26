"""
FastORM 查询作用域系统

实现Eloquent风格的查询作用域，让复杂查询可以复用。

示例:
```python
class User(Model):
    @scope
    def active(self, query):
        return query.where('status', 'active')
    
    @scope  
    def by_role(self, query, role):
        return query.where('role', role)
    
    @global_scope
    def tenant_scope(self, query):
        # 全局作用域自动应用
        return query.where('tenant_id', get_current_tenant())

# 使用方式
users = await User.active().by_role('admin').get()
```
"""

from __future__ import annotations

from typing import (
    Any, Callable, Dict, List, Optional, Type, TypeVar, TYPE_CHECKING
)
from functools import wraps

if TYPE_CHECKING:
    from fastorm.query.builder import QueryBuilder
    from fastorm.model.model import Model

T = TypeVar('T')


class ScopeRegistry:
    """作用域注册表 - 管理所有已注册的查询作用域"""
    
    def __init__(self):
        self._scopes: Dict[Type, Dict[str, Callable]] = {}
        self._global_scopes: Dict[Type, Dict[str, Callable]] = {}
    
    def register_scope(
        self, 
        model_class: Type, 
        scope_name: str, 
        scope_func: Callable
    ) -> None:
        """注册普通作用域"""
        if model_class not in self._scopes:
            self._scopes[model_class] = {}
        self._scopes[model_class][scope_name] = scope_func
    
    def register_global_scope(
        self, 
        model_class: Type, 
        scope_name: str, 
        scope_func: Callable
    ) -> None:
        """注册全局作用域"""
        if model_class not in self._global_scopes:
            self._global_scopes[model_class] = {}
        self._global_scopes[model_class][scope_name] = scope_func
    
    def get_scopes(self, model_class: Type) -> Dict[str, Callable]:
        """获取模型的所有普通作用域"""
        return self._scopes.get(model_class, {})
    
    def get_global_scopes(self, model_class: Type) -> Dict[str, Callable]:
        """获取模型的所有全局作用域"""
        return self._global_scopes.get(model_class, {})


# 全局作用域注册表实例
_scope_registry = ScopeRegistry()


def scope(func: Callable) -> Callable:
    """查询作用域装饰器
    
    将方法标记为查询作用域，可以在查询构建器中链式调用。
    
    Args:
        func: 作用域方法，第一个参数必须是query（QueryBuilder实例）
        
    Returns:
        装饰后的方法
        
    示例:
    ```python
    class User(Model):
        @scope
        def active(self, query):
            return query.where('status', 'active')
        
        @scope
        def by_email_domain(self, query, domain):
            return query.where('email', 'like', f'%@{domain}')
    
    # 使用
    users = await User.active().by_email_domain('gmail.com').get()
    ```
    """
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 实际的作用域逻辑在QueryBuilder中处理
        return func(self, *args, **kwargs)
    
    # 标记为作用域方法
    wrapper._is_scope = True
    wrapper._scope_name = func.__name__
    
    return wrapper


def global_scope(scope_name: Optional[str] = None):
    """全局作用域装饰器
    
    标记为全局作用域的方法会自动应用到该模型的所有查询。
    
    Args:
        scope_name: 作用域名称，如果不提供则使用方法名
        
    Returns:
        装饰器函数
        
    示例:
    ```python
    class User(Model):
        @global_scope('tenant_filter')
        def apply_tenant_filter(self, query):
            return query.where('tenant_id', get_current_tenant_id())
        
        @global_scope()  # 使用方法名作为作用域名
        def soft_delete_filter(self, query):
            return query.where('deleted_at', None)
    ```
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, query):
            return func(self, query)
        
        # 标记为全局作用域
        wrapper._is_global_scope = True
        wrapper._global_scope_name = scope_name or func.__name__
        
        return wrapper
    
    return decorator


class ScopeMixin:
    """作用域混入类
    
    为Model提供作用域支持功能。
    """
    
    def __init_subclass__(cls, **kwargs):
        """子类初始化时自动注册作用域"""
        super().__init_subclass__(**kwargs)
        
        # 扫描并注册作用域方法
        for attr_name in dir(cls):
            if attr_name.startswith('_'):
                continue
                
            attr = getattr(cls, attr_name)
            if not callable(attr):
                continue
            
            # 注册普通作用域
            if hasattr(attr, '_is_scope') and attr._is_scope:
                _scope_registry.register_scope(
                    cls, 
                    attr._scope_name, 
                    attr
                )
            
            # 注册全局作用域
            if (hasattr(attr, '_is_global_scope') and
                    attr._is_global_scope):
                _scope_registry.register_global_scope(
                    cls, 
                    attr._global_scope_name, 
                    attr
                )
    
    @classmethod
    def get_registered_scopes(cls) -> Dict[str, Callable]:
        """获取已注册的查询作用域"""
        return _scope_registry.get_scopes(cls)
    
    @classmethod
    def get_registered_global_scopes(cls) -> Dict[str, Callable]:
        """获取已注册的全局作用域"""
        return _scope_registry.get_global_scopes(cls)


class ScopedQueryBuilder:
    """作用域查询构建器
    
    扩展QueryBuilder以支持动态作用域方法调用。
    """
    
    def __init__(self, query_builder: 'QueryBuilder', model_class: Type):
        self._query_builder = query_builder
        self._model_class = model_class
        self._applied_global_scopes: List[str] = []
        
        # 自动应用全局作用域
        self._apply_global_scopes()
    
    def _apply_global_scopes(self) -> None:
        """自动应用全局作用域"""
        global_scopes = _scope_registry.get_global_scopes(self._model_class)
        
        for scope_name, scope_func in global_scopes.items():
            if scope_name not in self._applied_global_scopes:
                # 创建模型实例来调用作用域方法
                model_instance = self._model_class()
                self._query_builder = scope_func(
                    model_instance, self._query_builder
                )
                self._applied_global_scopes.append(scope_name)
    
    def without_global_scope(self, scope_name: str) -> 'ScopedQueryBuilder':
        """移除指定的全局作用域
        
        Args:
            scope_name: 要移除的全局作用域名称
            
        Returns:
            新的作用域查询构建器实例
            
        示例:
        ```python
        # 查询包含软删除的记录
        users = await User.without_global_scope('soft_delete_filter').get()
        ```
        """
        # 创建新的查询构建器，不应用指定的全局作用域
        new_builder = ScopedQueryBuilder(
            self._query_builder.__class__(self._model_class), 
            self._model_class
        )
        
        # 应用除了指定作用域之外的所有全局作用域
        global_scopes = _scope_registry.get_global_scopes(self._model_class)
        for name, scope_func in global_scopes.items():
            if name != scope_name:
                model_instance = self._model_class()
                new_builder._query_builder = scope_func(
                    model_instance, 
                    new_builder._query_builder
                )
                new_builder._applied_global_scopes.append(name)
        
        return new_builder
    
    def without_global_scopes(
        self, scope_names: List[str] = None
    ) -> 'ScopedQueryBuilder':
        """移除指定的多个全局作用域，如果不指定则移除所有
        
        Args:
            scope_names: 要移除的全局作用域名称列表，None表示移除全部
            
        Returns:
            新的作用域查询构建器实例
        """
        if scope_names is None:
            # 移除所有全局作用域
            return ScopedQueryBuilder(
                self._query_builder.__class__(self._model_class), 
                self._model_class
            )
        
        # 移除指定的作用域
        new_builder = ScopedQueryBuilder(
            self._query_builder.__class__(self._model_class), 
            self._model_class
        )
        
        global_scopes = _scope_registry.get_global_scopes(self._model_class)
        for name, scope_func in global_scopes.items():
            if name not in scope_names:
                model_instance = self._model_class()
                new_builder._query_builder = scope_func(
                    model_instance, 
                    new_builder._query_builder
                )
                new_builder._applied_global_scopes.append(name)
        
        return new_builder
    
    def __getattr__(self, name: str) -> Any:
        """动态处理作用域方法调用和QueryBuilder方法代理"""
        
        # 首先检查是否是注册的作用域
        scopes = _scope_registry.get_scopes(self._model_class)
        if name in scopes:
            scope_func = scopes[name]
            
            def scope_caller(*args, **kwargs):
                # 创建模型实例来调用作用域方法
                model_instance = self._model_class()
                
                # 调用作用域方法，传入query作为第一个参数
                result_builder = scope_func(
                    model_instance, 
                    self._query_builder, 
                    *args, 
                    **kwargs
                )
                
                # 返回新的作用域查询构建器
                new_scoped = ScopedQueryBuilder(
                    result_builder, self._model_class
                )
                new_scoped._applied_global_scopes = (
                    self._applied_global_scopes.copy()
                )
                return new_scoped
            
            return scope_caller
        
        # 如果不是作用域，代理到QueryBuilder
        attr = getattr(self._query_builder, name)
        
        if callable(attr):
            def method_proxy(*args, **kwargs):
                result = attr(*args, **kwargs)
                
                # 如果返回的是QueryBuilder，包装为ScopedQueryBuilder
                if hasattr(result, '_model_class'):
                    new_scoped = ScopedQueryBuilder(
                        result, self._model_class
                    )
                    new_scoped._applied_global_scopes = (
                        self._applied_global_scopes.copy()
                    )
                    return new_scoped
                
                # 否则直接返回结果（如get(), first()等的执行结果）
                return result
            
            return method_proxy
        
        return attr


def create_scoped_query(model_class: Type) -> ScopedQueryBuilder:
    """创建作用域查询构建器
    
    Args:
        model_class: 模型类
        
    Returns:
        作用域查询构建器实例
    """
    from fastorm.query.builder import QueryBuilder
    
    base_builder = QueryBuilder(model_class)
    return ScopedQueryBuilder(base_builder, model_class) 