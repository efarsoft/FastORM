"""
FastORM 关系管理模块

提供Eloquent风格的模型关系管理功能。

支持的关系类型：
- HasOne: 一对一关系（拥有）
- BelongsTo: 一对一关系（属于）
- HasMany: 一对多关系
- BelongsToMany: 多对多关系

特性：
- 简洁的关系定义
- 自动预加载
- 延迟加载支持
- 链式查询集成
"""

from .base import Relation
from .has_one import HasOne
from .belongs_to import BelongsTo
from .has_many import HasMany
from .belongs_to_many import BelongsToMany
from .loader import RelationLoader
from .mixins import RelationMixin

__all__ = [
    'Relation',
    'HasOne',
    'BelongsTo', 
    'HasMany',
    'BelongsToMany',
    'RelationLoader',
    'RelationMixin',
] 