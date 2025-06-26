"""
FastORM 模型事件系统

支持ThinkORM风格的before/after事件处理。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import inspect

# =================================================================
# ThinkORM风格事件名称定义
# =================================================================

# 查询事件
AFTER_READ = "after_read"

# 写入事件
BEFORE_INSERT = "before_insert"
AFTER_INSERT = "after_insert"
BEFORE_UPDATE = "before_update" 
AFTER_UPDATE = "after_update"
BEFORE_WRITE = "before_write"
AFTER_WRITE = "after_write"

# 删除事件
BEFORE_DELETE = "before_delete"
AFTER_DELETE = "after_delete"

# 恢复事件（软删除相关）
BEFORE_RESTORE = "before_restore"
AFTER_RESTORE = "after_restore"

# 所有支持的事件
ALL_EVENTS = [
    AFTER_READ,
    BEFORE_INSERT, AFTER_INSERT,
    BEFORE_UPDATE, AFTER_UPDATE, 
    BEFORE_WRITE, AFTER_WRITE,
    BEFORE_DELETE, AFTER_DELETE,
    BEFORE_RESTORE, AFTER_RESTORE,
]


class EventHandler:
    """事件处理器"""
    
    def __init__(
        self,
        handler: Callable,
        priority: int = 0,
        condition: Optional[Callable] = None
    ):
        self.handler = handler
        self.priority = priority
        self.condition = condition
        self.is_async = inspect.iscoroutinefunction(handler)


class EventMixin:
    """模型事件混入类
    
    提供ThinkORM风格的模型事件支持。
    
    支持的事件：
    - after_read: 查询后
    - before_insert: 新增前  
    - after_insert: 新增后
    - before_update: 更新前
    - after_update: 更新后
    - before_write: 写入前
    - after_write: 写入后
    - before_delete: 删除前
    - after_delete: 删除后
    - before_restore: 恢复前
    - after_restore: 恢复后
    
    示例:
    ```python
    class User(Model, EventMixin):
        def on_before_insert(self):
            self.created_at = datetime.now(timezone.utc)
            
        def on_after_insert(self):
            print(f"用户 {self.name} 创建成功")
    ```
    """
    
    _event_handlers: Dict[str, List[EventHandler]] = {}
    
    def __init__(self, *args, **kwargs):
        """初始化事件混入，设置实例级状态管理"""
        super().__init__(*args, **kwargs)
        # 实例级状态管理，避免类属性共享问题
        self._model_state: Dict[str, Any] = {}
        self._original_state_saved = False
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # 为每个子类初始化独立的事件处理器
        cls._event_handlers = {}
        for event in ALL_EVENTS:
            cls._event_handlers[event] = []
        
        # 自动注册类方法作为事件处理器
        cls._register_class_handlers()
    
    @classmethod
    def _register_class_handlers(cls):
        """自动注册类方法作为事件处理器"""
        for name in dir(cls):
            if name.startswith('on_'):
                # 提取事件名称：on_before_insert -> before_insert
                event_name = name[3:]  # 去掉 'on_' 前缀
                
                if event_name in ALL_EVENTS:
                    handler = getattr(cls, name)
                    if callable(handler):
                        cls.add_event_handler(event_name, handler)
    
    @classmethod
    def add_event_handler(
        cls,
        event: str,
        handler: Callable,
        priority: int = 0,
        condition: Optional[Callable] = None
    ):
        """添加事件处理器
        
        Args:
            event: 事件名称
            handler: 处理器函数
            priority: 优先级（数字越大优先级越高）
            condition: 条件函数（返回True时才执行处理器）
        """
        if event not in ALL_EVENTS:
            raise ValueError(f"不支持的事件: {event}")
        
        event_handler = EventHandler(handler, priority, condition)
        cls._event_handlers[event].append(event_handler)
        
        # 按优先级排序
        cls._event_handlers[event].sort(
            key=lambda h: h.priority, 
            reverse=True
        )
    
    @classmethod
    def remove_event_handler(cls, event: str, handler: Callable):
        """移除事件处理器"""
        if event in cls._event_handlers:
            cls._event_handlers[event] = [
                h for h in cls._event_handlers[event] 
                if h.handler != handler
            ]
    
    async def fire_event(self, event: str, **kwargs):
        """触发事件
        
        Args:
            event: 事件名称
            **kwargs: 传递给处理器的参数
        """
        if event not in self._event_handlers:
            return
        
        for event_handler in self._event_handlers[event]:
            # 检查条件
            if event_handler.condition:
                if not event_handler.condition(self):
                    continue
            
            try:
                if event_handler.is_async:
                    await event_handler.handler(self, **kwargs)
                else:
                    event_handler.handler(self, **kwargs)
            except Exception as e:
                # 提供更详细的错误信息
                handler_name = getattr(
                    event_handler.handler, 
                    '__name__', 
                    str(event_handler.handler)
                )
                error_msg = (
                    f"事件处理器执行失败 [{event}:{handler_name}]: {e}"
                )
                print(f"⚠️ {error_msg}")
                
                # 对于关键事件，可以选择重新抛出异常
                critical_events = (
                    'before_insert', 'before_update', 'before_delete'
                )
                if event in critical_events:
                    # 验证类事件失败应该中断操作
                    is_validator = (
                        'validate' in handler_name.lower() or 
                        'check' in handler_name.lower()
                    )
                    if is_validator:
                        raise RuntimeError(error_msg) from e
    
    # =================================================================
    # 模型状态管理
    # =================================================================
    
    def _save_original_state(self):
        """保存原始状态"""
        # 确保_original_state_saved属性存在
        if not hasattr(self, '_original_state_saved'):
            self._original_state_saved = False
        
        # 确保_model_state属性存在
        if not hasattr(self, '_model_state'):
            self._model_state = {}
        
        if hasattr(self, '__table__') and not self._original_state_saved:
            # 只有在尚未保存状态时才保存
            for column in self.__table__.columns:
                self._model_state[column.name] = getattr(
                    self, column.name, None
                )
            self._original_state_saved = True
    
    def _reset_original_state(self):
        """重置原始状态，为下次保存做准备"""
        if hasattr(self, '_original_state_saved'):
            self._original_state_saved = False
        # 保存当前状态作为新的原始状态
        if hasattr(self, '__table__'):
            if not hasattr(self, '_model_state'):
                self._model_state = {}
            for column in self.__table__.columns:
                self._model_state[column.name] = getattr(
                    self, column.name, None
                )
    
    def get_original_value(self, field: str) -> Any:
        """获取字段的原始值"""
        if not hasattr(self, '_model_state'):
            self._model_state = {}
        return self._model_state.get(field)
    
    def is_dirty(self, field: Optional[str] = None) -> bool:
        """检查字段是否被修改
        
        Args:
            field: 字段名，None表示检查所有字段
            
        Returns:
            True如果字段被修改
        """
        if not hasattr(self, '__table__'):
            return False
        
        if not hasattr(self, '_model_state'):
            self._model_state = {}
        
        if field:
            current_value = getattr(self, field, None)
            original_value = self._model_state.get(field)
            return current_value != original_value
        else:
            # 检查所有字段
            for column in self.__table__.columns:
                if self.is_dirty(column.name):
                    return True
            return False
    
    def get_dirty_fields(self) -> Dict[str, Any]:
        """获取所有被修改的字段"""
        dirty_fields = {}
        
        if not hasattr(self, '_model_state'):
            self._model_state = {}
        
        if hasattr(self, '__table__'):
            for column in self.__table__.columns:
                if self.is_dirty(column.name):
                    dirty_fields[column.name] = getattr(self, column.name)
        
        return dirty_fields
    
    def is_new_record(self) -> bool:
        """检查是否为新记录"""
        # 假设主键字段名为 'id'
        pk_value = getattr(self, 'id', None)
        return pk_value is None
    
    # =================================================================
    # 便捷的事件处理器装饰器
    # =================================================================
    
    @classmethod
    def on_event(
        cls, 
        event: str, 
        priority: int = 0,
        condition: Optional[Callable] = None
    ):
        """事件处理器装饰器
        
        Example:
        ```python
        @User.on_event('before_insert')
        def validate_user(user):
            if not user.email:
                raise ValueError("邮箱不能为空")
        ```
        """
        def decorator(handler):
            cls.add_event_handler(event, handler, priority, condition)
            return handler
        return decorator


# =================================================================
# 便捷装饰器
# =================================================================

def before_insert(priority: int = 0, condition: Optional[Callable] = None):
    """新增前事件装饰器"""
    def decorator(func):
        func._event = BEFORE_INSERT
        func._priority = priority
        func._condition = condition
        return func
    return decorator


def after_insert(priority: int = 0, condition: Optional[Callable] = None):
    """新增后事件装饰器"""
    def decorator(func):
        func._event = AFTER_INSERT
        func._priority = priority
        func._condition = condition
        return func
    return decorator


def before_update(priority: int = 0, condition: Optional[Callable] = None):
    """更新前事件装饰器"""
    def decorator(func):
        func._event = BEFORE_UPDATE
        func._priority = priority
        func._condition = condition
        return func
    return decorator


def after_update(priority: int = 0, condition: Optional[Callable] = None):
    """更新后事件装饰器"""
    def decorator(func):
        func._event = AFTER_UPDATE
        func._priority = priority
        func._condition = condition
        return func
    return decorator


def before_delete(priority: int = 0, condition: Optional[Callable] = None):
    """删除前事件装饰器"""
    def decorator(func):
        func._event = BEFORE_DELETE
        func._priority = priority
        func._condition = condition
        return func
    return decorator


def after_delete(priority: int = 0, condition: Optional[Callable] = None):
    """删除后事件装饰器"""
    def decorator(func):
        func._event = AFTER_DELETE
        func._priority = priority
        func._condition = condition
        return func
    return decorator 