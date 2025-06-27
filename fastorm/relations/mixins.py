"""
FastORM 关系管理 Mixin

为模型添加关系管理功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from .base import Relation
from .belongs_to import BelongsTo
from .belongs_to_many import BelongsToMany
from .has_many import HasMany
from .has_one import HasOne
from .loader import RelationLoader
from .loader import RelationProxy

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RelationProxy:
    """关系代理类

    提供延迟加载和便捷方法。
    """

    def __init__(self, relation: Relation[Any], parent: Any):
        """初始化关系代理

        Args:
            relation: 关系对象
            parent: 父模型实例
        """
        self._relation = relation
        self._parent = parent
        self._loaded_data: Any | None = None
        self._is_loaded = False

    async def load(self) -> Any:
        """加载关系数据"""
        from fastorm.core.session_manager import execute_with_session

        async def _load(session: AsyncSession) -> Any:
            data = await self._relation.load(self._parent, session)
            self._loaded_data = data
            self._is_loaded = True
            return data

        return await execute_with_session(_load)

    async def create(self, **attributes: Any) -> Any:
        """通过关系创建新记录"""
        return await self._relation.create(self._parent, **attributes)

    async def save(self, instance: Any) -> Any:
        """保存关联模型实例"""
        return await self._relation.save(self._parent, instance)

    async def count(self) -> int:
        """统计关联记录数量"""
        return await self._relation.count(self._parent)

    # 多对多关系的方法
    async def attach(self, ids: Any, pivot_data: dict[str, Any] | None = None) -> None:
        """附加关联记录（多对多）"""
        if hasattr(self._relation, "attach"):
            return await self._relation.attach(self._parent, ids, pivot_data)
        raise AttributeError(f"Relation {type(self._relation)} does not support attach")

    async def detach(self, ids: Any | None = None) -> None:
        """分离关联记录（多对多）"""
        if hasattr(self._relation, "detach"):
            return await self._relation.detach(self._parent, ids)
        raise AttributeError(f"Relation {type(self._relation)} does not support detach")

    async def sync(
        self, ids: list[Any], pivot_data: dict[str, Any] | None = None
    ) -> None:
        """同步关联记录（多对多）"""
        if hasattr(self._relation, "sync"):
            return await self._relation.sync(self._parent, ids, pivot_data)
        raise AttributeError(f"Relation {type(self._relation)} does not support sync")

    async def toggle(
        self, ids: Any, pivot_data: dict[str, Any] | None = None
    ) -> dict[str, list[int]]:
        """切换关联状态（多对多）"""
        if hasattr(self._relation, "toggle"):
            return await self._relation.toggle(self._parent, ids, pivot_data)
        raise AttributeError(f"Relation {type(self._relation)} does not support toggle")

    @property
    def is_loaded(self) -> bool:
        """是否已加载"""
        return self._is_loaded

    @property
    def data(self) -> Any:
        """获取已加载的数据"""
        return self._loaded_data


class RelationMixin:
    """关系管理混入类

    为模型添加Eloquent风格的关系管理功能。

    示例：
    ```python
    class User(Model, RelationMixin):
        # 定义关系
        profile = HasOne('Profile')
        posts = HasMany('Post')
        roles = BelongsToMany('Role', pivot_table='user_roles')

    # 使用关系
    user = await User.find(1)
    profile = await user.profile  # 自动加载
    posts = await user.posts  # 自动加载
    ```
    """

    # 关系定义存储
    __relations__: ClassVar[dict[str, Relation]] = {}

    def __init_subclass__(cls, **kwargs):
        """子类初始化时自动处理关系定义"""
        super().__init_subclass__(**kwargs)

        # 收集关系定义
        cls._relations = {}
        for name, value in cls.__dict__.items():
            # 检查是否是关系对象，避免触发model_class的getter
            if isinstance(value, Relation):
                # 这是一个关系对象
                cls._relations[name] = value

        # 自动发现类属性中的关系定义
        cls._discover_relations()

    @classmethod
    def _discover_relations(cls):
        """自动发现关系定义"""
        for name in dir(cls):
            if not name.startswith("_"):
                attr = getattr(cls, name)
                if isinstance(attr, Relation):
                    cls.__relations__[name] = attr
                    # 将关系属性转换为属性访问器
                    setattr(cls, name, cls._create_relation_property(name, attr))

    @classmethod
    def _create_relation_property(cls, name: str, relation: Relation):
        """创建关系属性访问器"""

        def getter(self) -> RelationProxy:
            # 检查是否已有缓存的代理
            proxy_attr = f"_{name}_proxy"
            if not hasattr(self, proxy_attr):
                setattr(self, proxy_attr, RelationProxy(relation, self))
            return getattr(self, proxy_attr)

        return property(getter)

    @classmethod
    def has_one(
        cls,
        model_class: type[Any],
        foreign_key: str | None = None,
        local_key: str = "id",
    ) -> HasOne:
        """定义HasOne关系

        Args:
            model_class: 关联的模型类
            foreign_key: 外键名
            local_key: 本地键名

        Returns:
            HasOne关系实例
        """
        return HasOne(model_class, foreign_key, local_key)

    @classmethod
    def belongs_to(
        cls,
        model_class: type[Any],
        foreign_key: str | None = None,
        local_key: str = "id",
    ) -> BelongsTo:
        """定义BelongsTo关系

        Args:
            model_class: 关联的模型类
            foreign_key: 外键名
            local_key: 本地键名

        Returns:
            BelongsTo关系实例
        """
        return BelongsTo(model_class, foreign_key, local_key)

    @classmethod
    def has_many(
        cls,
        model_class: type[Any],
        foreign_key: str | None = None,
        local_key: str = "id",
    ) -> HasMany:
        """定义HasMany关系

        Args:
            model_class: 关联的模型类
            foreign_key: 外键名
            local_key: 本地键名

        Returns:
            HasMany关系实例
        """
        return HasMany(model_class, foreign_key, local_key)

    @classmethod
    def belongs_to_many(
        cls,
        model_class: type[Any],
        pivot_table: str | None = None,
        foreign_key: str | None = None,
        related_key: str | None = None,
        local_key: str = "id",
        related_local_key: str = "id",
    ) -> BelongsToMany:
        """定义BelongsToMany关系

        Args:
            model_class: 关联的模型类
            pivot_table: 中间表名
            foreign_key: 当前模型外键名
            related_key: 关联模型外键名
            local_key: 当前模型本地键名
            related_local_key: 关联模型本地键名

        Returns:
            BelongsToMany关系实例
        """
        return BelongsToMany(
            model_class,
            pivot_table,
            foreign_key,
            related_key,
            local_key,
            related_local_key,
        )

    @classmethod
    def get_relations(cls) -> dict[str, Relation]:
        """获取所有关系定义

        Returns:
            关系字典
        """
        return cls.__relations__.copy()

    def get_relation(self, name: str) -> Relation | None:
        """获取指定关系

        Args:
            name: 关系名称

        Returns:
            关系实例，如果不存在则返回None
        """
        return self.__relations__.get(name)

    def has_relation(self, name: str) -> bool:
        """检查是否有指定关系

        Args:
            name: 关系名称

        Returns:
            如果有关系返回True，否则返回False
        """
        return name in self.__relations__

    def is_relation_loaded(self, name: str) -> bool:
        """检查关系是否已加载

        Args:
            name: 关系名称

        Returns:
            如果关系已加载返回True，否则返回False
        """
        return RelationLoader.is_relation_loaded(self, name)

    def clear_relation_cache(self, name: str = None) -> None:
        """清空关系缓存

        Args:
            name: 关系名称，如果为None则清空所有关系缓存
        """
        RelationLoader.clear_relation_cache(self, name)

        # 同时清空代理缓存
        if name:
            proxy_attr = f"_{name}_proxy"
            if hasattr(self, proxy_attr):
                delattr(self, proxy_attr)
        else:
            # 清空所有代理缓存
            attrs_to_remove = []
            for attr_name in dir(self):
                if attr_name.endswith("_proxy") and attr_name.startswith("_"):
                    if not attr_name.startswith("__"):
                        attrs_to_remove.append(attr_name)

            for attr_name in attrs_to_remove:
                if hasattr(self, attr_name):
                    delattr(self, attr_name)

    async def load_relations(self, *relation_names: str) -> dict[str, Any]:
        """批量加载指定关系

        Args:
            *relation_names: 关系名称列表

        Returns:
            关系数据字典
        """
        if not relation_names:
            # 如果没有指定关系名，加载所有关系
            relation_names = tuple(self.__relations__.keys())

        # 构建关系字典
        relations = {
            name: relation
            for name, relation in self.__relations__.items()
            if name in relation_names
        }

        # 使用session管理器加载关系
        from fastorm.core.session_manager import execute_with_session

        async def _load_relations(session):
            return await RelationLoader.load_relations(self, relations, session)

        return await execute_with_session(_load_relations)

    def __getattribute__(self, name: str) -> Any:
        """重写属性访问，为关系返回代理对象"""
        # 首先尝试正常的属性访问
        try:
            attr = super().__getattribute__(name)

            # 检查是否是关系对象
            if hasattr(attr, "model_class") and hasattr(attr, "load"):
                # 返回关系代理
                return RelationProxy(attr, self)

            return attr
        except AttributeError:
            # 如果属性不存在，继续正常的异常流程
            raise

    def get_relations(self) -> dict[str, Any]:
        """获取所有关系定义"""
        return getattr(self.__class__, "_relations", {})
