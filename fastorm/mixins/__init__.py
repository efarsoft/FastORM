"""
FastORM Mixins - 优雅的模型特性

提供Eloquent风格的模型混入特性：
- TimestampMixin: 自动时间戳管理
- SoftDeleteMixin: 软删除功能
- FillableMixin: 批量赋值控制
- EventMixin: 模型事件系统
- PydanticIntegrationMixin: Pydantic V2深度集成
"""

from .timestamps import TimestampMixin
from .soft_delete import SoftDeleteMixin
from .fillable import FillableMixin
from .events import EventMixin
from .pydantic_integration import PydanticIntegrationMixin

__all__ = [
    'TimestampMixin',
    'SoftDeleteMixin', 
    'FillableMixin',
    'EventMixin',
    'PydanticIntegrationMixin',
] 