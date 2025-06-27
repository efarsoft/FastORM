"""
FastORM Session 管理器

使用ContextVar实现线程安全的session管理，支持读写分离。
"""

from __future__ import annotations

import contextvars
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Callable, Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from fastorm.core.fastorm import FastORM
    from fastorm.connection.database import Database

# 全局session上下文变量 - 线程安全
_session_context: contextvars.ContextVar[Optional[AsyncSession]] = (
    contextvars.ContextVar('session_context', default=None)
)


class SessionManager:
    """Session管理器
    
    提供简洁的session管理API，支持自动session和手动session，集成读写分离。
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
    async def auto_session(
        cls, 
        connection_type: Optional[str] = None,
        force_write: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        """自动session上下文管理器
        
        如果当前已有session则重用，否则创建新session。
        支持读写分离的会话类型选择。
        
        Args:
            connection_type: 连接类型提示 ("read", "write", "transaction")
            force_write: 强制使用写库
        
        Yields:
            数据库session
        """
        current_session = cls.get_session()
        
        if current_session is not None:
            # 重用现有session
            yield current_session
        else:
            # 创建新session，支持读写分离
            from fastorm.connection.database import Database
            
            # 根据提示确定连接类型
            if force_write:
                connection_type = "write"
            
            async with Database.session(
                connection_type=connection_type, 
                force_write=force_write
            ) as new_session:
                cls.set_session(new_session)
                try:
                    yield new_session
                    # commit已经在Database.session中处理
                except Exception:
                    # rollback已经在Database.session中处理
                    raise
                finally:
                    cls.set_session(None)


async def execute_with_session(
    func: Callable[[AsyncSession], Any],
    connection_type: Optional[str] = None,
    force_write: bool = False
) -> Any:
    """在session上下文中执行函数
    
    自动管理session的创建、提交和回滚，支持读写分离。
    
    Args:
        func: 接受session参数的异步函数
        connection_type: 连接类型提示 ("read", "write", "transaction")
        force_write: 强制使用写库
        
    Returns:
        函数执行结果
        
    Example:
        # 读操作 - 自动使用从库
        async def get_user(session):
            return await session.get(User, 1)
        user = await execute_with_session(get_user)
        
        # 写操作 - 自动使用主库
        async def create_user(session):
            user = User(name='John')
            session.add(user)
            await session.flush()
            return user
        user = await execute_with_session(create_user, connection_type="write")
        
        # 强制使用主库（读自己的写）
        user = await execute_with_session(get_user, force_write=True)
    """
    async with SessionManager.auto_session(
        connection_type=connection_type, 
        force_write=force_write
    ) as session:
        return await func(session)


# 向后兼容的别名
get_session = SessionManager.get_session
set_session = SessionManager.set_session


# 装饰器：自动注入session参数
def with_session(
    connection_type: Optional[str] = None, 
    force_write: bool = False
):
    """装饰器：自动为方法注入session参数，支持读写分离
    
    Args:
        connection_type: 连接类型提示 ("read", "write", "transaction")
        force_write: 强制使用写库
    
    Example:
        @with_session(connection_type="read")
        async def get_user_by_email(session, email):
            return await User.where('email', email).first()
        
        @with_session(connection_type="write")  
        async def create_user(session, name, email):
            return await User.create(name=name, email=email)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await execute_with_session(
                lambda session: func(session, *args, **kwargs),
                connection_type=connection_type,
                force_write=force_write
            )
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator 