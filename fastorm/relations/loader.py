"""
FastORM 关系加载器

提供关系数据的加载和管理功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from fastorm.core.session_manager import execute_with_session

from .base import Relation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RelationLoader:
    """关系加载器

    管理模型关系的加载和缓存。
    """

    @staticmethod
    async def load_relation(
        parent: Any, relation_name: str, relation: Relation, session: AsyncSession
    ) -> Any:
        """加载单个关系

        Args:
            parent: 父模型实例
            relation_name: 关系名称
            relation: 关系实例
            session: 数据库会话

        Returns:
            关系数据
        """
        result = await relation.load(parent, session)

        # 将结果缓存到父实例上
        setattr(parent, f"_{relation_name}_cache", result)
        setattr(parent, f"_{relation_name}_loaded", True)

        return result

    @staticmethod
    async def load_relations(
        parent: Any, relations: dict[str, Relation], session: AsyncSession
    ) -> dict[str, Any]:
        """批量加载多个关系

        Args:
            parent: 父模型实例
            relations: 关系字典
            session: 数据库会话

        Returns:
            关系数据字典
        """
        results = {}

        for relation_name, relation in relations.items():
            results[relation_name] = await RelationLoader.load_relation(
                parent, relation_name, relation, session
            )

        return results

    @staticmethod
    async def eager_load_relations(
        instances: list[Any], relations: dict[str, Relation], session: AsyncSession
    ) -> None:
        """预加载关系（避免N+1查询）

        Args:
            instances: 模型实例列表
            relations: 关系字典
            session: 数据库会话
        """
        for relation_name, relation in relations.items():
            # 为每个实例加载关系
            for instance in instances:
                await RelationLoader.load_relation(
                    instance, relation_name, relation, session
                )

    @staticmethod
    def get_relation_cache(parent: Any, relation_name: str) -> Any:
        """获取关系缓存

        Args:
            parent: 父模型实例
            relation_name: 关系名称

        Returns:
            缓存的关系数据，如果未加载则返回None
        """
        if hasattr(parent, f"_{relation_name}_loaded"):
            if getattr(parent, f"_{relation_name}_loaded"):
                return getattr(parent, f"_{relation_name}_cache", None)
        return None

    @staticmethod
    def is_relation_loaded(parent: Any, relation_name: str) -> bool:
        """检查关系是否已加载

        Args:
            parent: 父模型实例
            relation_name: 关系名称

        Returns:
            如果关系已加载返回True，否则返回False
        """
        return getattr(parent, f"_{relation_name}_loaded", False)

    @staticmethod
    def clear_relation_cache(parent: Any, relation_name: Optional[str] = None) -> None:
        """清空关系缓存

        Args:
            parent: 父模型实例
            relation_name: 关系名称，如果为None则清空所有关系缓存
        """
        if relation_name:
            # 清空指定关系的缓存
            if hasattr(parent, f"_{relation_name}_cache"):
                delattr(parent, f"_{relation_name}_cache")
            if hasattr(parent, f"_{relation_name}_loaded"):
                delattr(parent, f"_{relation_name}_loaded")
        else:
            # 清空所有关系缓存
            attrs_to_remove = []
            for attr_name in dir(parent):
                is_cache = attr_name.endswith("_cache")
                is_loaded = attr_name.endswith("_loaded")
                is_private = attr_name.startswith("_")
                is_not_special = not attr_name.startswith("__")

                if (is_cache or is_loaded) and is_private and is_not_special:
                    attrs_to_remove.append(attr_name)

            for attr_name in attrs_to_remove:
                if hasattr(parent, attr_name):
                    delattr(parent, attr_name)
