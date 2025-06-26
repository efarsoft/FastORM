"""
FastORM 核心类

提供数据库连接和模型管理功能。
"""

from __future__ import annotations

from typing import Optional, Any

from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker
)


class FastORM:
    """FastORM 主类"""
    
    def __init__(self, database_url: str, **kwargs: Any):
        """初始化FastORM
        
        Args:
            database_url: 数据库连接URL
            **kwargs: 其他数据库配置参数
        """
        self.database_url = database_url
        self.engine = create_async_engine(database_url, **kwargs)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 设置全局数据库实例
        FastORM._instance = self
    
    _instance: Optional[FastORM] = None
    
    @classmethod
    def get_instance(cls) -> FastORM:
        """获取FastORM实例"""
        if cls._instance is None:
            raise RuntimeError(
                "FastORM not initialized. Call FastORM(database_url) first."
            )
        return cls._instance
    
    async def create_session(self) -> AsyncSession:
        """创建新的数据库会话"""
        return self.session_factory()
    
    async def create_all(self):
        """创建所有表"""
        from fastorm.model.model import Model
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Model.metadata.create_all)
    
    async def drop_all(self):
        """删除所有表"""
        from fastorm.model.model import Model
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Model.metadata.drop_all)
    
    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose() 