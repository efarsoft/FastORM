"""
FastORM - 专为FastAPI优化的现代异步ORM框架

FastORM = FastAPI + SQLAlchemy 2.0 + Pydantic 2.11 的完美融合
简洁如ThinkORM，优雅如Eloquent，现代如FastAPI

Version: 0.1.0
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
from fastorm import Model, Database
from sqlalchemy.orm import Mapped, mapped_column

class User(Model):
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
__version__ = "0.1.0"
__author__ = "FastORM Team"
__email__ = "team@fastorm.dev"
__license__ = "MIT"
__homepage__ = "https://fastorm.dev"
__repository__ = "https://github.com/fastorm/fastorm"

# 配置日志
logger = logging.getLogger("fastorm")

# =============================================================================
# 主要导出API - 只导出确实存在的组件
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
    "Model",
    "DeclarativeBase",
    
    # 查询与数据库
    "QueryBuilder", 
    "Database",
    "Session",
    
    # 缓存支持
    "CacheableModel",
    
    # 模型混入 (Mixins) - TimestampMixin已集成到Model基类中
    "SoftDeleteMixin", 
    "EventMixin",
    "FillableMixin",
    "PydanticIntegrationMixin",
    "ScopeMixin",
    
    # 验证系统增强 (Stage 14)
    "ValidationEngine", 
    "ValidationContext",
    "field_validator",
    "model_validator", 
    "ValidationInfo",
    "validate_field",
    "validate_model",
    "async_validator",
    "FieldValidatorRegistry",
    "ModelValidatorRegistry",
    "ValidationRuleRegistry",
    "ValidationError",
    "FieldValidationError", 
    "ModelValidationError",
    
    # 序列化系统增强 (Stage 14)
    "SerializationEngine",
    "SerializationContext", 
    "SerializationConfig",
    "BaseSerializer",
    "ModelSerializer",
    "FieldSerializer", 
    "RelationSerializer",
    "SerializerRegistry",
    "SerializerChain",
    "SerializationField",
    "FieldConfig",
    "FieldMapping", 
    "FieldTransformer",
    "JSONFormatter",
    "XMLFormatter",
    "CSVFormatter",
    "FormatterRegistry",
    "serialize_field",
    "serialize_model",
    "serialize_relation", 
    "custom_serializer",
    "format_as_json",
    "format_as_xml",
    "format_as_csv",
    "SerializationError",
    "FieldSerializationError", 
    "RelationSerializationError",
    
    # 批量操作增强 (Stage 14)
    "BatchEngine",
    "BatchContext",
    "BatchConfig",
    "BatchInsert",
    "BatchUpdate",
    "BatchDelete",
    "BatchUpsert",
    "BatchOperation",
    "BatchError",
    "BatchValidationError",
    "BatchTransactionError",
    
    # 测试支持 (Stage 8)
    "Factory",
    "trait", 
    "LazyAttribute",
    "Sequence",
    "Seeder",
    "DatabaseSeeder",
    "TestCase",
    "DatabaseTestCase", 
    "faker",
    "ChineseProvider",
    "CompanyProvider",
    "TestDataProvider",
    
    # 性能监控 (Stage 9)
    "QueryProfiler",
    "PerformanceMonitor",
    "N1Detector",
    "PerformanceReporter",
    "profile_query",
    "start_monitoring",
    "stop_monitoring", 
    "get_performance_stats",
    "print_performance_summary",
    
    # 配置系统
    "FastORMConfig",
    "ConfigManager", 
    "get_config",
    "set_config",
    "get_setting",
    "set_setting",
    "generate_config_file",
    "validate_config",
    
    # 初始化函数
    "init",
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
    elif name == "Model":
        from fastorm.model.model import Model
        return Model
    elif name == "DeclarativeBase":
        from fastorm.model.model import DeclarativeBase
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
    
    # 缓存支持
    elif name == "CacheableModel":
        from fastorm.model.cacheable import CacheableModel
        return CacheableModel
    
    # 模型混入 (Mixins) - TimestampMixin已集成到Model基类中
    elif name == "SoftDeleteMixin":
        from fastorm.mixins.soft_delete import SoftDeleteMixin
        return SoftDeleteMixin
    elif name == "EventMixin":
        from fastorm.mixins.events import EventMixin
        return EventMixin
    elif name == "FillableMixin":
        from fastorm.mixins.fillable import FillableMixin
        return FillableMixin
    elif name == "PydanticIntegrationMixin":
        from fastorm.mixins.pydantic_integration import PydanticIntegrationMixin
        return PydanticIntegrationMixin
    elif name == "ScopeMixin":
        from fastorm.mixins.scopes import ScopeMixin
        return ScopeMixin
    
    # 验证系统增强 (Stage 14)
    elif name in ["ValidationEngine", "ValidationContext"]:
        from fastorm.validation.engine import ValidationEngine, ValidationContext
        return locals()[name]
    elif name in ["field_validator", "model_validator", "ValidationInfo"]:
        from fastorm.validation import field_validator, model_validator, ValidationInfo
        return locals()[name]
    elif name in ["validate_field", "validate_model", "async_validator"]:
        from fastorm.validation import validate_field, validate_model, async_validator
        return locals()[name]
    elif name in ["FieldValidatorRegistry", "ModelValidatorRegistry"]:
        from fastorm.validation import FieldValidatorRegistry, ModelValidatorRegistry
        return locals()[name]
    elif name == "ValidationRuleRegistry":
        from fastorm.validation.rules import ValidationRuleRegistry
        return ValidationRuleRegistry
    elif name in ["ValidationError", "FieldValidationError", "ModelValidationError"]:
        from fastorm.validation import ValidationError, FieldValidationError, ModelValidationError
        return locals()[name]
    
    # 序列化系统增强 (Stage 14)
    elif name in ["SerializationEngine", "SerializationContext", "SerializationConfig"]:
        from fastorm.serialization import SerializationEngine, SerializationContext, SerializationConfig
        return locals()[name]
    elif name in ["BaseSerializer", "ModelSerializer", "FieldSerializer", "RelationSerializer"]:
        from fastorm.serialization import BaseSerializer, ModelSerializer, FieldSerializer, RelationSerializer
        return locals()[name]
    elif name in ["SerializerRegistry", "SerializerChain"]:
        from fastorm.serialization import SerializerRegistry, SerializerChain
        return locals()[name]
    elif name in ["SerializationField", "FieldConfig", "FieldMapping", "FieldTransformer"]:
        from fastorm.serialization import SerializationField, FieldConfig, FieldMapping, FieldTransformer
        return locals()[name]
    elif name in ["JSONFormatter", "XMLFormatter", "CSVFormatter", "FormatterRegistry"]:
        from fastorm.serialization import JSONFormatter, XMLFormatter, CSVFormatter, FormatterRegistry
        return locals()[name]
    elif name in ["serialize_field", "serialize_model", "serialize_relation", "custom_serializer"]:
        from fastorm.serialization import serialize_field, serialize_model, serialize_relation, custom_serializer
        return locals()[name]
    elif name in ["format_as_json", "format_as_xml", "format_as_csv"]:
        from fastorm.serialization.formatters import format_as_json, format_as_xml, format_as_csv
        return locals()[name]
    elif name in ["SerializationError", "FieldSerializationError", "RelationSerializationError"]:
        from fastorm.serialization import SerializationError, FieldSerializationError, RelationSerializationError
        return locals()[name]
    
    # 批量操作增强 (Stage 14)
    elif name in ["BatchEngine", "BatchContext", "BatchConfig"]:
        from fastorm.query.batch import BatchEngine, BatchContext, BatchConfig
        return locals()[name]
    elif name in ["BatchInsert", "BatchUpdate", "BatchDelete", "BatchUpsert"]:
        from fastorm.query.batch import BatchInsert, BatchUpdate, BatchDelete, BatchUpsert
        return locals()[name]
    elif name == "BatchOperation":
        from fastorm.query.batch import BatchOperation
        return BatchOperation
    elif name in ["BatchError", "BatchValidationError", "BatchTransactionError"]:
        from fastorm.query.batch import BatchError, BatchValidationError, BatchTransactionError
        return locals()[name]
    
    # 测试支持 (Stage 8)
    elif name in ["Factory", "trait", "LazyAttribute", "Sequence"]:
        from fastorm.testing import Factory, trait, LazyAttribute, Sequence
        return locals()[name]
    elif name in ["Seeder", "DatabaseSeeder"]:
        from fastorm.testing import Seeder, DatabaseSeeder
        return locals()[name]
    elif name in ["TestCase", "DatabaseTestCase"]:
        from fastorm.testing import TestCase, DatabaseTestCase
        return locals()[name]
    elif name in ["faker", "ChineseProvider", "CompanyProvider", "TestDataProvider"]:
        from fastorm.testing import faker, ChineseProvider, CompanyProvider, TestDataProvider
        return locals()[name]
    
    # 性能监控 (Stage 9)
    elif name in ["QueryProfiler", "profile_query"]:
        from fastorm.performance import QueryProfiler, profile_query
        return locals()[name]
    elif name in ["PerformanceMonitor", "start_monitoring", "stop_monitoring"]:
        from fastorm.performance import PerformanceMonitor, start_monitoring, stop_monitoring
        return locals()[name]
    elif name == "N1Detector":
        from fastorm.performance import N1Detector
        return N1Detector
    elif name in ["PerformanceReporter", "get_performance_stats", "print_performance_summary"]:
        from fastorm.performance import PerformanceReporter, get_performance_stats, print_performance_summary
        return locals()[name]
    
    # 配置系统
    elif name in ["FastORMConfig", "ConfigManager"]:
        from fastorm.config import FastORMConfig, ConfigManager
        return locals()[name]
    elif name in ["get_config", "set_config", "get_setting", "set_setting"]:
        from fastorm.config import get_config, set_config, get_setting, set_setting
        return locals()[name]
    elif name in ["generate_config_file", "validate_config"]:
        from fastorm.config import generate_config_file, validate_config
        return locals()[name]
    
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
    """初始化FastORM数据库连接

    Args:
        database_url: 数据库连接URL
        echo: 是否打印SQL语句
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出
        pool_timeout: 连接超时时间
        pool_recycle: 连接回收时间
        **kwargs: 其他SQLAlchemy引擎参数

    Example:
        await init("postgresql+asyncpg://user:pass@localhost/db")
    """
    from fastorm.connection.database import Database
    
    return Database.init(
        database_url=database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        **kwargs,
    )


# =============================================================================
# 依赖检查
# =============================================================================

def _check_dependencies() -> Dict[str, bool]:
    """检查依赖包是否安装"""
    dependencies = {}
    
    try:
        import sqlalchemy
        dependencies["sqlalchemy"] = True
    except ImportError:
        dependencies["sqlalchemy"] = False
    
    try:
        import pydantic
        dependencies["pydantic"] = True
    except ImportError:
        dependencies["pydantic"] = False
    
    try:
        import fastapi
        dependencies["fastapi"] = True
    except ImportError:
        dependencies["fastapi"] = False
    
    return dependencies


if TYPE_CHECKING:
    # 仅在类型检查时导入，避免循环导入
    from fastorm.model.model import Model as _Model
    from fastorm.query.builder import QueryBuilder as _QueryBuilder
    from fastorm.connection.database import Database as _Database

logger.info(f"FastORM {__version__} 已加载")

from fastorm.serialization.fields import Field 

# 官方API自动生成器入口
from .api.crud import create_crud_router 