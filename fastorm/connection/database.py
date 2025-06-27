"""
FastORM 数据库连接管理

提供数据库连接和会话管理功能，支持读写分离和多数据库适配。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from enum import Enum
from typing import Any, Optional, AsyncGenerator, Dict, Union

from sqlalchemy.ext.asyncio import (
    AsyncEngine, 
    AsyncSession, 
    create_async_engine,
    async_sessionmaker
)

from .adapters import (
    DatabaseAdapterFactory, 
    get_optimal_engine_config, 
    validate_database_connection,
    DatabaseAdapter
)

logger = logging.getLogger("fastorm.database")


class ConnectionType(str, Enum):
    """连接类型"""
    WRITE = "write"  # 写操作（主库）
    READ = "read"    # 读操作（从库）


class ReadWriteConfig:
    """读写分离配置"""
    
    def __init__(
        self,
        enable_read_write_split: bool = False,
        read_preference: str = "prefer_secondary",  # prefer_secondary, primary_only
        write_concern: str = "primary_only",  # primary_only
        force_primary_for_transaction: bool = True,
        connection_timeout: int = 30,
        retry_writes: bool = True,
        max_retry_attempts: int = 3
    ):
        self.enable_read_write_split = enable_read_write_split
        self.read_preference = read_preference
        self.write_concern = write_concern
        self.force_primary_for_transaction = force_primary_for_transaction
        self.connection_timeout = connection_timeout
        self.retry_writes = retry_writes
        self.max_retry_attempts = max_retry_attempts


class Database:
    """数据库连接管理类
    
    支持单数据库和读写分离模式。
    在读写分离模式下，自动路由读写操作到相应的数据库。
    
    单数据库模式:
    ```python
    Database.init("postgresql+asyncpg://user:pass@localhost/db")
    ```
    
    读写分离模式:
    ```python
    Database.init({
        "write": "postgresql+asyncpg://user:pass@master.db/mydb", 
        "read": "postgresql+asyncpg://user:pass@slave.db/mydb"
    })
    ```
    """
    
    _engines: Dict[str, AsyncEngine] = {}
    _session_factories: Dict[str, async_sessionmaker] = {}
    _config: Optional[ReadWriteConfig] = None
    _is_read_write_mode: bool = False
    _current_connection_type: Optional[ConnectionType] = None
    
    @classmethod
    def init(
        cls,
        database_config: Union[str, Dict[str, str]],
        read_write_config: Optional[ReadWriteConfig] = None,
        **engine_kwargs: Any
    ) -> None:
        """初始化数据库连接
        
        Args:
            database_config: 数据库配置，可以是单个URL或读写分离的字典
            read_write_config: 读写分离配置
            **engine_kwargs: 引擎配置参数
        """
        cls._config = read_write_config or ReadWriteConfig()
        
        if isinstance(database_config, str):
            # 单数据库模式
            cls._is_read_write_mode = False
            cls._init_single_database(database_config, **engine_kwargs)
        elif isinstance(database_config, dict):
            # 读写分离模式
            cls._is_read_write_mode = True
            cls._init_read_write_databases(database_config, **engine_kwargs)
        else:
            raise ValueError("database_config must be a string URL or dict of URLs")
    
    @classmethod
    def _init_single_database(cls, database_url: str, **engine_kwargs: Any) -> None:
        """初始化单数据库连接"""
        # 验证连接参数
        validation_issues = validate_database_connection(database_url)
        if validation_issues:
            logger.warning(f"Database connection validation issues: {validation_issues}")
        
        # 获取最优配置
        optimal_config = get_optimal_engine_config(database_url)
        # 用户配置优先于最优配置
        final_config = {**optimal_config, **engine_kwargs}
        
        # 使用适配器构建连接URL
        adapter = DatabaseAdapterFactory.create_adapter(database_url)
        final_url = adapter.build_connection_url()
        
        engine = create_async_engine(final_url, **final_config)
        cls._engines["default"] = engine
        cls._session_factories["default"] = async_sessionmaker(
            bind=engine,
            expire_on_commit=False
        )
        
        logger.info(
            f"Database initialized in single mode with {adapter.dialect_name}"
        )
    
    @classmethod 
    def _init_read_write_databases(
        cls, 
        database_urls: Dict[str, str], 
        **engine_kwargs: Any
    ) -> None:
        """初始化读写分离数据库连接"""
        required_keys = ["write"]
        for key in required_keys:
            if key not in database_urls:
                raise ValueError(
                    f"Missing required database config key: {key}"
                )
        
        # 创建写库连接
        write_url = database_urls["write"]
        write_adapter = DatabaseAdapterFactory.create_adapter(write_url)
        write_config = get_optimal_engine_config(write_url)
        write_final_config = {**write_config, **engine_kwargs}
        write_final_url = write_adapter.build_connection_url()
        
        write_engine = create_async_engine(
            write_final_url, **write_final_config
        )
        cls._engines["write"] = write_engine
        cls._session_factories["write"] = async_sessionmaker(
            bind=write_engine,
            expire_on_commit=False
        )
        
        # 创建读库连接（如果有的话）
        if "read" in database_urls:
            read_url = database_urls["read"]
            read_adapter = DatabaseAdapterFactory.create_adapter(read_url)
            read_config = get_optimal_engine_config(read_url)
            read_final_config = {**read_config, **engine_kwargs}
            read_final_url = read_adapter.build_connection_url()
            
            read_engine = create_async_engine(
                read_final_url, **read_final_config
            )
            cls._engines["read"] = read_engine
            cls._session_factories["read"] = async_sessionmaker(
                bind=read_engine,
                expire_on_commit=False
            )
        else:
            # 如果没有读库，读操作也使用写库
            cls._engines["read"] = write_engine
            cls._session_factories["read"] = cls._session_factories["write"]
        
        db_types = [
            write_adapter.dialect_name,
            read_adapter.dialect_name if "read" in database_urls 
            else write_adapter.dialect_name
        ]
        logger.info(
            f"Database initialized in read-write split mode: "
            f"{list(database_urls.keys())} ({'/'.join(set(db_types))})"
        )
    
    @classmethod
    def _determine_connection_type(cls, operation_hint: Optional[str] = None) -> str:
        """确定连接类型
        
        Args:
            operation_hint: 操作提示 ("read", "write", "transaction")
            
        Returns:
            连接键名
        """
        if not cls._is_read_write_mode:
            return "default"
        
        if not cls._config.enable_read_write_split:
            return "write"  # 禁用读写分离时使用写库
        
        # 如果在事务中，强制使用写库
        if cls._current_connection_type == ConnectionType.WRITE:
            return "write"
        
        # 根据操作提示决定
        if operation_hint == "write" or operation_hint == "transaction":
            return "write"
        elif operation_hint == "read":
            # 检查读偏好设置
            if cls._config.read_preference == "primary_only":
                return "write"
            elif "read" in cls._engines:
                return "read"
            else:
                return "write"  # 降级到写库
        
        # 默认情况：有读库则用读库，否则用写库
        return "read" if "read" in cls._engines else "write"
    
    @classmethod
    def get_engine(cls, connection_type: Optional[str] = None) -> AsyncEngine:
        """获取数据库引擎
        
        Args:
            connection_type: 连接类型提示
            
        Returns:
            数据库引擎
            
        Raises:
            RuntimeError: 如果数据库未初始化
        """
        if not cls._engines:
            raise RuntimeError(
                "Database not initialized. Call Database.init() first."
            )
        
        conn_key = cls._determine_connection_type(connection_type)
        return cls._engines[conn_key]
    
    @classmethod
    def get_session_factory(cls, connection_type: Optional[str] = None) -> async_sessionmaker:
        """获取会话工厂
        
        Args:
            connection_type: 连接类型提示
            
        Returns:
            会话工厂
            
        Raises:
            RuntimeError: 如果数据库未初始化
        """
        if not cls._session_factories:
            raise RuntimeError(
                "Database not initialized. Call Database.init() first."
            )
        
        conn_key = cls._determine_connection_type(connection_type)
        return cls._session_factories[conn_key]
    
    @classmethod
    @contextlib.asynccontextmanager
    async def session(
        cls, 
        connection_type: Optional[str] = None,
        force_write: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        """创建数据库会话
        
        Args:
            connection_type: 连接类型提示 ("read", "write", "transaction")
            force_write: 强制使用写库
            
        Returns:
            数据库会话上下文管理器
        """
        if force_write:
            connection_type = "write"
        
        session_factory = cls.get_session_factory(connection_type)
        
        async with session_factory() as session:
            try:
                # 设置当前连接类型上下文
                if connection_type == "write" or connection_type == "transaction":
                    cls._current_connection_type = ConnectionType.WRITE
                else:
                    cls._current_connection_type = ConnectionType.READ
                
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
                cls._current_connection_type = None
    
    @classmethod
    @contextlib.asynccontextmanager 
    async def read_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """创建只读会话（优先使用从库）
        
        Returns:
            只读数据库会话
        """
        async with cls.session(connection_type="read") as session:
            yield session
    
    @classmethod
    @contextlib.asynccontextmanager
    async def write_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """创建写入会话（强制使用主库）
        
        Returns:
            写入数据库会话
        """
        async with cls.session(connection_type="write") as session:
            yield session
    
    @classmethod
    @contextlib.asynccontextmanager
    async def transaction(cls) -> AsyncGenerator[AsyncSession, None]:
        """创建事务会话（强制使用主库）
        
        Returns:
            事务数据库会话
        """
        async with cls.session(connection_type="transaction") as session:
            try:
                yield session
                # 事务会话的提交由调用者控制
            except Exception:
                await session.rollback()
                raise
    
    @classmethod
    def get_connection_info(cls) -> Dict[str, Any]:
        """获取连接信息
        
        Returns:
            连接信息字典
        """
        return {
            "mode": "read_write_split" if cls._is_read_write_mode else "single",
            "engines": list(cls._engines.keys()),
            "read_write_split_enabled": cls._config.enable_read_write_split if cls._config else False,
            "current_connection_type": cls._current_connection_type.value if cls._current_connection_type else None
        }
    
    @classmethod
    async def create_all(cls) -> None:
        """创建所有数据库表（在写库上执行）"""
        from fastorm.model.model import DeclarativeBase
        
        # 总是在写库上创建表
        engine = cls.get_engine("write")
        async with engine.begin() as conn:
            await conn.run_sync(DeclarativeBase.metadata.create_all)
        
        logger.info("All database tables created on write database")
    
    @classmethod
    async def close(cls) -> None:
        """关闭所有数据库连接"""
        for engine in cls._engines.values():
            await engine.dispose()
        
        cls._engines.clear()
        cls._session_factories.clear()
        cls._config = None
        cls._is_read_write_mode = False
        cls._current_connection_type = None
        
        logger.info("All database connections closed") 