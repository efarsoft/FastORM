"""
FastORM 自动Session管理器

实现自动session管理，让API真正简洁如ThinkORM。
"""

from __future__ import annotations

import contextlib
from typing import Optional, AsyncGenerator, Any
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession

from fastorm.connection.database import Database


# 当前会话的上下文变量
_current_session: ContextVar[Optional[AsyncSession]] = ContextVar(
    'current_session', default=None
)


class SessionManager:
    """自动Session管理器
    
    实现ThinkORM风格的简洁API，自动管理数据库会话。
    """
    
    @classmethod
    def get_current_session(cls) -> Optional[AsyncSession]:
        """获取当前上下文的会话"""
        return _current_session.get()
    
    @classmethod
    def set_current_session(cls, session: Optional[AsyncSession]) -> None:
        """设置当前上下文的会话"""
        _current_session.set(session)
    
    @classmethod
    @contextlib.asynccontextmanager
    async def auto_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """自动会话上下文管理器
        
        如果已有会话则复用，否则创建新会话。
        """
        current = cls.get_current_session()
        if current is not None:
            # 复用现有会话
            yield current
        else:
            # 创建新会话
            async with Database.session() as new_session:
                cls.set_current_session(new_session)
                try:
                    yield new_session
                finally:
                    cls.set_current_session(None)
    
    @classmethod
    async def execute_with_session(cls, func, *args, **kwargs) -> Any:
        """在会话上下文中执行函数
        
        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        current = cls.get_current_session()
        if current is not None:
            # 有现有会话，直接执行
            return await func(current, *args, **kwargs)
        else:
            # 创建新会话并执行
            async with cls.auto_session() as session:
                return await func(session, *args, **kwargs)


# 便捷函数别名
auto_session = SessionManager.auto_session
get_session = SessionManager.get_current_session
execute_with_session = SessionManager.execute_with_session


# 装饰器：自动注入session参数
def with_session(func):
    """装饰器：自动为方法注入session参数
    
    Example:
        @with_session
        async def create_user(session, name, email):
            return await User.create(session, name=name, email=email)
    """
    async def wrapper(*args, **kwargs):
        return await execute_with_session(func, *args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper 