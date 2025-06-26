"""
FastORM 数据库连接管理

提供数据库连接和会话管理功能。
"""

from __future__ import annotations

from typing import Any, Optional, AsyncGenerator
import contextlib

from sqlalchemy.ext.asyncio import (
    AsyncEngine, 
    AsyncSession, 
    create_async_engine,
    async_sessionmaker
)


class Database:
    """数据库连接管理类
    
    负责创建和管理数据库连接，提供会话管理功能。
    """
    
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker] = None
    
    @classmethod
    def init(
        cls,
        database_url: str,
        **engine_kwargs: Any
    ) -> None:
        """初始化数据库连接
        
        Args:
            database_url: 数据库连接URL
            **engine_kwargs: 引擎配置参数
        """
        cls._engine = create_async_engine(database_url, **engine_kwargs)
        cls._session_factory = async_sessionmaker(
            bind=cls._engine,
            expire_on_commit=False
        )
    
    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """获取数据库引擎
        
        Returns:
            数据库引擎
            
        Raises:
            RuntimeError: 如果数据库未初始化
        """
        if cls._engine is None:
            raise RuntimeError(
                "Database not initialized. Call Database.init() first."
            )
        return cls._engine
    
    @classmethod
    def get_session_factory(cls) -> async_sessionmaker:
        """获取会话工厂
        
        Returns:
            会话工厂
            
        Raises:
            RuntimeError: 如果数据库未初始化
        """
        if cls._session_factory is None:
            raise RuntimeError(
                "Database not initialized. Call Database.init() first."
            )
        return cls._session_factory
    
    @classmethod
    @contextlib.asynccontextmanager
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        """创建数据库会话
        
        Returns:
            数据库会话上下文管理器
        """
        session_factory = cls.get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @classmethod
    async def create_all(cls) -> None:
        """创建所有数据库表"""
        from fastorm.model.base import DeclarativeBase
        
        engine = cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(DeclarativeBase.metadata.create_all)
    
    @classmethod
    async def close(cls) -> None:
        """关闭数据库连接"""
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None 