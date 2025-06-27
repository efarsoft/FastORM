"""
FastORM 时间戳 Mixin

提供Eloquent风格的自动时间戳管理。
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import ClassVar

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class TimestampMixin:
    """时间戳混入类

    提供Eloquent风格的自动时间戳管理。

    特性：
    - 自动管理 created_at 和 updated_at 字段
    - 支持自定义时间戳字段名
    - 可配置是否启用时间戳

    示例：
    ```python
    class User(TimestampMixin, Model):
        timestamps = True  # 启用时间戳

        name: Mapped[str]
        email: Mapped[str]

    # 自动设置 created_at
    user = await User.create(name='John', email='john@example.com')
    print(user.created_at)  # 当前时间

    # 自动更新 updated_at
    await user.update(name='Jane')
    print(user.updated_at)  # 更新时间
    ```
    """

    # =================================================================
    # 配置选项
    # =================================================================

    # 是否启用时间戳（默认False，需要显式启用）
    timestamps: ClassVar[bool] = False

    # 时间戳字段名配置
    created_at_column: ClassVar[str] = "created_at"
    updated_at_column: ClassVar[str] = "updated_at"

    # =================================================================
    # 时间戳字段定义
    # =================================================================

    # 创建时间 - 仅在创建时设置
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="创建时间",
    )

    # 更新时间 - 创建和更新时都会设置
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="更新时间",
    )

    # =================================================================
    # 时间戳管理方法
    # =================================================================

    def touch(self) -> None:
        """手动更新时间戳

        更新 updated_at 为当前时间，不触发其他字段更新。

        Example:
            await user.touch()
            await user.save()
        """
        if self.timestamps:
            setattr(self, self.updated_at_column, datetime.now(timezone.utc))

    @classmethod
    def without_timestamps(cls):
        """临时禁用时间戳

        返回一个禁用时间戳的模型类副本，用于批量操作等场景。

        Example:
            # 批量插入时禁用时间戳以提高性能
            UserWithoutTimestamps = User.without_timestamps()
            await UserWithoutTimestamps.create_many([...])

        Returns:
            禁用时间戳的模型类
        """

        class ModelWithoutTimestamps(cls):
            timestamps = False

        ModelWithoutTimestamps.__name__ = f"{cls.__name__}WithoutTimestamps"
        return ModelWithoutTimestamps

    def get_created_at(self) -> datetime | None:
        """获取创建时间

        Returns:
            创建时间，如果未设置则返回None
        """
        return getattr(self, self.created_at_column, None)

    def get_updated_at(self) -> datetime | None:
        """获取更新时间

        Returns:
            更新时间，如果未设置则返回None
        """
        return getattr(self, self.updated_at_column, None)

    def set_created_at(self, value: datetime | None) -> None:
        """设置创建时间

        Args:
            value: 创建时间
        """
        setattr(self, self.created_at_column, value)

    def set_updated_at(self, value: datetime | None) -> None:
        """设置更新时间

        Args:
            value: 更新时间
        """
        setattr(self, self.updated_at_column, value)

    # =================================================================
    # 内部钩子方法
    # =================================================================

    def _before_create_timestamp(self) -> None:
        """创建前的时间戳处理"""
        if not self.timestamps:
            return

        now = datetime.now(timezone.utc)

        # 设置创建时间（如果未设置）
        if not self.get_created_at():
            self.set_created_at(now)

        # 设置更新时间（如果未设置）
        if not self.get_updated_at():
            self.set_updated_at(now)

    def _before_update_timestamp(self) -> None:
        """更新前的时间戳处理"""
        if not self.timestamps:
            return

        # 自动更新 updated_at
        self.set_updated_at(datetime.now(timezone.utc))

    # =================================================================
    # 时间戳工具方法
    # =================================================================

    @classmethod
    def get_timestamp_columns(cls) -> list[str]:
        """获取时间戳字段列表

        Returns:
            时间戳字段名列表
        """
        if not cls.timestamps:
            return []

        return [cls.created_at_column, cls.updated_at_column]

    def is_timestamps_enabled(self) -> bool:
        """检查是否启用时间戳

        Returns:
            如果启用时间戳返回True，否则返回False
        """
        return self.timestamps

    def format_timestamps(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> dict:
        """格式化时间戳

        Args:
            format_str: 时间格式字符串

        Returns:
            格式化后的时间戳字典

        Example:
            timestamps = user.format_timestamps()
            # 返回格式化的时间戳字典
        """
        result = {}

        created_at = self.get_created_at()
        if created_at:
            result[self.created_at_column] = created_at.strftime(format_str)

        updated_at = self.get_updated_at()
        if updated_at:
            result[self.updated_at_column] = updated_at.strftime(format_str)

        return result
