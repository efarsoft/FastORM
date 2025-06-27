"""
FastORM会话管理模块

提供SQLAlchemy 2.0会话的包装和管理
"""

from typing import Any, Optional, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

T = TypeVar("T")


class Session:
    """FastORM会话包装器"""
    
    def __init__(self, async_session: AsyncSession):
        self._async_session = async_session
    
    @property
    def async_session(self) -> AsyncSession:
        """获取底层的异步会话"""
        return self._async_session
    
    async def get(self, model_class: Type[T], primary_key: Any) -> Optional[T]:
        """根据主键获取实例"""
        return await self._async_session.get(model_class, primary_key)
    
    def add(self, instance: Any) -> None:
        """添加实例到会话"""
        self._async_session.add(instance)
    
    async def delete(self, instance: Any) -> None:
        """删除实例"""
        await self._async_session.delete(instance)
    
    async def commit(self) -> None:
        """提交事务"""
        await self._async_session.commit()
    
    async def rollback(self) -> None:
        """回滚事务"""
        await self._async_session.rollback()
    
    async def flush(self) -> None:
        """刷新会话"""
        await self._async_session.flush()
    
    async def refresh(self, instance: Any) -> None:
        """刷新实例"""
        await self._async_session.refresh(instance)
    
    async def close(self) -> None:
        """关闭会话"""
        await self._async_session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.close() 