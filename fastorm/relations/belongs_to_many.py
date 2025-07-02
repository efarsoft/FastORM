"""
FastORM BelongsToMany 关系

实现多对多关系。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import Table

from fastorm.core.session_manager import execute_with_session

from .base import Relation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BelongsToMany(Relation[list[Any]]):
    """多对多关系

    表示当前模型与另一个模型之间的多对多关系。

    示例：
    ```python
    class User(Model):
        # 用户拥有多个角色（多对多）
        roles = BelongsToMany(
            'Role',
            pivot_table='user_roles',
            foreign_key='user_id',
            related_key='role_id'
        )

    # 使用
    user = await User.find(1)
    roles = await user.roles.load()  # 加载所有关联的角色

    # Laravel风格的关系操作
    await user.roles.attach(role_id)  # 附加角色
    await user.roles.detach(role_id)  # 分离角色
    await user.roles.sync([1, 2, 3])  # 同步角色列表
    ```
    """

    def __init__(
        self,
        model_class: Any,
        pivot_table: str | None = None,
        foreign_key: str | None = None,
        related_key: str | None = None,
        local_key: str = "id",
        related_local_key: str = "id",
    ):
        """初始化多对多关系

        Args:
            model_class: 关联的模型类
            pivot_table: 中间表名，如果为None则自动推断
            foreign_key: 当前模型在中间表中的外键
            related_key: 关联模型在中间表中的外键
            local_key: 当前模型的本地键
            related_local_key: 关联模型的本地键
        """
        super().__init__(model_class, foreign_key, local_key)
        self.pivot_table = pivot_table
        self.related_key = related_key
        self.related_local_key = related_local_key

    async def load(self, parent: Any, session: AsyncSession) -> list[Any]:
        """加载关联数据

        Args:
            parent: 父模型实例
            session: 数据库会话

        Returns:
            关联的模型实例列表
        """
        # 获取本地键值
        local_key_value = self.get_local_key_value(parent)
        if local_key_value is None:
            return []

        # 获取配置
        pivot_table = self.get_pivot_table(parent)
        foreign_key = self.get_foreign_key(parent)
        related_key = self.get_related_key()

        # 通过run_sync反射Table，兼容AsyncSession
        def get_pivot_table(sync_conn):
            metadata = self.model_class.metadata
            return Table(pivot_table, metadata, autoload_with=sync_conn)

        sync_conn = await session.connection()
        pivot = await sync_conn.run_sync(get_pivot_table)

        query = (
            select(self.model_class)
            .select_from(
                self.model_class.__table__.join(
                    pivot,
                    getattr(self.model_class, self.related_local_key)
                    == getattr(pivot.c, related_key),
                )
            )
            .where(getattr(pivot.c, foreign_key) == local_key_value)
        )

        result = await session.execute(query)
        instances = list(result.scalars().all())
        return instances

    def get_pivot_table(self, parent: Any) -> str:
        """获取中间表名

        Args:
            parent: 父模型实例

        Returns:
            中间表名
        """
        if self.pivot_table:
            return self.pivot_table

        # 自动推断中间表名：按字母顺序排列的表名
        tables = sorted(
            [parent.__class__.__tablename__, self.model_class.__tablename__]
        )
        return f"{tables[0]}_{tables[1]}"

    def get_foreign_key(self, parent: Any) -> str:
        """获取当前模型在中间表中的外键名"""
        if self.foreign_key:
            return self.foreign_key

        # 自动推断：父模型名_id
        return f"{parent.__class__.__name__.lower()}_id"

    def get_related_key(self) -> str:
        """获取关联模型在中间表中的外键名"""
        if self.related_key:
            return self.related_key

        # 自动推断：关联模型名_id
        return f"{self.model_class.__name__.lower()}_id"

    # =================================================================
    # Laravel风格的多对多关系操作方法
    # =================================================================

    async def attach(
        self,
        parent: Any,
        ids: int | list[int],
        pivot_data: dict[str, Any] | None = None,
    ) -> None:
        """附加关联记录（Laravel风格）

        Args:
            parent: 父模型实例
            ids: 要附加的ID或ID列表
            pivot_data: 中间表额外数据
        """

        async def _attach(session: AsyncSession) -> None:
            if isinstance(ids, (int, str)):
                id_list = [ids]
            else:
                id_list = ids

            pivot_table = self.get_pivot_table(parent)
            foreign_key = self.get_foreign_key(parent)
            related_key = self.get_related_key()
            local_key_value = self.get_local_key_value(parent)

            # 构建插入数据
            insert_data = []
            base_data = pivot_data or {}

            for related_id in id_list:
                row_data = {
                    foreign_key: local_key_value,
                    related_key: related_id,
                    **base_data,
                }
                insert_data.append(row_data)

            # 批量插入中间表
            if insert_data:
                await session.execute(
                    text(f"""
                        INSERT OR IGNORE INTO {pivot_table} 
                        ({', '.join(insert_data[0].keys())}) 
                        VALUES {', '.join([
                            f"({', '.join([':' + k + str(i) for k in row.keys()])})"
                            for i, row in enumerate(insert_data)
                        ])}
                    """),
                    {
                        f"{k}{i}": v
                        for i, row in enumerate(insert_data)
                        for k, v in row.items()
                    },
                )

        await execute_with_session(_attach)

    async def detach(self, parent: Any, ids: int | list[int] | None = None) -> None:
        """分离关联记录（Laravel风格）

        Args:
            parent: 父模型实例
            ids: 要分离的ID或ID列表，None表示分离所有
        """

        async def _detach(session: AsyncSession) -> None:
            pivot_table = self.get_pivot_table(parent)
            foreign_key = self.get_foreign_key(parent)
            related_key = self.get_related_key()
            local_key_value = self.get_local_key_value(parent)

            if ids is None:
                # 分离所有关联
                await session.execute(
                    text(f"DELETE FROM {pivot_table} WHERE {foreign_key} = :local_id"),
                    {"local_id": local_key_value},
                )
            else:
                # 分离指定ID
                if isinstance(ids, (int, str)):
                    id_list = [ids]
                else:
                    id_list = ids

                if id_list:
                    placeholders = ", ".join([f":id{i}" for i in range(len(id_list))])
                    await session.execute(
                        text(f"""
                            DELETE FROM {pivot_table} 
                            WHERE {foreign_key} = :local_id 
                            AND {related_key} IN ({placeholders})
                        """),
                        {
                            "local_id": local_key_value,
                            **{f"id{i}": v for i, v in enumerate(id_list)},
                        },
                    )

        await execute_with_session(_detach)

    async def sync(
        self, parent: Any, ids: list[int], pivot_data: dict[str, Any] | None = None
    ) -> None:
        """同步关联记录（Laravel风格）

        将关联关系同步为指定的ID列表，会删除不在列表中的关联。

        Args:
            parent: 父模型实例
            ids: 要同步的ID列表
            pivot_data: 中间表额外数据
        """

        async def _sync(session: AsyncSession) -> None:
            # 先分离所有现有关联
            await self.detach(parent)

            # 然后附加新的关联
            if ids:
                await self.attach(parent, ids, pivot_data)

        await execute_with_session(_sync)

    async def toggle(
        self,
        parent: Any,
        ids: int | list[int],
        pivot_data: dict[str, Any] | None = None,
    ) -> dict[str, list[int]]:
        """切换关联状态（Laravel风格）

        如果关联存在则分离，不存在则附加。

        Args:
            parent: 父模型实例
            ids: 要切换的ID或ID列表
            pivot_data: 中间表额外数据

        Returns:
            包含attached和detached列表的字典
        """

        async def _toggle(session: AsyncSession) -> dict[str, list[int]]:
            if isinstance(ids, (int, str)):
                id_list = [ids]
            else:
                id_list = ids

            pivot_table = self.get_pivot_table(parent)
            foreign_key = self.get_foreign_key(parent)
            related_key = self.get_related_key()
            local_key_value = self.get_local_key_value(parent)

            # 获取当前关联的ID
            current_ids_result = await session.execute(
                text(
                    f"SELECT {related_key} FROM {pivot_table} WHERE {foreign_key} = :local_id"
                ),
                {"local_id": local_key_value},
            )
            current_ids = {row[0] for row in current_ids_result}

            attached = []
            detached = []

            for an_id in id_list:
                if an_id in current_ids:
                    detached.append(an_id)
                else:
                    attached.append(an_id)

            if detached:
                await self.detach(parent, detached)
            if attached:
                await self.attach(parent, attached, pivot_data)

            return {"attached": attached, "detached": detached}

        return await execute_with_session(_toggle)

    async def sync_without_detaching(
        self, parent: Any, ids: list[int], pivot_data: dict[str, Any] | None = None
    ) -> None:
        """同步但不分离现有关联（Laravel风格）

        Args:
            parent: 父模型实例
            ids: 要同步的ID列表
            pivot_data: 中间表额外数据
        """

        async def _sync_without_detaching(session: AsyncSession) -> None:
            # 获取当前关联的ID
            current_relations = await self.load(parent, session)
            current_ids = [
                getattr(instance, self.related_local_key)
                for instance in current_relations
            ]

            # 只附加不存在的关联
            new_ids = [id_val for id_val in ids if id_val not in current_ids]
            if new_ids:
                await self.attach(parent, new_ids, pivot_data)

        await execute_with_session(_sync_without_detaching)
