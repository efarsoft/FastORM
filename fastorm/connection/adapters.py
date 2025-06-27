"""
FastORM 多数据库适配器系统

提供数据库特性检测、最优配置和兼容性支持。
支持PostgreSQL、MySQL、SQLite的企业级特性。
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.engine import URL


@dataclass
class DatabaseFeatures:
    """数据库特性描述

    定义数据库支持的功能和限制。
    """

    supports_json_fields: bool = False
    supports_array_fields: bool = False
    supports_full_text_search: bool = False
    supports_window_functions: bool = True
    supports_cte: bool = True
    supports_upsert: bool = False
    supports_returning: bool = False
    supports_transactions: bool = True
    supports_savepoints: bool = True
    supports_foreign_keys: bool = True
    supports_check_constraints: bool = True
    supports_partial_indexes: bool = False
    supports_concurrent_indexes: bool = False
    max_identifier_length: int = 63
    max_index_name_length: int = 63
    max_column_name_length: int = 63
    case_sensitive: bool = False
    requires_literal_defaults: bool = False
    supports_schemas: bool = True
    default_schema_name: str | None = None


@dataclass
class OptimalConfig:
    """数据库最优配置

    针对不同数据库的连接池和性能优化配置。
    """

    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    # SQLAlchemy 2.0 新特性
    query_cache_size: int = 1200
    compiled_cache_size: int = 1000
    # 数据库特定配置
    extra_engine_options: dict[str, Any] = None

    def __post_init__(self):
        if self.extra_engine_options is None:
            self.extra_engine_options = {}


class DatabaseAdapter(ABC):
    """数据库适配器基类

    定义数据库适配器的标准接口，遵循SQLAlchemy 2.0规范。
    """

    def __init__(self, database_url: str | URL):
        self.database_url = (
            database_url if isinstance(database_url, str) else str(database_url)
        )
        self.parsed_url = urlparse(self.database_url)
        self._features: DatabaseFeatures | None = None
        self._optimal_config: OptimalConfig | None = None

    @property
    @abstractmethod
    def dialect_name(self) -> str:
        """数据库方言名称"""
        pass

    @property
    @abstractmethod
    def default_driver(self) -> str:
        """默认异步驱动"""
        pass

    @property
    @abstractmethod
    def available_drivers(self) -> set[str]:
        """可用的异步驱动列表"""
        pass

    @property
    def features(self) -> DatabaseFeatures:
        """获取数据库特性"""
        if self._features is None:
            self._features = self._detect_features()
        return self._features

    @property
    def optimal_config(self) -> OptimalConfig:
        """获取最优配置"""
        if self._optimal_config is None:
            self._optimal_config = self._build_optimal_config()
        return self._optimal_config

    @abstractmethod
    def _detect_features(self) -> DatabaseFeatures:
        """检测数据库特性"""
        pass

    @abstractmethod
    def _build_optimal_config(self) -> OptimalConfig:
        """构建最优配置"""
        pass

    def detect_driver(self) -> str:
        """检测可用的驱动"""
        for driver in [self.default_driver] + list(self.available_drivers):
            try:
                __import__(driver)
                return driver
            except ImportError:
                continue

        raise ImportError(
            f"没有找到可用的{self.dialect_name}驱动。"
            f"请安装以下驱动之一: {', '.join(self.available_drivers)}"
        )

    def build_connection_url(self, driver: str | None = None) -> str:
        """构建连接URL"""
        if driver is None:
            driver = self.detect_driver()

        # 解析原始URL
        scheme_parts = self.parsed_url.scheme.split("+")
        base_scheme = scheme_parts[0]

        # 构建新的scheme
        new_scheme = f"{base_scheme}+{driver}"

        # 重构URL
        return self.database_url.replace(self.parsed_url.scheme, new_scheme, 1)

    def validate_connection_params(self) -> dict[str, str]:
        """验证连接参数并返回问题"""
        issues = {}

        if not self.parsed_url.hostname:
            issues["hostname"] = "缺少主机名"
        if not self.parsed_url.username:
            issues["username"] = "缺少用户名"
        if not self.parsed_url.path or self.parsed_url.path == "/":
            issues["database"] = "缺少数据库名"

        return issues


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL数据库适配器

    支持PostgreSQL 12+的现代特性。
    """

    @property
    def dialect_name(self) -> str:
        return "postgresql"

    @property
    def default_driver(self) -> str:
        return "asyncpg"

    @property
    def available_drivers(self) -> set[str]:
        return {"asyncpg", "psycopg"}

    def _detect_features(self) -> DatabaseFeatures:
        """PostgreSQL特性检测"""
        return DatabaseFeatures(
            supports_json_fields=True,
            supports_array_fields=True,
            supports_full_text_search=True,
            supports_window_functions=True,
            supports_cte=True,
            supports_upsert=True,  # ON CONFLICT
            supports_returning=True,
            supports_transactions=True,
            supports_savepoints=True,
            supports_foreign_keys=True,
            supports_check_constraints=True,
            supports_partial_indexes=True,
            supports_concurrent_indexes=True,
            max_identifier_length=63,
            max_index_name_length=63,
            max_column_name_length=63,
            case_sensitive=True,
            requires_literal_defaults=False,
            supports_schemas=True,
            default_schema_name="public",
        )

    def _build_optimal_config(self) -> OptimalConfig:
        """PostgreSQL最优配置"""
        return OptimalConfig(
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
            query_cache_size=1200,
            compiled_cache_size=1000,
            extra_engine_options={
                # PostgreSQL特定优化
                "server_side_cursors": True,
                "stream_results": True,
                # asyncpg特定配置
                "command_timeout": 60,
                "server_settings": {
                    "jit": "off",  # 对于小查询禁用JIT
                    "application_name": "FastORM",
                },
            },
        )


class MySQLAdapter(DatabaseAdapter):
    """MySQL数据库适配器

    支持MySQL 8.0+和MariaDB 10.5+的现代特性。
    """

    @property
    def dialect_name(self) -> str:
        return "mysql"

    @property
    def default_driver(self) -> str:
        return "aiomysql"

    @property
    def available_drivers(self) -> set[str]:
        return {"aiomysql", "asyncmy"}

    def _detect_features(self) -> DatabaseFeatures:
        """MySQL特性检测"""
        return DatabaseFeatures(
            supports_json_fields=True,  # MySQL 5.7+
            supports_array_fields=False,
            supports_full_text_search=True,
            supports_window_functions=True,  # MySQL 8.0+
            supports_cte=True,  # MySQL 8.0+
            supports_upsert=True,  # ON DUPLICATE KEY UPDATE
            supports_returning=False,  # MySQL不支持RETURNING
            supports_transactions=True,
            supports_savepoints=True,
            supports_foreign_keys=True,
            supports_check_constraints=True,  # MySQL 8.0.16+
            supports_partial_indexes=False,
            supports_concurrent_indexes=False,
            max_identifier_length=64,
            max_index_name_length=64,
            max_column_name_length=64,
            case_sensitive=False,  # 取决于配置，默认不敏感
            requires_literal_defaults=True,
            supports_schemas=True,
            default_schema_name=None,
        )

    def _build_optimal_config(self) -> OptimalConfig:
        """MySQL最优配置"""
        return OptimalConfig(
            pool_size=8,
            max_overflow=16,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
            query_cache_size=1200,
            compiled_cache_size=1000,
            extra_engine_options={
                # MySQL特定优化
                "charset": "utf8mb4",
                "use_unicode": True,
                "autocommit": False,
                # 连接参数
                "connect_timeout": 60,
                "read_timeout": 30,
                "write_timeout": 30,
            },
        )


class SQLiteAdapter(DatabaseAdapter):
    """SQLite数据库适配器

    支持SQLite 3.35+的现代特性。
    """

    @property
    def dialect_name(self) -> str:
        return "sqlite"

    @property
    def default_driver(self) -> str:
        return "aiosqlite"

    @property
    def available_drivers(self) -> set[str]:
        return {"aiosqlite"}

    def _detect_features(self) -> DatabaseFeatures:
        """SQLite特性检测"""
        return DatabaseFeatures(
            supports_json_fields=True,  # SQLite 3.38+
            supports_array_fields=False,
            supports_full_text_search=True,  # FTS5
            supports_window_functions=True,  # SQLite 3.25+
            supports_cte=True,  # SQLite 3.8.3+
            supports_upsert=True,  # ON CONFLICT
            supports_returning=True,  # SQLite 3.35+
            supports_transactions=True,
            supports_savepoints=True,
            supports_foreign_keys=True,
            supports_check_constraints=True,
            supports_partial_indexes=True,
            supports_concurrent_indexes=False,
            max_identifier_length=1000,
            max_index_name_length=1000,
            max_column_name_length=1000,
            case_sensitive=True,
            requires_literal_defaults=False,
            supports_schemas=True,
            default_schema_name="main",
        )

    def _build_optimal_config(self) -> OptimalConfig:
        """SQLite最优配置"""
        return OptimalConfig(
            pool_size=1,  # SQLite是单文件数据库
            max_overflow=0,
            pool_timeout=30,
            pool_recycle=-1,  # SQLite不需要回收连接
            pool_pre_ping=False,
            echo=False,
            query_cache_size=1200,
            compiled_cache_size=1000,
            extra_engine_options={
                # SQLite特定优化
                "timeout": 20,
                "check_same_thread": False,
                # SQLite性能优化参数
                "pragmas": {
                    "journal_mode": "WAL",
                    "cache_size": -1 * 64000,  # 64MB
                    "foreign_keys": 1,
                    "ignore_check_constraints": 0,
                    "synchronous": 0,
                },
            },
        )

    def validate_connection_params(self) -> dict[str, str]:
        """SQLite特殊的连接参数验证"""
        issues = {}

        # SQLite不需要hostname、username等
        if not self.parsed_url.path or self.parsed_url.path == "/":
            issues["database"] = "缺少数据库文件路径"

        return issues


class DatabaseAdapterFactory:
    """数据库适配器工厂

    根据数据库URL自动创建适当的适配器。
    """

    _adapters: dict[str, type[DatabaseAdapter]] = {
        "postgresql": PostgreSQLAdapter,
        "mysql": MySQLAdapter,
        "sqlite": SQLiteAdapter,
    }

    @classmethod
    def create_adapter(cls, database_url: str | URL) -> DatabaseAdapter:
        """创建数据库适配器

        Args:
            database_url: 数据库连接URL

        Returns:
            适配器实例

        Raises:
            ValueError: 不支持的数据库类型
        """
        if isinstance(database_url, str):
            parsed_url = urlparse(database_url)
        else:
            parsed_url = urlparse(str(database_url))

        # 提取数据库类型
        scheme_parts = parsed_url.scheme.split("+")
        dialect = scheme_parts[0].lower()

        if dialect not in cls._adapters:
            raise ValueError(
                f"不支持的数据库类型: {dialect}。"
                f"支持的类型: {', '.join(cls._adapters.keys())}"
            )

        adapter_class = cls._adapters[dialect]
        return adapter_class(database_url)

    @classmethod
    def register_adapter(
        cls, dialect: str, adapter_class: type[DatabaseAdapter]
    ) -> None:
        """注册自定义适配器

        Args:
            dialect: 数据库方言名称
            adapter_class: 适配器类
        """
        cls._adapters[dialect] = adapter_class

    @classmethod
    def get_supported_dialects(cls) -> set[str]:
        """获取支持的数据库类型"""
        return set(cls._adapters.keys())


def detect_database_type(database_url: str | URL) -> str:
    """检测数据库类型

    Args:
        database_url: 数据库连接URL

    Returns:
        数据库类型名称
    """
    adapter = DatabaseAdapterFactory.create_adapter(database_url)
    return adapter.dialect_name


def get_optimal_engine_config(database_url: str | URL) -> dict[str, Any]:
    """获取数据库的最优引擎配置

    Args:
        database_url: 数据库连接URL

    Returns:
        引擎配置字典
    """
    adapter = DatabaseAdapterFactory.create_adapter(database_url)
    config = adapter.optimal_config

    # 构建引擎配置
    engine_config = {
        "pool_size": config.pool_size,
        "max_overflow": config.max_overflow,
        "pool_timeout": config.pool_timeout,
        "pool_recycle": config.pool_recycle,
        "pool_pre_ping": config.pool_pre_ping,
        "echo": config.echo,
        # SQLAlchemy 2.0 新特性
        "query_cache_size": config.query_cache_size,
        "compiled_cache_size": config.compiled_cache_size,
    }

    # 添加数据库特定配置
    engine_config.update(config.extra_engine_options)

    return engine_config


def validate_database_connection(database_url: str | URL) -> dict[str, str]:
    """验证数据库连接参数

    Args:
        database_url: 数据库连接URL

    Returns:
        验证问题字典，空字典表示无问题
    """
    try:
        adapter = DatabaseAdapterFactory.create_adapter(database_url)
        return adapter.validate_connection_params()
    except ValueError as e:
        return {"adapter": str(e)}


__all__ = [
    "DatabaseFeatures",
    "OptimalConfig",
    "DatabaseAdapter",
    "PostgreSQLAdapter",
    "MySQLAdapter",
    "SQLiteAdapter",
    "DatabaseAdapterFactory",
    "detect_database_type",
    "get_optimal_engine_config",
    "validate_database_connection",
]
