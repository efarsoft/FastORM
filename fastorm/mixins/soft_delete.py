"""
FastORM 软删除 Mixin

提供Eloquent风格的软删除功能。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar

from sqlalchemy import DateTime
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from fastorm.core.session_manager import execute_with_session


# 定义软删除全局作用域
def _soft_delete_global_scope(self, query):
    """软删除全局作用域：自动排除已删除记录"""
    if getattr(self.__class__, 'soft_delete', False):
        return query.where(f'{self.__class__.deleted_at_column}', None)
    return query


class SoftDeleteMixin:
    """软删除混入类

    提供Eloquent风格的软删除功能。

    特性：
    - 软删除：删除时设置 deleted_at 而不是物理删除
    - 自动过滤：查询时自动排除已删除记录
    - 恢复功能：可以恢复已删除的记录
    - 强制删除：支持物理删除

    示例：
    ```python
    class User(SoftDeleteMixin, Model):
        soft_delete = True  # 启用软删除

        name: Mapped[str]
        email: Mapped[str]

    user = await User.create(name='John')

    # 软删除
    await user.delete()  # 设置 deleted_at

    # 查询时自动排除已删除记录
    users = await User.all()  # 不包含已删除的用户

    # 包含已删除记录的查询
    all_users = await User.with_trashed().all()

    # 恢复已删除记录
    await user.restore()

    # 物理删除
    await user.force_delete()
    ```
    """

    def __init_subclass__(cls, **kwargs):
        """子类初始化时自动注册软删除全局作用域"""
        super().__init_subclass__(**kwargs)
        
        # 如果启用了软删除，注册全局作用域
        if getattr(cls, 'soft_delete', False):
            from fastorm.mixins.scopes import _scope_registry
            _scope_registry.register_global_scope(
                cls, 'soft_delete_filter', _soft_delete_global_scope
            )

    # =================================================================
    # 配置选项
    # =================================================================

    # 是否启用软删除（默认False，需要显式启用）
    soft_delete: ClassVar[bool] = False

    # 软删除字段名配置
    deleted_at_column: ClassVar[str] = "deleted_at"

    # =================================================================
    # 软删除字段定义
    # =================================================================

    # 删除时间 - 软删除时设置，恢复时清空
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="软删除时间"
    )

    # =================================================================
    # 软删除状态检查
    # =================================================================

    def is_deleted(self) -> bool:
        """检查记录是否已被软删除

        Returns:
            如果记录已被软删除返回True，否则返回False
        """
        return self.get_deleted_at() is not None

    def is_not_deleted(self) -> bool:
        """检查记录是否未被软删除

        Returns:
            如果记录未被软删除返回True，否则返回False
        """
        return not self.is_deleted()

    def get_deleted_at(self) -> datetime | None:
        """获取删除时间

        Returns:
            删除时间，如果未删除则返回None
        """
        return getattr(self, self.deleted_at_column, None)

    def set_deleted_at(self, value: datetime | None) -> None:
        """设置删除时间

        Args:
            value: 删除时间
        """
        setattr(self, self.deleted_at_column, value)

    # =================================================================
    # 软删除操作
    # =================================================================

    async def delete(self, force: bool = False) -> None:
        """删除记录

        Args:
            force: 是否强制物理删除，默认False使用软删除

        Example:
            await user.delete()  # 软删除
            await user.delete(force=True)  # 物理删除
        """
        if force or not self.soft_delete:
            # 物理删除
            await self.force_delete()
        else:
            # 软删除
            await self.soft_delete_record()

    async def soft_delete_record(self) -> None:
        """执行软删除

        设置 deleted_at 为当前时间。

        Example:
            await user.soft_delete_record()
        """
        if not self.soft_delete:
            raise ValueError("模型未启用软删除功能")

        # 设置删除时间
        self.set_deleted_at(datetime.now(timezone.utc))

        # 保存更改
        await self.save()

    async def restore(self) -> None:
        """恢复软删除的记录

        将 deleted_at 设置为 None。

        Example:
            await user.restore()
        """
        if not self.soft_delete:
            raise ValueError("模型未启用软删除功能")

        if not self.is_deleted():
            raise ValueError("记录未被删除，无需恢复")

        # 清空删除时间
        self.set_deleted_at(None)

        # 保存更改
        await self.save()

    async def force_delete(self) -> None:
        """强制物理删除记录

        Example:
            await user.force_delete()
        """

        async def _force_delete(session: AsyncSession) -> None:
            await session.delete(self)
            await session.flush()

        await execute_with_session(_force_delete)

    # =================================================================
    # 查询范围方法（类方法）
    # =================================================================

    @classmethod
    def with_trashed(cls):
        """包含已删除记录的查询构建器

        Returns:
            包含已删除记录的查询构建器

        Example:
            all_users = await User.with_trashed().all()
        """
        from fastorm.query.soft_delete import SoftDeleteQueryBuilder

        return SoftDeleteQueryBuilder(cls, include_deleted=True)

    @classmethod
    def only_trashed(cls):
        """只查询已删除记录的查询构建器

        Returns:
            只包含已删除记录的查询构建器

        Example:
            deleted_users = await User.only_trashed().all()
        """
        from fastorm.query.soft_delete import SoftDeleteQueryBuilder

        return SoftDeleteQueryBuilder(cls, only_deleted=True)

    @classmethod
    def without_trashed(cls):
        """排除已删除记录的查询构建器（默认行为）

        Returns:
            排除已删除记录的查询构建器

        Example:
            active_users = await User.without_trashed().all()
        """
        from fastorm.query.soft_delete import SoftDeleteQueryBuilder

        return SoftDeleteQueryBuilder(cls, include_deleted=False)

    # =================================================================
    # 批量软删除操作
    # =================================================================

    @classmethod
    async def restore_all(cls, ids: list[Any]) -> int:
        """批量恢复记录

        Args:
            ids: 要恢复的记录ID列表

        Returns:
            恢复的记录数量

        Example:
            count = await User.restore_all([1, 2, 3])
        """

        async def _restore_all(session: AsyncSession) -> int:
            from sqlalchemy import update

            result = await session.execute(
                update(cls)
                .where(
                    and_(
                        cls.id.in_(ids),
                        getattr(cls, cls.deleted_at_column).is_not(None),
                    )
                )
                .values({cls.deleted_at_column: None})
            )
            return result.rowcount or 0

        return await execute_with_session(_restore_all)

    @classmethod
    async def force_delete_all(cls, ids: list[Any]) -> int:
        """批量物理删除记录

        Args:
            ids: 要删除的记录ID列表

        Returns:
            删除的记录数量

        Example:
            count = await User.force_delete_all([1, 2, 3])
        """

        async def _force_delete_all(session: AsyncSession) -> int:
            from sqlalchemy import delete

            result = await session.execute(delete(cls).where(cls.id.in_(ids)))
            return result.rowcount or 0

        return await execute_with_session(_force_delete_all)

    # =================================================================
    # 内部钩子方法
    # =================================================================

    def _get_soft_delete_condition(self):
        """获取软删除查询条件

        Returns:
            SQLAlchemy查询条件
        """
        if not self.soft_delete:
            return None

        deleted_at_column = getattr(self.__class__, self.deleted_at_column)
        return deleted_at_column.is_(None)

    @classmethod
    def _apply_soft_delete_filter(cls, query):
        """应用软删除过滤器到查询

        Args:
            query: SQLAlchemy查询对象

        Returns:
            应用软删除过滤器后的查询对象
        """
        if not cls.soft_delete:
            return query

        deleted_at_column = getattr(cls, cls.deleted_at_column)
        return query.where(deleted_at_column.is_(None))

    # =================================================================
    # 软删除工具方法
    # =================================================================

    @classmethod
    def get_soft_delete_column(cls) -> str | None:
        """获取软删除字段名

        Returns:
            软删除字段名，如果未启用软删除则返回None
        """
        return cls.deleted_at_column if cls.soft_delete else None

    def format_deleted_at(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str | None:
        """格式化删除时间

        Args:
            format_str: 时间格式字符串

        Returns:
            格式化后的删除时间字符串，如果未删除则返回None

        Example:
            deleted_time = user.format_deleted_at()
            # '2023-12-01 15:30:00' 或 None
        """
        deleted_at = self.get_deleted_at()
        if deleted_at:
            return deleted_at.strftime(format_str)
        return None
