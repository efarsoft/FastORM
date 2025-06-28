"""
FastORM 关系基类

定义所有关系类型的基础接口。
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class Relation(Generic[T], ABC):
    """关系基类

    所有关系类型的基类，定义关系的基本接口。
    支持SQLAlchemy 2.0风格的字符串模型引用和延迟解析。

    Args:
        model_class: 关联的模型类或类名字符串
        foreign_key: 外键字段名
        local_key: 本地键字段名
    """

    def __init__(
        self,
        model_class: type[T] | str,
        foreign_key: str | None = None,
        local_key: str = "id",
    ):
        """初始化关系

        Args:
            model_class: 关联的模型类或类名字符串
            foreign_key: 外键字段名，如果为None则自动推断
            local_key: 本地键字段名，默认为'id'
        """
        if isinstance(model_class, str):
            self._model_class_name = model_class
            self._resolved_model_class = None
        else:
            self._model_class_name = model_class.__name__
            self._resolved_model_class = model_class

        self.foreign_key = foreign_key
        self.local_key = local_key

    @property
    def model_class(self) -> type[T]:
        """获取解析后的模型类

        使用SQLAlchemy 2.0的registry进行延迟解析

        Returns:
            解析后的模型类
        """
        if self._resolved_model_class is None:
            self._resolved_model_class = self._resolve_model_class()
        return self._resolved_model_class

    def _resolve_model_class(self) -> type[T]:
        """解析字符串模型名为实际的类对象

        使用SQLAlchemy 2.0的registry系统进行解析

        Returns:
            解析后的模型类

        Raises:
            ValueError: 如果模型类未找到
        """
        try:
            # 尝试从全局命名空间获取
            import sys

            # 首先尝试从调用者的模块获取
            frame = sys._getframe(1)
            while frame:
                if self._model_class_name in frame.f_globals:
                    model_class = frame.f_globals[self._model_class_name]
                    if hasattr(model_class, "__tablename__"):
                        return model_class
                frame = frame.f_back

            # 尝试从SQLAlchemy registry获取
            from fastorm.model.model import DeclarativeBase

            registry = DeclarativeBase.registry

            if hasattr(registry, "_class_registry"):
                for cls in registry._class_registry.values():
                    if (
                        hasattr(cls, "__name__")
                        and cls.__name__ == self._model_class_name
                    ):
                        return cls

            # 尝试从registry.mappers获取
            for mapper in registry.mappers:
                if mapper.class_.__name__ == self._model_class_name:
                    return mapper.class_

        except Exception:
            pass

        raise ValueError(
            f"无法解析模型类 '{self._model_class_name}'。"
            f"请确保模型已正确定义并导入。"
        )

    @abstractmethod
    async def load(self, parent: Any, session: AsyncSession) -> Any:
        """加载关联数据

        Args:
            parent: 父模型实例
            session: 数据库会话

        Returns:
            关联的数据
        """
        pass

    def get_foreign_key(self, parent: Any) -> str:
        """获取外键字段名

        Args:
            parent: 父模型实例

        Returns:
            外键字段名
        """
        if self.foreign_key:
            return self.foreign_key

        # 自动推断外键名：父模型名_id
        return f"{parent.__class__.__name__.lower()}_id"

    def get_local_key_value(self, parent: Any) -> Any:
        """获取本地键的值

        Args:
            parent: 父模型实例

        Returns:
            本地键的值
        """
        return getattr(parent, self.local_key, None)
