"""
FastORM 模型

实现真正简洁如ThinkORM的API。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from sqlalchemy import Integer, DateTime
from sqlalchemy import MetaData
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase as SQLAlchemyDeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import mapped_column

from fastorm.core.session_manager import execute_with_session
from fastorm.mixins.events import EventMixin
from fastorm.mixins.pydantic_integration import PydanticIntegrationMixin
from fastorm.mixins.scopes import ScopeMixin
from fastorm.mixins.scopes import create_scoped_query

if TYPE_CHECKING:
    from fastorm.query.builder import QueryBuilder

T = TypeVar("T", bound="Model")


class DeclarativeBase(SQLAlchemyDeclarativeBase):
    """SQLAlchemy 2.0 声明式基类

    使用最新的SQLAlchemy 2.0特性：
    - 🔧 优化的元数据配置
    - 🚀 编译缓存支持
    - 📊 查询计划缓存
    """

    # SQLAlchemy 2.0.40+ 元数据优化
    metadata = MetaData(
        # 启用编译缓存以提升性能
        info={
            "compiled_cache": {},
            "render_postcompile": True,
        }
    )


class Model(DeclarativeBase, EventMixin, PydanticIntegrationMixin, ScopeMixin):
    """FastORM模型基类

    实现真正简洁的API，无需手动管理session，自动集成事件系统和Pydantic V2验证。
    内置时间戳管理功能，支持全局配置和自定义。

    示例:
    ```python
    # 🎯 简洁如ThinkORM + 事件支持 + Pydantic验证 + 自动时间戳
    user = await User.create(name='John', email='john@example.com')
    users = await User.where('age', '>', 18).limit(10).get()
    await user.update(name='Jane')  # 自动更新 updated_at
    await user.delete()

    # 时间戳配置
    class User(Model):
        timestamps = True  # 启用时间戳（默认False）
        created_at_column = "created_time"  # 自定义字段名
        updated_at_column = "updated_time"  # 自定义字段名

    # 全局关闭时间戳
    Model.set_global_timestamps(False)
    ```
    """

    __abstract__ = True

    # =================================================================
    # 时间戳配置 - 内置到Model基类中
    # =================================================================

    # 全局时间戳开关（由配置系统控制）
    @classmethod
    def _get_global_timestamps_enabled(cls) -> bool:
        """获取全局时间戳配置状态"""
        try:
            from fastorm.config import get_setting
            return get_setting('timestamps_enabled', True)
        except ImportError:
            # 如果配置系统不可用，使用默认值
            return True

    # 模型级配置（默认启用，简化配置）
    timestamps: ClassVar[bool] = True

    # 时间戳字段名配置（可在子类中自定义）
    created_at_column: ClassVar[str] = "created_at"
    updated_at_column: ClassVar[str] = "updated_at"

    @classmethod
    def set_global_timestamps(cls, enabled: bool) -> None:
        """全局设置时间戳功能
        
        Args:
            enabled: 是否启用时间戳功能
            
        Example:
            # 全局关闭时间戳
            Model.set_global_timestamps(False)
            
            # 全局启用时间戳
            Model.set_global_timestamps(True)
        """
        try:
            from fastorm.config import set_setting
            set_setting('timestamps_enabled', enabled)
        except ImportError:
            # 如果配置系统不可用，暂时存储在类属性中
            cls._fallback_timestamps_enabled = enabled

    @classmethod
    def is_timestamps_enabled(cls) -> bool:
        """检查当前模型是否启用时间戳
        
        Returns:
            如果全局启用且模型启用则返回True
        """
        global_enabled = cls._get_global_timestamps_enabled()
        return global_enabled and cls.timestamps

    @declared_attr
    def created_at(cls):
        """创建时间字段 - 自动添加到启用时间戳的模型中"""
        # 检查是否需要时间戳字段
        global_enabled = cls._get_global_timestamps_enabled()
        if (global_enabled and 
            hasattr(cls, 'timestamps') and 
            cls.timestamps):
            return mapped_column(
                DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),
                nullable=True,
                name=cls.created_at_column,
                comment="创建时间",
            )
        return None

    @declared_attr  
    def updated_at(cls):
        """更新时间字段 - 自动添加到启用时间戳的模型中"""
        # 检查是否需要时间戳字段
        global_enabled = cls._get_global_timestamps_enabled()
        if (global_enabled and 
            hasattr(cls, 'timestamps') and 
            cls.timestamps):
            return mapped_column(
                DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),
                onupdate=lambda: datetime.now(timezone.utc),
                nullable=True,
                name=cls.updated_at_column,
                comment="更新时间",
            )
        return None

    def touch(self) -> None:
        """手动更新时间戳
        
        更新 updated_at 为当前时间，不触发其他字段更新。
        
        Example:
            await user.touch()
            await user.save()
        """
        if self.is_timestamps_enabled():
            setattr(self, self.updated_at_column, datetime.now(timezone.utc))

    def get_created_at(self) -> datetime | None:
        """获取创建时间
        
        Returns:
            创建时间，如果未设置或未启用时间戳则返回None
        """
        if not self.is_timestamps_enabled():
            return None
        return getattr(self, self.created_at_column, None)

    def get_updated_at(self) -> datetime | None:
        """获取更新时间
        
        Returns:
            更新时间，如果未设置或未启用时间戳则返回None
        """
        if not self.is_timestamps_enabled():
            return None
        return getattr(self, self.updated_at_column, None)

    def set_created_at(self, value: datetime | None) -> None:
        """设置创建时间
        
        Args:
            value: 创建时间
        """
        if self.is_timestamps_enabled():
            setattr(self, self.created_at_column, value)

    def set_updated_at(self, value: datetime | None) -> None:
        """设置更新时间
        
        Args:
            value: 更新时间
        """
        if self.is_timestamps_enabled():
            setattr(self, self.updated_at_column, value)

    def _before_create_timestamp(self) -> None:
        """创建前的时间戳处理 - 内部方法"""
        if not self.is_timestamps_enabled():
            return

        now = datetime.now(timezone.utc)

        # 设置创建时间（如果未设置）
        if not self.get_created_at():
            self.set_created_at(now)

        # 设置更新时间（如果未设置）
        if not self.get_updated_at():
            self.set_updated_at(now)

    def _before_update_timestamp(self) -> None:
        """更新前的时间戳处理 - 内部方法"""
        if not self.is_timestamps_enabled():
            return

        # 自动更新 updated_at
        self.set_updated_at(datetime.now(timezone.utc))

    # 通用主键字段（子类可以覆盖）
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(Integer, primary_key=True, autoincrement=True)

    # =================================================================
    # 简洁的创建和查询方法
    # =================================================================

    @classmethod
    async def create(cls: type[T], **values: Any) -> T:
        """创建新记录 - 无需session参数，自动触发事件！自动使用写库

        Args:
            **values: 字段值

        Returns:
            创建的模型实例

        Example:
            user = await User.create(name='John', email='john@example.com')
        """

        async def _create(session: AsyncSession) -> T:
            instance = cls(**values)

            # 处理时间戳（在事件之前）
            instance._before_create_timestamp()

            # 触发 before_insert 事件
            await instance.fire_event("before_insert")

            session.add(instance)
            await session.flush()
            await session.refresh(instance)

            # 触发 after_insert 事件
            await instance.fire_event("after_insert")

            # 在记录创建完成后保存其状态作为原始状态
            instance._reset_original_state()

            return instance

        # 创建操作使用写库
        return await execute_with_session(_create, connection_type="write")

    @classmethod
    async def find(cls: type[T], id: Any, *, force_write: bool = False) -> T | None:
        """通过主键查找记录 - 无需session参数！自动使用读库

        Args:
            id: 主键值
            force_write: 强制使用写库（用于读自己的写等场景）

        Returns:
            模型实例或None

        Example:
            user = await User.find(1)  # 使用读库
            user = await User.find(1, force_write=True)  # 强制使用写库
        """

        async def _find(session: AsyncSession) -> T | None:
            return await session.get(cls, id)

        connection_type = "write" if force_write else "read"
        return await execute_with_session(_find, connection_type=connection_type)

    @classmethod
    async def find_or_fail(cls: type[T], id: Any) -> T:
        """通过主键查找记录，不存在则抛出异常 - 无需session参数！

        Args:
            id: 主键值

        Returns:
            模型实例

        Raises:
            ValueError: 记录不存在

        Example:
            user = await User.find_or_fail(1)
        """

        async def _find_or_fail(session: AsyncSession) -> T:
            instance = await session.get(cls, id)
            if instance is None:
                raise ValueError(f"{cls.__name__} with id {id} not found")
            return instance

        return await execute_with_session(_find_or_fail)

    @classmethod
    async def all(cls: type[T]) -> list[T]:
        """获取所有记录 - 无需session参数！使用读库

        Returns:
            所有记录列表

        Example:
            users = await User.all()
        """

        async def _all(session: AsyncSession) -> list[T]:
            result = await session.execute(select(cls))
            return list(result.scalars().all())

        return await execute_with_session(_all, connection_type="read")

    @classmethod
    async def count(cls: type[T]) -> int:
        """统计记录数量 - 无需session参数！使用读库

        Returns:
            记录数量

        Example:
            count = await User.count()
        """

        async def _count(session: AsyncSession) -> int:
            result = await session.execute(select(func.count()).select_from(cls))
            return result.scalar() or 0

        return await execute_with_session(_count, connection_type="read")

    # =================================================================
    # 便捷的查询方法
    # =================================================================

    @classmethod
    async def first(cls: type[T]) -> T | None:
        """获取第一条记录，使用读库

        Returns:
            第一条记录或None

        Example:
            user = await User.first()
        """

        async def _first(session: AsyncSession) -> T | None:
            result = await session.execute(select(cls).limit(1))
            return result.scalars().first()

        return await execute_with_session(_first, connection_type="read")

    @classmethod
    async def last(cls: type[T]) -> T | None:
        """获取最后一条记录，使用读库

        Returns:
            最后一条记录或None

        Example:
            user = await User.last()
        """

        async def _last(session: AsyncSession) -> T | None:
            # 假设有id字段作为主键，尝试获取
            try:
                result = await session.execute(
                    select(cls).order_by(cls.id.desc()).limit(1)  # type: ignore
                )
                return result.scalars().first()
            except AttributeError:
                # 如果没有id字段，获取最后插入的记录
                result = await session.execute(select(cls))
                records = list(result.scalars().all())
                return records[-1] if records else None

        return await execute_with_session(_last, connection_type="read")

    # =================================================================
    # 便捷的批量操作
    # =================================================================

    @classmethod
    async def create_many(cls: type[T], records: list[dict[str, Any]]) -> list[T]:
        """批量创建记录

        Args:
            records: 记录数据列表

        Returns:
            创建的模型实例列表

        Example:
            users = await User.create_many([
                {'name': 'John', 'email': 'john@example.com'},
                {'name': 'Jane', 'email': 'jane@example.com'}
            ])
        """

        async def _create_many(session: AsyncSession) -> list[T]:
            instances = [cls(**record) for record in records]
            session.add_all(instances)
            await session.flush()
            for instance in instances:
                await session.refresh(instance)
            return instances

        return await execute_with_session(_create_many)

    @classmethod
    async def delete_where(cls: type[T], column: str, value: Any) -> int:
        """删除符合条件的记录

        Args:
            column: 列名
            value: 值

        Returns:
            删除的记录数量

        Example:
            count = await User.delete_where('age', 0)
        """

        async def _delete_where(session: AsyncSession) -> int:
            column_attr = getattr(cls, column)
            result = await session.execute(delete(cls).where(column_attr == value))
            return result.rowcount or 0

        return await execute_with_session(_delete_where)

    @classmethod
    async def count_where(cls: type[T], column: str, value: Any) -> int:
        """统计符合条件的记录数量，使用读库

        Args:
            column: 列名
            value: 值

        Returns:
            记录数量

        Example:
            count = await User.count_where('status', 'active')
        """

        async def _count_where(session: AsyncSession) -> int:
            column_attr = getattr(cls, column)
            result = await session.execute(
                select(func.count()).select_from(cls).where(column_attr == value)
            )
            return result.scalar() or 0

        return await execute_with_session(_count_where)

    # =================================================================
    # 实例方法 - 简洁的更新和删除
    # =================================================================

    async def save(self) -> None:
        """保存当前实例 - 无需session参数，自动触发事件！

        Example:
            user.name = 'Jane'
            await user.save()
        """

        async def _save(session: AsyncSession) -> None:
            # 保存原始状态用于事件和脏检查
            self._save_original_state()

            # 判断是新增还是更新
            is_new = self.is_new_record()

            if is_new:
                # 新增记录 - 处理时间戳
                self._before_create_timestamp()
                await self.fire_event("before_insert")
                session.add(self)
                await session.flush()
                await session.refresh(self)
                await self.fire_event("after_insert")
            else:
                # 更新记录 - 处理时间戳
                self._before_update_timestamp()
                await self.fire_event("before_update")
                session.add(self)
                await session.flush()
                await self.fire_event("after_update")

            # 重置状态标志，为下次保存做准备
            self._reset_original_state()

        await execute_with_session(_save)

    async def delete(self) -> None:
        """删除当前实例 - 无需session参数，自动触发事件！

        Example:
            await user.delete()
        """

        async def _delete(session: AsyncSession) -> None:
            # 触发 before_delete 事件
            await self.fire_event("before_delete")

            await session.delete(self)
            await session.flush()

            # 触发 after_delete 事件
            await self.fire_event("after_delete")

        await execute_with_session(_delete)

    async def update(self, **values: Any) -> None:
        """更新当前实例 - 无需session参数，自动触发事件！自动更新时间戳

        Args:
            **values: 要更新的字段值

        Example:
            await user.update(name='Jane', email='jane@example.com')
        """
        # 保存原始状态
        self._save_original_state()

        # 更新字段值
        for key, value in values.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # 直接保存，由save()方法统一处理事件触发和时间戳
        await self.save()

    async def refresh(self) -> None:
        """刷新当前实例数据

        Example:
            await user.refresh()
        """

        async def _refresh(session: AsyncSession) -> None:
            await session.refresh(self)

        await execute_with_session(_refresh)

    # =================================================================
    # 链式查询构建器
    # =================================================================

    @classmethod
    def where(
        cls: type[T], column: str, operator: str | Any = "=", value: Any = None
    ) -> QueryBuilder[T]:
        """开始构建查询 - 支持操作符

        Args:
            column: 列名
            operator: 操作符或值（如果省略value）
            value: 值

        Returns:
            查询构建器

        Example:
            users = await User.where('age', '>', 18).get()
            users = await User.where('name', 'John').get()
        """
        from fastorm.query.builder import QueryBuilder

        # 处理参数重载
        if value is None:
            # where('name', 'John') 形式
            actual_operator = "="
            actual_value = operator
        else:
            # where('age', '>', 18) 形式
            actual_operator = operator
            actual_value = value

        return QueryBuilder(cls).where(column, actual_operator, actual_value)

    @classmethod
    def query(cls: type[T]) -> QueryBuilder[T]:
        """创建作用域查询构建器

        Returns:
            作用域查询构建器实例（自动应用全局作用域）

        Example:
            # 基础查询
            users = await User.query().where('age', '>', 18).get()

            # 使用作用域
            active_users = await User.query().active().get()

            # 移除全局作用域
            all_users = await User.query().without_global_scopes().get()
        """
        return create_scoped_query(cls)

    def to_dict(self, exclude: list[str] | None = None) -> dict[str, Any]:
        """转换为字典

        Args:
            exclude: 要排除的字段列表

        Returns:
            字典表示
        """
        exclude = exclude or []
        result = {}

        if hasattr(self, "__table__"):
            for column in self.__table__.columns:
                if column.name not in exclude:
                    value = getattr(self, column.name)
                    # 处理日期时间类型
                    if hasattr(value, "isoformat"):
                        value = value.isoformat()
                    result[column.name] = value

        return result
