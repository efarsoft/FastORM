"""
FastORM Fillable Mixin

提供Eloquent风格的批量赋值控制功能。
"""

from __future__ import annotations

from typing import Any, ClassVar


class FillableMixin:
    """批量赋值控制混入类

    提供Eloquent风格的fillable和guarded功能。

    特性：
    - fillable：允许批量赋值的字段白名单
    - guarded：禁止批量赋值的字段黑名单
    - 安全的批量赋值控制
    - 灵活的字段过滤

    示例：
    ```python
    class User(FillableMixin, Model):
        fillable = ['name', 'email', 'age']  # 只允许这些字段批量赋值
        guarded = ['id', 'password']         # 禁止这些字段批量赋值

        name: Mapped[str]
        email: Mapped[str]
        age: Mapped[int]
        password: Mapped[str]

    # 批量赋值 - 只有fillable中的字段会被设置
    user = await User.create({
        'name': 'John',
        'email': 'john@example.com',
        'age': 25,
        'password': 'secret'  # 这个会被忽略（在guarded中）
    })

    # 强制赋值（跳过fillable检查）
    user = await User.create({
        'name': 'Admin',
        'password': 'admin123'
    }, force_fill=True)
    ```
    """

    # =================================================================
    # 配置选项
    # =================================================================

    # 允许批量赋值的字段白名单
    fillable: ClassVar[list[str]] = []

    # 禁止批量赋值的字段黑名单
    guarded: ClassVar[list[str]] = ["id"]

    # 是否启用严格模式（fillable为空时是否允许所有字段）
    strict_fillable: ClassVar[bool] = False

    # =================================================================
    # 批量赋值控制方法
    # =================================================================

    @classmethod
    def get_fillable_attributes(cls) -> set[str]:
        """获取允许批量赋值的字段集合

        Returns:
            允许批量赋值的字段名集合
        """
        return set(cls.fillable)

    @classmethod
    def get_guarded_attributes(cls) -> set[str]:
        """获取禁止批量赋值的字段集合

        Returns:
            禁止批量赋值的字段名集合
        """
        return set(cls.guarded)

    @classmethod
    def is_fillable(cls, attribute: str) -> bool:
        """检查字段是否允许批量赋值

        Args:
            attribute: 字段名

        Returns:
            如果字段允许批量赋值返回True，否则返回False
        """
        # 如果在guarded中，直接禁止
        if attribute in cls.get_guarded_attributes():
            return False

        # 如果有fillable配置，只允许fillable中的字段
        fillable_attrs = cls.get_fillable_attributes()
        if fillable_attrs:
            return attribute in fillable_attrs

        # 如果没有fillable配置且非严格模式，允许所有非guarded字段
        if not cls.strict_fillable:
            return True

        # 严格模式下，fillable为空时禁止所有字段
        return False

    @classmethod
    def filter_fillable_attributes(
        cls, attributes: dict[str, Any], force_fill: bool = False
    ) -> dict[str, Any]:
        """过滤出允许批量赋值的字段

        Args:
            attributes: 要过滤的字段字典
            force_fill: 是否强制填充（跳过fillable检查）

        Returns:
            过滤后的字段字典

        Example:
            filtered = User.filter_fillable_attributes({
                'name': 'John',
                'email': 'john@example.com',
                'password': 'secret'  # 会被过滤掉
            })
        """
        if force_fill:
            return attributes

        return {key: value for key, value in attributes.items() if cls.is_fillable(key)}

    def fill_attributes(
        self, attributes: dict[str, Any], force_fill: bool = False
    ) -> None:
        """填充字段值

        Args:
            attributes: 要填充的字段字典
            force_fill: 是否强制填充（跳过fillable检查）

        Example:
            user.fill_attributes({
                'name': 'Jane',
                'email': 'jane@example.com'
            })
        """
        filtered_attrs = self.filter_fillable_attributes(attributes, force_fill)

        for key, value in filtered_attrs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    # =================================================================
    # 批量赋值工厂方法
    # =================================================================

    @classmethod
    async def make(cls, attributes: dict[str, Any], force_fill: bool = False):
        """创建模型实例但不保存到数据库

        Args:
            attributes: 字段值字典
            force_fill: 是否强制填充

        Returns:
            新的模型实例（未保存）

        Example:
            user = User.make({'name': 'John', 'email': 'john@example.com'})
            # 此时user还未保存到数据库
            await user.save()  # 手动保存
        """
        filtered_attrs = cls.filter_fillable_attributes(attributes, force_fill)
        return cls(**filtered_attrs)

    @classmethod
    def fill(cls, *attributes_list: list[dict[str, Any]]):
        """批量创建多个模型实例但不保存

        Args:
            *attributes_list: 多个字段值字典

        Returns:
            模型实例列表（未保存）

        Example:
            users = User.fill(
                {'name': 'John', 'email': 'john@example.com'},
                {'name': 'Jane', 'email': 'jane@example.com'}
            )
            # 批量保存
            for user in users:
                await user.save()
        """
        return [
            cls.make(attributes, force_fill=False) for attributes in attributes_list
        ]

    # =================================================================
    # 字段可见性控制
    # =================================================================

    # 隐藏字段（序列化时不包含）
    hidden: ClassVar[list[str]] = []

    # 可见字段（如果设置，只显示这些字段）
    visible: ClassVar[list[str]] = []

    @classmethod
    def get_hidden_attributes(cls) -> set[str]:
        """获取隐藏字段集合

        Returns:
            隐藏字段名集合
        """
        return set(cls.hidden)

    @classmethod
    def get_visible_attributes(cls) -> set[str]:
        """获取可见字段集合

        Returns:
            可见字段名集合
        """
        return set(cls.visible)

    def is_attribute_visible(self, attribute: str) -> bool:
        """检查字段是否可见

        Args:
            attribute: 字段名

        Returns:
            如果字段可见返回True，否则返回False
        """
        # 如果在hidden中，不可见
        if attribute in self.get_hidden_attributes():
            return False

        # 如果有visible配置，只显示visible中的字段
        visible_attrs = self.get_visible_attributes()
        if visible_attrs:
            return attribute in visible_attrs

        # 没有visible配置时，默认可见
        return True

    def get_visible_attributes_dict(self) -> dict[str, Any]:
        """获取可见字段的字典

        Returns:
            包含可见字段的字典

        Example:
            visible_data = user.get_visible_attributes_dict()
            # 不包含hidden字段，只包含visible字段
        """
        result = {}

        # 获取所有字段
        for column in self.__table__.columns:
            attr_name = column.name
            if self.is_attribute_visible(attr_name):
                value = getattr(self, attr_name, None)
                result[attr_name] = value

        return result

    # =================================================================
    # 动态字段控制
    # =================================================================

    def make_hidden(self, *attributes: str) -> None:
        """临时隐藏字段（仅对当前实例有效）

        Args:
            *attributes: 要隐藏的字段名

        Example:
            user.make_hidden('password', 'email')
        """
        if not hasattr(self, "_instance_hidden"):
            self._instance_hidden = set()
        self._instance_hidden.update(attributes)

    def make_visible(self, *attributes: str) -> None:
        """临时显示字段（仅对当前实例有效）

        Args:
            *attributes: 要显示的字段名

        Example:
            user.make_visible('password')  # 临时显示密码字段
        """
        if not hasattr(self, "_instance_visible"):
            self._instance_visible = set()
        self._instance_visible.update(attributes)

    def is_attribute_visible_for_instance(self, attribute: str) -> bool:
        """检查字段对当前实例是否可见（考虑实例级别的设置）

        Args:
            attribute: 字段名

        Returns:
            如果字段可见返回True，否则返回False
        """
        # 检查实例级别的隐藏设置
        instance_hidden = getattr(self, "_instance_hidden", set())
        if attribute in instance_hidden:
            return False

        # 检查实例级别的可见设置
        instance_visible = getattr(self, "_instance_visible", set())
        if instance_visible and attribute in instance_visible:
            return True

        # 使用类级别的设置
        return self.is_attribute_visible(attribute)

    # =================================================================
    # 调试和工具方法
    # =================================================================

    @classmethod
    def get_fillable_info(cls) -> dict[str, Any]:
        """获取批量赋值配置信息

        Returns:
            包含fillable配置信息的字典
        """
        return {
            "fillable": cls.fillable,
            "guarded": cls.guarded,
            "strict_fillable": cls.strict_fillable,
            "fillable_count": len(cls.fillable),
            "guarded_count": len(cls.guarded),
        }

    def get_fillable_changes(
        self, attributes: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """获取批量赋值会产生的变更

        Args:
            attributes: 要检查的字段字典

        Returns:
            包含变更信息的字典

        Example:
            changes = user.get_fillable_changes({
                'name': 'New Name',
                'password': 'secret'
            })
            # {
            #     'allowed': {'name': 'New Name'},
            #     'rejected': {'password': 'secret'},
            #     'summary': {'allowed_count': 1, 'rejected_count': 1}
            # }
        """
        allowed = {}
        rejected = {}

        for key, value in attributes.items():
            if self.is_fillable(key):
                allowed[key] = value
            else:
                rejected[key] = value

        return {
            "allowed": allowed,
            "rejected": rejected,
            "summary": {
                "allowed_count": len(allowed),
                "rejected_count": len(rejected),
                "total_count": len(attributes),
            },
        }
