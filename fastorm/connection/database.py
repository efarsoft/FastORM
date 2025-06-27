"""
FastORM 数据库连接管理

提供数据库连接和会话管理功能，支持读写分离和多数据库适配。
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from .adapters import DatabaseAdapterFactory
from .adapters import get_optimal_engine_config
from .adapters import validate_database_connection

logger = logging.getLogger("fastorm.database")


class ConnectionType(str, Enum):
    """连接类型"""

    WRITE = "write"  # 写操作（主库）
    READ = "read"  # 读操作（从库）


class ReadWriteConfig:
    """读写分离配置"""

    def __init__(
        self,
        enable_read_write_split: bool = False,
        read_preference: str = "prefer_secondary",
        write_concern: str = "primary_only",
        force_primary_for_transaction: bool = True,
        connection_timeout: int = 30,
        retry_writes: bool = True,
        max_retry_attempts: int = 3,
    ):
        self.enable_read_write_split = enable_read_write_split
        self.read_preference = read_preference
        self.write_concern = write_concern
        self.force_primary_for_transaction = force_primary_for_transaction
        self.connection_timeout = connection_timeout
        self.retry_writes = retry_writes
        self.max_retry_attempts = max_retry_attempts


class Database:
    """数据库连接管理类 - 纯实例方法设计

    支持单数据库和读写分离模式。
    在读写分离模式下，自动路由读写操作到相应的数据库。

    使用方式:
    ```python
    # 方式1：直接使用实例
    db = Database("postgresql+asyncpg://user:pass@localhost/db")
    async with db.session() as session:
        # 执行数据库操作
        pass
    await db.close()
    
    # 方式2：使用全局便利函数
    from fastorm.connection import init, close
    init("postgresql+asyncpg://user:pass@localhost/db")
    # 模型会自动使用默认数据库
    users = await User.where().get()
    await close()
    ```
    """

    def __init__(
        self,
        database_config: str | dict[str, str],
        read_write_config: ReadWriteConfig | None = None,
        **engine_kwargs: Any,
    ):
        """初始化数据库连接
        
        Args:
            database_config: 数据库配置，可以是单个URL或读写分离的字典
            read_write_config: 读写分离配置
            **engine_kwargs: 引擎配置参数
        """
        self._engines: dict[str, AsyncEngine] = {}
        self._session_factories: dict[str, async_sessionmaker] = {}
        self._config: ReadWriteConfig = (
            read_write_config or ReadWriteConfig()
        )
        self._is_read_write_mode: bool = False
        self._current_connection_type: ConnectionType | None = None
        
        # 初始化连接
        self._initialize_connections(database_config, **engine_kwargs)

    def _initialize_connections(
        self, 
        database_config: str | dict[str, str], 
        **engine_kwargs: Any
    ) -> None:
        """初始化数据库连接"""
        if isinstance(database_config, str):
            # 单数据库模式
            self._is_read_write_mode = False
            self._init_single_database(database_config, **engine_kwargs)
        elif isinstance(database_config, dict):
            # 读写分离模式
            self._is_read_write_mode = True
            self._init_read_write_databases(database_config, **engine_kwargs)
        else:
            raise ValueError(
                "database_config must be a string URL or dict of URLs"
            )

    def _init_single_database(
        self, database_url: str, **engine_kwargs: Any
    ) -> None:
        """初始化单数据库连接"""
        # 验证连接参数
        validation_issues = validate_database_connection(database_url)
        if validation_issues:
            logger.warning(
                f"Database connection validation issues: {validation_issues}"
            )

        # 获取最优配置
        optimal_config = get_optimal_engine_config(database_url)
        # 用户配置优先于最优配置
        final_config = {**optimal_config, **engine_kwargs}

        # 使用适配器构建连接URL
        adapter = DatabaseAdapterFactory.create_adapter(database_url)
        final_url = adapter.build_connection_url()

        engine = create_async_engine(final_url, **final_config)
        self._engines["default"] = engine
        self._session_factories["default"] = async_sessionmaker(
            bind=engine, expire_on_commit=False
        )

        logger.info(
            f"Database initialized in single mode with "
            f"{adapter.dialect_name}"
        )

    def _init_read_write_databases(
        self, database_urls: dict[str, str], **engine_kwargs: Any
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
        self._engines["write"] = write_engine
        self._session_factories["write"] = async_sessionmaker(
            bind=write_engine, expire_on_commit=False
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
            self._engines["read"] = read_engine
            self._session_factories["read"] = async_sessionmaker(
                bind=read_engine, expire_on_commit=False
            )
        else:
            # 如果没有读库，读操作也使用写库
            self._engines["read"] = write_engine
            self._session_factories["read"] = self._session_factories["write"]

        db_types = [
            write_adapter.dialect_name,
            read_adapter.dialect_name
            if "read" in database_urls
            else write_adapter.dialect_name,
        ]
        logger.info(
            f"Database initialized in read-write split mode: "
            f"{list(database_urls.keys())} ({'/'.join(set(db_types))})"
        )

    def _determine_connection_type(
        self, operation_hint: str | None = None
    ) -> str:
        """确定连接类型

        Args:
            operation_hint: 操作提示 ("read", "write", "transaction")

        Returns:
            连接键名
        """
        if not self._is_read_write_mode:
            return "default"

        # 事务操作强制使用写库
        if operation_hint == "transaction":
            return "write"

        # 明确指定写操作
        if operation_hint == "write":
            return "write"

        # 读操作
        if operation_hint == "read":
            # 检查是否有独立的读库
            return "read" if "read" in self._engines else "write"

        # 默认使用写库（保守策略）
        return "write"

    def get_engine(self, connection_type: str | None = None) -> AsyncEngine:
        """获取数据库引擎

        Args:
            connection_type: 连接类型 ("read", "write", "transaction")

        Returns:
            AsyncEngine: 数据库引擎
        """
        key = self._determine_connection_type(connection_type)
        if key not in self._engines:
            raise RuntimeError(
                f"No engine configured for connection type: {key}"
            )

        engine = self._engines[key]
        logger.debug(f"Using {key} engine for operation")
        return engine

    def get_session_factory(
        self, connection_type: str | None = None
    ) -> async_sessionmaker:
        """获取会话工厂

        Args:
            connection_type: 连接类型

        Returns:
            async_sessionmaker: 会话工厂
        """
        key = self._determine_connection_type(connection_type)
        if key not in self._session_factories:
            raise RuntimeError(
                f"No session factory for connection type: {key}"
            )

        return self._session_factories[key]

    @contextlib.asynccontextmanager
    async def session(
        self, connection_type: str | None = None, force_write: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        """创建数据库会话

        Args:
            connection_type: 连接类型
            force_write: 强制使用写库

        Yields:
            AsyncSession: 数据库会话
        """
        # 强制写库时覆盖连接类型
        if force_write:
            connection_type = "write"

        session_factory = self.get_session_factory(connection_type)

        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                # 只有在非事务模式下才自动提交
                if connection_type != "transaction":
                    await session.commit()

    @contextlib.asynccontextmanager
    async def read_session(self) -> AsyncGenerator[AsyncSession, None]:
        """创建读会话（从库优先）

        Returns:
            数据库会话
        """
        async with self.session(connection_type="read") as session:
            yield session

    @contextlib.asynccontextmanager
    async def write_session(self) -> AsyncGenerator[AsyncSession, None]:
        """创建写会话（主库）

        Returns:
            数据库会话
        """
        async with self.session(connection_type="write") as session:
            yield session

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """创建事务会话（强制使用主库）

        Returns:
            事务数据库会话
        """
        async with self.session(connection_type="transaction") as session:
            try:
                yield session
                # 事务会话的提交由调用者控制
            except Exception:
                await session.rollback()
                raise

    def get_connection_info(self) -> dict[str, Any]:
        """获取连接信息

        Returns:
            连接信息字典
        """
        return {
            "mode": "read_write_split" if self._is_read_write_mode else "single",
            "engines": list(self._engines.keys()),
            "read_write_split_enabled": self._config.enable_read_write_split,
            "current_connection_type": self._current_connection_type.value
            if self._current_connection_type
            else None,
        }

    async def create_all(self) -> None:
        """创建所有数据库表（在写库上执行）"""
        from fastorm.model.model import DeclarativeBase

        # 总是在写库上创建表
        engine = self.get_engine("write")
        async with engine.begin() as conn:
            await conn.run_sync(DeclarativeBase.metadata.create_all)

        logger.info("All database tables created on write database")

    async def close(self) -> None:
        """关闭所有数据库连接"""
        logger.info("Closing database connections...")

        for name, engine in self._engines.items():
            try:
                await engine.dispose()
                logger.debug(f"Closed {name} engine")
            except Exception as e:
                logger.error(f"Error closing {name} engine: {e}")

        self._engines.clear()
        self._session_factories.clear()

        logger.info("All database connections closed")


# =================================================================
# 全局便利函数 - 管理默认数据库实例
# =================================================================

_default_database: Database | None = None


def init(
    database_config: str | dict[str, str],
    read_write_config: ReadWriteConfig | None = None,
    **engine_kwargs: Any,
) -> Database:
    """初始化默认数据库连接
    
    这是一个便利函数，内部创建Database实例并设置为默认数据库。
    
    Args:
        database_config: 数据库配置，可以是单个URL或读写分离的字典
        read_write_config: 读写分离配置
        **engine_kwargs: 引擎配置参数
        
    Returns:
        Database: 数据库实例
        
    Example:
        # 单数据库
        db = init("sqlite+aiosqlite:///:memory:")
        
        # 读写分离
        db = init({
            "write": "postgresql://user:pass@master/db",
            "read": "postgresql://user:pass@slave/db"
        })
    """
    global _default_database
    _default_database = Database(database_config, read_write_config, **engine_kwargs)
    logger.info("Default database initialized")
    return _default_database


def get_default() -> Database:
    """获取默认数据库实例
    
    Returns:
        Database: 默认数据库实例
        
    Raises:
        RuntimeError: 如果未初始化默认数据库
    """
    if _default_database is None:
        raise RuntimeError(
            "Default database not initialized. "
            "Use init(url) or Database(url) first."
        )
    return _default_database


async def create_all() -> None:
    """在默认数据库上创建所有表"""
    db = get_default()
    await db.create_all()


async def close() -> None:
    """关闭默认数据库连接"""
    global _default_database
    if _default_database:
        await _default_database.close()
        _default_database = None
        logger.info("Default database closed")


@contextlib.asynccontextmanager
async def session(
    connection_type: str | None = None, force_write: bool = False
) -> AsyncGenerator[AsyncSession, None]:
    """使用默认数据库创建会话
    
    Args:
        connection_type: 连接类型
        force_write: 强制使用写库
        
    Yields:
        AsyncSession: 数据库会话
    """
    db = get_default()
    async with db.session(connection_type, force_write) as s:
        yield s


@contextlib.asynccontextmanager
async def read_session() -> AsyncGenerator[AsyncSession, None]:
    """使用默认数据库创建读会话"""
    db = get_default()
    async with db.read_session() as s:
        yield s


@contextlib.asynccontextmanager
async def write_session() -> AsyncGenerator[AsyncSession, None]:
    """使用默认数据库创建写会话"""
    db = get_default()
    async with db.write_session() as s:
        yield s


@contextlib.asynccontextmanager
async def transaction() -> AsyncGenerator[AsyncSession, None]:
    """使用默认数据库创建事务会话"""
    db = get_default()
    async with db.transaction() as s:
        yield s


def get_connection_info() -> dict[str, Any]:
    """获取默认数据库连接信息"""
    db = get_default()
    return db.get_connection_info()