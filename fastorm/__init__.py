"""
FastORM - 专为FastAPI优化的现代异步ORM框架

FastORM = FastAPI + SQLAlchemy 2.0 + Pydantic 2.11 的完美融合
简洁如ThinkORM，优雅如Eloquent，现代如FastAPI

Version: 1.0.0
Author: FastORM Team
Homepage: https://fastorm.dev
Repository: https://github.com/fastorm/fastorm

核心特性:
- 🚀 100% SQLAlchemy 2.0.40规范遵循（编译缓存、高级类型注解、async优化）
- 🔧 100% Pydantic 2.11规范遵循（实验性特性、高级验证器、优化序列化）
- ⚡ 100% FastAPI 0.115.12规范遵循（lifespan管理、dependency injection、类型安全）
- 🎯 API设计哲学：简洁、直观、类型安全
- 💡 企业级特性：高性能、可扩展、生产就绪

示例用法：
```python
from fastorm import BaseModel, Database
from sqlalchemy.orm import Mapped, mapped_column

class User(BaseModel):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]

# 初始化数据库
await Database.init("postgresql+asyncpg://user:pass@localhost/db")

# 使用模型
user = await User.create(name="张三", email="zhang@example.com")
users = await User.where("name", "like", "%张%").limit(10).get()
```
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

# 版本信息
__version__ = "1.0.0"
__author__ = "FastORM Team"
__email__ = "team@fastorm.dev"
__license__ = "MIT"
__homepage__ = "https://fastorm.dev"
__repository__ = "https://github.com/fastorm/fastorm"

# 配置日志
logger = logging.getLogger("fastorm")

# =============================================================================
# 主要导出API - 稍后定义实际的导入和导出
# =============================================================================

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__homepage__",
    "__repository__",
    
    # 核心类
    "FastORM",
    
    # 核心模型
    "BaseModel",
    "Model",  # 增强版模型
    "DeclarativeBase",
    
    # 查询与数据库
    "QueryBuilder", 
    "Database",
    "Session",
    
    # 仓储模式
    "BaseRepository",
    
    # Schema系统
    "FastORMSchema",
    "CreateSchema",
    "UpdateSchema", 
    "ResponseSchema",
    "PaginatedResponseSchema",
    "SchemaFactory",
    "create_schema_from_model",
    "create_response_schema",
    "create_partial_schema",
    
    # Pydantic 2.11验证器
    "field_validator_v2",
    "model_validator_v2",
    "computed_field",
    "field_serializer",
    
    # FastAPI集成
    "get_session",
    "get_repository", 
    "get_db",
    "Depends",
    "create_lifespan",
    "database_lifespan",
    "create_crud_router",
    "CRUDRouter",
    
    # SQLAlchemy 2.0类型
    "Mapped",
    "mapped_column",
    "relationship",
    "ForeignKey",
    "Index",
    "UniqueConstraint",
    "CheckConstraint",
    
    # Pydantic类型
    "EmailStr",
    "HttpUrl", 
    "UUID4",
    "Field",
    "ConfigDict",
    "BeforeValidator",
    "AfterValidator", 
    "PlainValidator",
    
    # 高级特性
    "CacheManager",
    "cache_query",
    "invalidate_cache",
    "EventManager", 
    "event_listener",
    "BatchOperations",
    "MigrationManager",
    
    # 异常
    "FastORMError",
    "DatabaseError",
    "ValidationError",
    "RecordNotFoundError", 
    "IntegrityError",
    "ConnectionError",
    "QueryError",
    "SchemaError",
    "ConfigurationError",
    
    # 工具函数
    "to_snake_case",
    "to_camel_case",
    "get_table_name",
    "get_primary_key",
    "Pagination",
    "paginate_query",
    
    # 配置
    "FastORMSettings",
    "config_manager",
    
    # 初始化函数
    "init",
    "setup_fastapi",
    
    # 测试支持 (Stage 8)
    'Factory', 'trait', 'LazyAttribute', 'Sequence',
    'Seeder', 'DatabaseSeeder',
    'TestCase', 'DatabaseTestCase', 
    'faker', 'ChineseProvider', 'CompanyProvider', 'TestDataProvider',
    
    # 性能监控 (Stage 9)
    'QueryProfiler', 'PerformanceMonitor', 'N1Detector', 'PerformanceReporter',
    'profile_query', 'start_monitoring', 'stop_monitoring', 
    'get_performance_stats', 'print_performance_summary',
]

# =============================================================================
# 延迟导入 - 避免循环导入，仅在实际使用时导入
# =============================================================================

def __getattr__(name: str) -> Any:
    """延迟导入模块和类"""
    
    # 核心类
    if name == "FastORM":
        from fastorm.core.fastorm import FastORM
        return FastORM
    
    # 核心模型
    elif name == "BaseModel":
        from fastorm.model.base import BaseModel
        return BaseModel
    elif name == "Model":
        from fastorm.model.model import Model
        return Model
    elif name == "DeclarativeBase":
        from fastorm.model.declarative import DeclarativeBase
        return DeclarativeBase
    
    # 查询构建器
    elif name == "QueryBuilder":
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder
    
    # 数据库连接
    elif name == "Database":
        from fastorm.connection.database import Database
        return Database
    elif name == "Session":
        from fastorm.connection.session import Session
        return Session
    
    # 仓储模式
    elif name == "BaseRepository":
        from fastorm.repository.base import BaseRepository
        return BaseRepository
    
    # Schema系统
    elif name in ["FastORMSchema", "CreateSchema", "UpdateSchema", "ResponseSchema", "PaginatedResponseSchema"]:
        from fastorm.schema.base import (
            FastORMSchema,
            CreateSchema,
            UpdateSchema,
            ResponseSchema,
            PaginatedResponseSchema,
        )
        return locals()[name]
    
    elif name in ["SchemaFactory", "create_schema_from_model", "create_response_schema", "create_partial_schema"]:
        from fastorm.schema.factory import (
            SchemaFactory,
            create_schema_from_model,
            create_response_schema,
            create_partial_schema,
        )
        return locals()[name]
    
    # Pydantic 2.11 验证器
    elif name in ["field_validator_v2", "model_validator_v2", "computed_field", "field_serializer"]:
        from fastorm.schema.validators import (
            field_validator_v2,
            model_validator_v2,
            computed_field,
            field_serializer,
        )
        return locals()[name]
    
    # FastAPI集成
    elif name in ["get_session", "get_repository", "get_db", "Depends"]:
        from fastorm.fastapi.dependencies import (
            get_session,
            get_repository,
            get_db,
            Depends,
        )
        return locals()[name]
    
    elif name in ["create_lifespan", "database_lifespan"]:
        from fastorm.fastapi.lifespan import (
            create_lifespan,
            database_lifespan,
        )
        return locals()[name]
    
    elif name in ["create_crud_router", "CRUDRouter"]:
        from fastorm.fastapi.routing import (
            create_crud_router,
            CRUDRouter,
        )
        return locals()[name]
    
    # SQLAlchemy 2.0 类型
    elif name in ["Mapped", "mapped_column", "relationship", "ForeignKey", "Index", "UniqueConstraint", "CheckConstraint"]:
        from fastorm.types.sqlalchemy import (
            Mapped,
            mapped_column,
            relationship,
            ForeignKey,
            Index,
            UniqueConstraint,
            CheckConstraint,
        )
        return locals()[name]
    
    # Pydantic类型
    elif name in ["EmailStr", "HttpUrl", "UUID4", "Field", "ConfigDict", "BeforeValidator", "AfterValidator", "PlainValidator"]:
        from fastorm.types.pydantic import (
            EmailStr,
            HttpUrl,
            UUID4,
            Field,
            ConfigDict,
            BeforeValidator,
            AfterValidator,
            PlainValidator,
        )
        return locals()[name]
    
    # 高级特性
    elif name == "CacheManager":
        from fastorm.cache.manager import CacheManager
        return CacheManager
    elif name in ["cache_query", "invalidate_cache"]:
        from fastorm.cache.decorators import cache_query, invalidate_cache
        return locals()[name]
    
    elif name == "EventManager":
        from fastorm.events.manager import EventManager
        return EventManager
    elif name == "event_listener":
        from fastorm.events.decorators import event_listener
        return event_listener
    
    elif name == "BatchOperations":
        from fastorm.operations.batch import BatchOperations
        return BatchOperations
    
    elif name == "MigrationManager":
        from fastorm.migrations.manager import MigrationManager
        return MigrationManager
    
    # 异常
    elif name in ["FastORMError", "DatabaseError", "ValidationError", "RecordNotFoundError", 
                  "IntegrityError", "ConnectionError", "QueryError", "SchemaError", "ConfigurationError"]:
        from fastorm.exceptions.base import (
            FastORMError,
            DatabaseError,
            ValidationError,
            RecordNotFoundError,
            IntegrityError,
            ConnectionError,
            QueryError,
            SchemaError,
            ConfigurationError,
        )
        return locals()[name]
    
    # 工具函数
    elif name in ["to_snake_case", "to_camel_case", "get_table_name", "get_primary_key"]:
        from fastorm.utils.helpers import (
            to_snake_case,
            to_camel_case,
            get_table_name,
            get_primary_key,
        )
        return locals()[name]
    
    elif name in ["Pagination", "paginate_query"]:
        from fastorm.utils.pagination import (
            Pagination,
            paginate_query,
        )
        return locals()[name]
    
    # 配置
    elif name == "FastORMSettings":
        from fastorm.config.settings import FastORMSettings
        return FastORMSettings
    elif name == "config_manager":
        from fastorm.config.manager import config_manager
        return config_manager
    
    # 测试支持 (Stage 8)
    elif name in ["Factory", "trait", "LazyAttribute", "Sequence"]:
        from fastorm.testing.factory import Factory, trait, LazyAttribute, Sequence
        return locals()[name]
    elif name in ["Seeder", "DatabaseSeeder"]:
        from fastorm.testing.seeder import Seeder, DatabaseSeeder
        return locals()[name]
    elif name in ["TestCase", "DatabaseTestCase"]:
        from fastorm.testing.testcase import TestCase, DatabaseTestCase
        return locals()[name]
    elif name in ["faker", "ChineseProvider", "CompanyProvider", "TestDataProvider"]:
        from fastorm.testing.faker_providers import (
            faker, ChineseProvider, CompanyProvider, TestDataProvider
        )
        return locals()[name]
    
    # 性能监控 (Stage 9)
    elif name in ["QueryProfiler", "profile_query"]:
        from fastorm.performance.profiler import QueryProfiler, profile_query
        return locals()[name]
    elif name in ["PerformanceMonitor", "start_monitoring", "stop_monitoring"]:
        from fastorm.performance.monitor import (
            PerformanceMonitor, start_monitoring, stop_monitoring
        )
        return locals()[name]
    elif name == "N1Detector":
        from fastorm.performance.detector import N1Detector
        return N1Detector
    elif name in ["PerformanceReporter", "get_performance_stats", "print_performance_summary"]:
        from fastorm.performance.reporter import (
            PerformanceReporter, generate_report as get_performance_stats,
            print_performance_summary
        )
        return locals()[name] if name != "get_performance_stats" else get_performance_stats
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# =============================================================================
# 初始化函数
# =============================================================================

def init(
    database_url: Optional[str] = None,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    **kwargs: Any,
) -> None:
    """初始化FastORM
    
    Args:
        database_url: 数据库连接URL
        echo: 是否输出SQL日志
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出数量
        pool_timeout: 连接池超时时间（秒）
        pool_recycle: 连接回收时间（秒）
        **kwargs: 其他引擎配置参数
        
    Example:
        ```python
        import fastorm
        
        # 基础初始化
        fastorm.init("postgresql+asyncpg://user:pass@localhost/db")
        
        # 高级配置
        fastorm.init(
            "postgresql+asyncpg://user:pass@localhost/db",
            echo=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=60
        )
        ```
    """
    if database_url:
        # 延迟导入Database
        Database = __getattr__("Database")
        
        # 设置数据库连接
        engine_kwargs = {
            "echo": echo,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            **kwargs,
        }
        
        # 初始化数据库
        Database.init(database_url, **engine_kwargs)
        
        logger.info(f"FastORM {__version__} 初始化完成")
        logger.info(f"数据库: {database_url.split('://')[0]}")
        logger.info(f"连接池大小: {pool_size}, 最大溢出: {max_overflow}")
    else:
        logger.warning("未提供数据库URL，请手动配置数据库连接")


def setup_fastapi(
    app,
    *,
    database_url: Optional[str] = None,
    include_crud_routers: bool = True,
    include_exception_handlers: bool = True,
    **database_kwargs: Any,
) -> None:
    """为FastAPI应用配置FastORM
    
    Args:
        app: FastAPI应用实例
        database_url: 数据库连接URL
        include_crud_routers: 是否包含CRUD路由
        include_exception_handlers: 是否包含异常处理器
        **database_kwargs: 数据库配置参数
        
    Example:
        ```python
        from fastapi import FastAPI
        import fastorm
        
        app = FastAPI()
        
        fastorm.setup_fastapi(
            app,
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            include_crud_routers=True,
            include_exception_handlers=True
        )
        ```
    """
    # 检查FastAPI版本兼容性
    try:
        import fastapi
        if hasattr(fastapi, '__version__'):
            version = fastapi.__version__
            if version < "0.115.0":
                logger.warning(f"FastAPI版本 {version} 可能不完全兼容，建议升级到 0.115.12+")
    except ImportError:
        logger.warning("未安装FastAPI，某些功能可能不可用")
        return
    
    # 初始化数据库
    if database_url:
        init(database_url, **database_kwargs)
    
    # 配置生命周期
    if hasattr(app, 'router'):
        # FastAPI 0.115.12+ 生命周期配置
        create_lifespan = __getattr__("create_lifespan")
        lifespan = create_lifespan(database_url, **database_kwargs)
        if hasattr(app, 'lifespan_context'):
            app.lifespan_context = lifespan
        elif hasattr(app, 'lifespan'):
            app.lifespan = lifespan
    
    # 添加异常处理器
    if include_exception_handlers:
        try:
            from fastorm.fastapi.exception_handlers import add_exception_handlers
            add_exception_handlers(app)
        except ImportError:
            logger.warning("异常处理器模块不可用")
    
    # 添加CRUD路由（如果需要）
    if include_crud_routers:
        logger.info("CRUD路由器已准备就绪，使用 create_crud_router() 创建路由")
    
    logger.info(f"FastAPI应用已配置FastORM {__version__}")


# =============================================================================
# 类型检查支持
# =============================================================================

if TYPE_CHECKING:
    # 仅在类型检查时导入，避免循环导入
    from fastorm.model.base import BaseModel as _BaseModel
    from fastorm.query.builder import QueryBuilder as _QueryBuilder
    from fastorm.connection.database import Database as _Database
    from fastorm.repository.base import BaseRepository as _BaseRepository
    
    # 类型别名
    Model = _BaseModel
    Query = _QueryBuilder
    DB = _Database
    Repository = _BaseRepository

# =============================================================================
# 运行时特性检测
# =============================================================================

def _check_dependencies() -> Dict[str, bool]:
    """检查可选依赖的可用性"""
    features = {}
    
    # SQLAlchemy版本检查
    try:
        import sqlalchemy
        features['sqlalchemy'] = sqlalchemy.__version__ >= "2.0.40"
        if not features['sqlalchemy']:
            logger.warning(f"SQLAlchemy版本 {sqlalchemy.__version__} 低于推荐版本 2.0.40")
    except ImportError:
        features['sqlalchemy'] = False
        logger.error("SQLAlchemy未安装")
    
    # Pydantic版本检查
    try:
        import pydantic
        features['pydantic'] = pydantic.__version__ >= "2.11.0"
        if not features['pydantic']:
            logger.warning(f"Pydantic版本 {pydantic.__version__} 低于推荐版本 2.11.0")
    except ImportError:
        features['pydantic'] = False
        logger.error("Pydantic未安装")
    
    # FastAPI检查
    try:
        import fastapi
        features['fastapi'] = hasattr(fastapi, '__version__') and fastapi.__version__ >= "0.115.12"
    except ImportError:
        features['fastapi'] = False
    
    # 数据库驱动检查
    for driver in ['asyncpg', 'aiomysql', 'aiosqlite']:
        try:
            __import__(driver)
            features[driver] = True
        except ImportError:
            features[driver] = False
    
    # 缓存支持检查
    try:
        import redis
        features['redis'] = True
    except ImportError:
        features['redis'] = False
    
    return features


# 启动时检查依赖
_FEATURES = _check_dependencies()

# 如果基础依赖不满足，发出警告
if not _FEATURES.get('sqlalchemy', False):
    logger.error("SQLAlchemy 2.0.40+ 是FastORM的必需依赖")
if not _FEATURES.get('pydantic', False):
    logger.error("Pydantic 2.11+ 是FastORM的必需依赖")

logger.info(f"FastORM {__version__} 已加载")
logger.debug(f"可用特性: {_FEATURES}") 