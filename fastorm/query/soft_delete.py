"""
软删除查询构建器模块

提供支持软删除功能的查询构建器，兼容SQLAlchemy 2.0语法。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastorm.query.builder import QueryBuilder

if TYPE_CHECKING:
    from fastorm.model.model import Model

__all__ = ["SoftDeleteQueryBuilder"]


class SoftDeleteQueryBuilder(QueryBuilder):
    """软删除查询构建器

    扩展基础QueryBuilder，添加软删除支持功能。

    Features:
    - 自动处理软删除记录的过滤
    - 支持 with_trashed()、only_trashed()、without_trashed() 方法
    - 兼容SQLAlchemy 2.0现代语法
    - 保持所有原有QueryBuilder功能

    Example:
        # 包含已删除记录
        users = await User.with_trashed().all()

        # 仅查询已删除记录
        deleted = await User.only_trashed().all()

        # 排除已删除记录（默认行为）
        active = await User.without_trashed().all()
    """

    def __init__(
        self,
        model_class: type[Model],
        include_deleted: bool = False,
        only_deleted: bool = False,
    ):
        """初始化软删除查询构建器

        Args:
            model_class: 模型类
            include_deleted: 是否包含已删除记录
            only_deleted: 是否仅查询已删除记录
        """
        super().__init__(model_class)
        self.include_deleted = include_deleted
        self.only_deleted = only_deleted

        # 验证模型是否支持软删除
        if not getattr(model_class, "soft_delete", False):
            msg = f"模型 {model_class.__name__} 未启用软删除功能"
            raise ValueError(msg)

        # 应用软删除过滤器
        self._apply_soft_delete_filter()

    def _apply_soft_delete_filter(self) -> None:
        """应用软删除过滤器到查询"""
        column_name = getattr(self._model_class, "deleted_at_column", "deleted_at")
        deleted_at_column = getattr(self._model_class, column_name)

        if self.only_deleted:
            # 仅查询已删除记录
            self._query = self._query.where(deleted_at_column.is_not(None))
        elif not self.include_deleted:
            # 排除已删除记录（默认行为）
            self._query = self._query.where(deleted_at_column.is_(None))
        # include_deleted=True 时不添加任何过滤器

    def with_trashed(self) -> SoftDeleteQueryBuilder:
        """包含已删除记录的查询

        返回包含所有记录（包括已删除）的新查询构建器。

        Returns:
            包含已删除记录的查询构建器

        Example:
            users = await User.with_trashed().all()
        """
        return SoftDeleteQueryBuilder(
            self._model_class, include_deleted=True, only_deleted=False
        )

    def only_trashed(self) -> SoftDeleteQueryBuilder:
        """仅查询已删除记录

        返回仅包含已删除记录的新查询构建器。

        Returns:
            仅包含已删除记录的查询构建器

        Example:
            deleted_users = await User.only_trashed().all()
        """
        return SoftDeleteQueryBuilder(
            self._model_class, include_deleted=False, only_deleted=True
        )

    def without_trashed(self) -> SoftDeleteQueryBuilder:
        """排除已删除记录的查询

        返回排除已删除记录的新查询构建器（默认行为）。

        Returns:
            排除已删除记录的查询构建器

        Example:
            active_users = await User.without_trashed().all()
        """
        return SoftDeleteQueryBuilder(
            self._model_class, include_deleted=False, only_deleted=False
        )

    def restore(self, ids: list[Any] | None = None) -> SoftDeleteQueryBuilder:
        """构建恢复查询

        用于批量恢复软删除记录的查询构建器。

        Args:
            ids: 要恢复的记录ID列表，如果为None则恢复所有匹配当前查询条件的记录

        Returns:
            当前查询构建器实例（支持链式调用）

        Example:
            # 恢复特定ID的记录
            await User.only_trashed().restore([1, 2, 3]).execute()

            # 恢复所有符合条件的已删除记录
            query = User.only_trashed().where('name', 'John').restore()
            await query.execute()
        """
        if ids:
            self._query = self._query.where(self._model_class.id.in_(ids))

        # 确保只操作已删除的记录
        column_name = getattr(self._model_class, "deleted_at_column", "deleted_at")
        deleted_at_column = getattr(self._model_class, column_name)
        self._query = self._query.where(deleted_at_column.is_not(None))

        return self

    def force_delete(self, ids: list[Any] | None = None) -> SoftDeleteQueryBuilder:
        """构建物理删除查询

        用于批量物理删除记录的查询构建器。

        Args:
            ids: 要删除的记录ID列表，如果为None则删除所有匹配当前查询条件的记录

        Returns:
            当前查询构建器实例（支持链式调用）

        Example:
            # 物理删除特定ID的记录
            await User.force_delete([1, 2, 3]).execute()

            # 物理删除所有符合条件的记录
            query = User.where('status', 'inactive').force_delete()
            await query.execute()
        """
        if ids:
            self._query = self._query.where(self._model_class.id.in_(ids))

        return self

    def clone(self) -> SoftDeleteQueryBuilder:
        """克隆查询构建器

        创建当前查询构建器的深拷贝，包括软删除设置。

        Returns:
            克隆的查询构建器实例
        """
        cloned = SoftDeleteQueryBuilder(
            self._model_class,
            include_deleted=self.include_deleted,
            only_deleted=self.only_deleted,
        )

        # 复制查询状态
        cloned._query = self._query
        cloned._conditions = self._conditions.copy()
        cloned._with_relations = self._with_relations.copy()
        cloned._order_clauses = self._order_clauses.copy()
        cloned._limit_value = self._limit_value
        cloned._offset_value = self._offset_value
        cloned._distinct_value = self._distinct_value

        return cloned

    def __repr__(self) -> str:
        """字符串表示"""
        status = []
        if self.include_deleted:
            status.append("with_trashed")
        elif self.only_deleted:
            status.append("only_trashed")
        else:
            status.append("without_trashed")

        model_name = self._model_class.__name__
        return f"<SoftDeleteQueryBuilder({model_name}) " f"[{', '.join(status)}]>"
