"""
FastORM Attributes Mixin

参照ThinkORM 4设计的属性处理混入类
提供获取器、修改器、类型转换等功能
"""

from typing import Any, Dict, Optional, Callable
from datetime import datetime
from decimal import Decimal


class AttributesMixin:
    """
    属性处理混入类
    
    提供类似ThinkORM的获取器(getter)和修改器(setter)功能
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attributes = {}
        self._original = {}
        self._changes = {}
        self._casts = {}
        
    def get_attribute(self, key: str) -> Any:
        """
        获取属性值，支持获取器
        
        Args:
            key: 属性名
            
        Returns:
            属性值
        """
        # 只查找类方法，避免递归
        getter_method = f"get_{key}_attribute"
        method = getattr(type(self), getter_method, None)
        if callable(method):
            raw_value = self._attributes.get(key)
            return method(self, raw_value)
        
        # 检查是否需要类型转换
        if key in self._casts:
            raw_value = self._attributes.get(key)
            return self._cast_attribute(key, raw_value)
            
        return self._attributes.get(key)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """
        设置属性值，支持修改器
        
        Args:
            key: 属性名
            value: 属性值
        """
        # 先尝试修改器方法
        setter_method = f"set_{key}_attribute"
        if hasattr(self, setter_method):
            value = getattr(self, setter_method)(value)
        
        # 记录变更
        if key in self._attributes:
            old_value = self._attributes[key]
            if old_value != value:
                self._changes[key] = value
        else:
            self._changes[key] = value
            
        self._attributes[key] = value
    
    def _cast_attribute(self, key: str, value: Any) -> Any:
        """
        类型转换
        
        Args:
            key: 属性名
            value: 原始值
            
        Returns:
            转换后的值
        """
        if value is None:
            return None
            
        cast_type = self._casts.get(key, 'string')
        
        if cast_type == 'int' or cast_type == 'integer':
            return int(value) if value is not None else None
        elif cast_type == 'float':
            return float(value) if value is not None else None
        elif cast_type == 'decimal':
            return Decimal(str(value)) if value is not None else None
        elif cast_type == 'string':
            return str(value) if value is not None else None
        elif cast_type == 'bool' or cast_type == 'boolean':
            if isinstance(value, str):
                return value.lower() in ('1', 'true', 'yes', 'on')
            return bool(value)
        elif cast_type == 'datetime':
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value
        elif cast_type == 'json':
            import json
            if isinstance(value, str):
                return json.loads(value)
            return value
        elif cast_type == 'array':
            if isinstance(value, str):
                import json
                return json.loads(value)
            return list(value) if value is not None else []
        
        return value
    
    def set_casts(self, casts: Dict[str, str]) -> None:
        """
        设置类型转换规则
        
        Args:
            casts: 类型转换字典
        """
        self._casts.update(casts)
    
    def get_dirty(self) -> Dict[str, Any]:
        """
        获取已修改的属性
        
        Returns:
            修改的属性字典
        """
        return self._changes.copy()
    
    def is_dirty(self, key: Optional[str] = None) -> bool:
        """
        检查是否有修改
        
        Args:
            key: 可选的属性名
            
        Returns:
            是否有修改
        """
        if key:
            return key in self._changes
        return len(self._changes) > 0
    
    def get_original(self, key: Optional[str] = None) -> Any:
        """
        获取原始值
        
        Args:
            key: 可选的属性名
            
        Returns:
            原始值
        """
        if key:
            return self._original.get(key)
        return self._original.copy()
    
    def sync_original(self) -> None:
        """
        同步原始值（保存后调用）
        """
        self._original = self._attributes.copy()
        self._changes.clear()
    
    def fill(self, attributes: Dict[str, Any]) -> None:
        """
        批量填充属性
        
        Args:
            attributes: 属性字典
        """
        for key, value in attributes.items():
            self.set_attribute(key, value)
    
    def only(self, *keys) -> Dict[str, Any]:
        """
        只获取指定属性
        
        Args:
            keys: 属性名列表
            
        Returns:
            指定属性字典
        """
        return {key: self.get_attribute(key) for key in keys if key in self._attributes}
    
    def except_attr(self, *keys) -> Dict[str, Any]:
        """
        获取除指定属性外的所有属性
        
        Args:
            keys: 要排除的属性名列表
            
        Returns:
            属性字典
        """
        return {key: self.get_attribute(key) for key in self._attributes.keys() if key not in keys}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            属性字典
        """
        return {key: self.get_attribute(key) for key in self._attributes.keys()}
    
    def __getattr__(self, name: str) -> Any:
        """
        魔术方法：获取属性
        """
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        # 只查找实例属性和属性字典，避免递归
        if name in self.__dict__:
            return self.__dict__[name]
        if name in self._attributes:
            return self.get_attribute(name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        魔术方法：设置属性
        """
        # 私有属性直接设置
        if name.startswith('_') or name in ('table_name', 'primary_key', 'fillable', 'guarded'):
            super().__setattr__(name, value)
            return
        
        # 如果已经初始化，使用属性设置方法
        if hasattr(self, '_attributes'):
            self.set_attribute(name, value)
        else:
            super().__setattr__(name, value)
    
    def __getitem__(self, key: str) -> Any:
        """
        字典风格访问
        """
        return self.get_attribute(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """
        字典风格设置
        """
        self.set_attribute(key, value)
    
    def __contains__(self, key: str) -> bool:
        """
        检查属性是否存在
        """
        return key in self._attributes


class CastingMixin:
    """
    类型转换混入类
    """
    
    # 常用的类型转换规则
    CAST_TYPES = {
        'int': int,
        'integer': int,
        'float': float,
        'string': str,
        'bool': bool,
        'boolean': bool,
        'decimal': Decimal,
        'datetime': datetime,
        'json': dict,
        'array': list,
    }
    
    def cast_as(self, cast_type: str):
        """
        声明式类型转换装饰器
        
        Args:
            cast_type: 类型名称
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            field_name = func.__name__.replace('get_', '').replace('_attribute', '')
            if not hasattr(self, '_casts'):
                self._casts = {}
            self._casts[field_name] = cast_type
            return func
        return decorator


def accessor(func: Callable) -> Callable:
    """
    获取器装饰器
    
    将方法标记为属性获取器
    """
    func._is_accessor = True
    return func


def mutator(func: Callable) -> Callable:
    """
    修改器装饰器
    
    将方法标记为属性修改器
    """
    func._is_mutator = True
    return func


# 示例用法
"""
from fastorm.mixins.attributes import AttributesMixin, accessor, mutator

class User(Model, AttributesMixin):
    # 类型转换定义
    _casts = {
        'age': 'int',
        'salary': 'decimal',
        'settings': 'json',
        'is_active': 'bool',
        'created_at': 'datetime'
    }
    
    @accessor
    def get_full_name_attribute(self, value):
        '''全名获取器'''
        return f"{self.first_name} {self.last_name}"
    
    @mutator  
    def set_full_name_attribute(self, value):
        '''全名修改器'''
        if value:
            parts = value.split(' ', 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ''
        return value
    
    @accessor
    def get_age_display_attribute(self, value):
        '''年龄显示获取器'''
        age = self.age
        if age is None:
            return "未知"
        return f"{age}岁"

# 使用示例
user = User()
user.first_name = "张"
user.last_name = "三"
user.age = "25"  # 自动转换为int

print(user.full_name)        # "张 三" (获取器)
print(user.age_display)      # "25岁" (获取器)
print(type(user.age))        # <class 'int'> (类型转换)

user.full_name = "李 四"      # 修改器自动拆分
print(user.first_name)       # "李"
print(user.last_name)        # "四"
""" 