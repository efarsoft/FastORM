"""
FastORM Session 管理器

使用ContextVar实现线程安全的session管理。
"""

from __future__ import annotations

import contextvars
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Callable, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from fastorm.core.fastorm import FastORM

# 全局session上下文变量 - 线程安全
_session_context: contextvars.ContextVar[Optional[AsyncSession]] = (
    contextvars.ContextVar('session_context', default=None)
)


class SessionManager:
    """Session管理器
    
    提供简洁的session管理API，支持自动session和手动session。
    """
    
    @classmethod
    def get_session(cls) -> Optional[AsyncSession]:
        """获取当前上下文的session
        
        Returns:
            当前session或None
        """
        return _session_context.get()
    
    @classmethod
    def set_session(cls, session: AsyncSession) -> None:
        """设置当前上下文的session
        
        Args:
            session: 数据库session
        """
        _session_context.set(session)
    
    @classmethod
    @asynccontextmanager
    async def auto_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """自动session上下文管理器
        
        如果当前已有session则重用，否则创建新session。
        
        Yields:
            数据库session
        """
        current_session = cls.get_session()
        
        if current_session is not None:
            # 重用现有session
            yield current_session
        else:
            # 创建新session
            from fastorm.core.fastorm import FastORM
            fastorm = FastORM.get_instance()
            
            async with fastorm.session_factory() as new_session:
                cls.set_session(new_session)
                try:
                    yield new_session
                    await new_session.commit()
                except Exception:
                    await new_session.rollback()
                    raise
                finally:
                    cls.set_session(None)


async def execute_with_session(
    func: Callable[[AsyncSession], Any]
) -> Any:
    """在session上下文中执行函数
    
    自动管理session的创建、提交和回滚。
    
    Args:
        func: 接受session参数的异步函数
        
    Returns:
        函数执行结果
        
    Example:
        async def create_user(session):
            user = User(name='John')
            session.add(user)
            await session.flush()
            return user
        
        user = await execute_with_session(create_user)
    """
    async with SessionManager.auto_session() as session:
        return await func(session)


# 向后兼容的别名
get_session = SessionManager.get_session
set_session = SessionManager.set_session


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