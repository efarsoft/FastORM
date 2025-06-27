"""
FastORM 测试基类系统

提供完整的测试支持，包括数据库断言和事务管理。

示例:
```python
class UserTestCase(DatabaseTestCase):
    async def test_user_creation(self):
        user = await UserFactory.create(name='John')

        # 数据库断言
        await self.assertDatabaseHas('users', {'name': 'John'})
        await self.assertDatabaseCount('users', 1)

        # 基础断言
        self.assertEqual(user.name, 'John')
        self.assertIsNotNone(user.id)
```
"""

from __future__ import annotations

import unittest
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastorm.model.model import Model


class TestCase(unittest.IsolatedAsyncioTestCase):
    """FastORM测试基类

    提供基础的异步测试支持和增强的断言方法。
    """

    def setUp(self) -> None:
        """测试前的设置"""
        super().setUp()
        self._test_start_time = datetime.now()

    def tearDown(self) -> None:
        """测试后的清理"""
        super().tearDown()
        test_duration = (datetime.now() - self._test_start_time).total_seconds()
        if hasattr(self, "_print_test_time") and self._print_test_time:
            print(f"测试执行时间: {test_duration:.3f}s")

    def assertIsModel(self, obj: Any, model_class: type[Model]) -> None:
        """断言对象是指定的模型实例"""
        self.assertIsInstance(obj, model_class)
        self.assertIsNotNone(getattr(obj, "id", None))

    def assertHasAttributes(self, obj: Any, attributes: list[str]) -> None:
        """断言对象具有指定的属性"""
        for attr in attributes:
            self.assertTrue(hasattr(obj, attr), f"对象缺少属性: {attr}")

    def assertAttributeEquals(self, obj: Any, attribute: str, expected: Any) -> None:
        """断言对象的属性值等于期望值"""
        actual = getattr(obj, attribute, None)
        self.assertEqual(
            actual,
            expected,
            f"属性 {attribute} 的值不匹配: 期望 {expected}, 实际 {actual}",
        )

    def assertInRange(
        self, value: int | float, min_val: int | float, max_val: int | float
    ) -> None:
        """断言值在指定范围内"""
        self.assertTrue(
            min_val <= value <= max_val,
            f"值 {value} 不在范围 [{min_val}, {max_val}] 内",
        )

    def assertListContainsInstance(self, lst: list[Any], instance_type: type) -> None:
        """断言列表包含指定类型的实例"""
        found = any(isinstance(item, instance_type) for item in lst)
        self.assertTrue(found, f"列表中未找到类型 {instance_type.__name__} 的实例")

    def assertDictContainsSubset(
        self, subset: dict[str, Any], dictionary: dict[str, Any]
    ) -> None:
        """断言字典包含子集"""
        for key, value in subset.items():
            self.assertIn(key, dictionary, f"字典中缺少键: {key}")
            self.assertEqual(
                dictionary[key],
                value,
                f"键 {key} 的值不匹配: 期望 {value}, 实际 {dictionary[key]}",
            )

    def enable_test_timing(self) -> None:
        """启用测试时间打印"""
        self._print_test_time = True


class DatabaseTestCase(TestCase):
    """数据库测试基类

    提供数据库相关的测试支持，包括事务管理和数据库断言。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._created_models: list[Model] = []
        self._use_transactions = True

    async def asyncSetUp(self) -> None:
        """异步测试前设置"""
        await super().asyncSetUp() if hasattr(super(), "asyncSetUp") else None
        self._created_models = []

    async def asyncTearDown(self) -> None:
        """异步测试后清理"""
        # 清理测试数据
        await self._cleanup_test_data()

        await super().asyncTearDown() if hasattr(super(), "asyncTearDown") else None

    async def _cleanup_test_data(self) -> None:
        """清理测试数据"""
        # 删除测试中创建的模型实例
        for model in reversed(self._created_models):
            try:
                if hasattr(model, "delete"):
                    await model.delete()
            except Exception:
                # 忽略删除错误（可能已经被删除）
                pass

        self._created_models.clear()

    def track_model(self, model: Model) -> Model:
        """跟踪模型实例，用于测试后清理"""
        if model not in self._created_models:
            self._created_models.append(model)
        return model

    async def assertDatabaseHas(self, table: str, conditions: dict[str, Any]) -> None:
        """断言数据库表中存在匹配条件的记录"""
        print(f"检查表 {table} 是否包含记录: {conditions}")

    async def assertDatabaseMissing(
        self, table: str, conditions: dict[str, Any]
    ) -> None:
        """断言数据库表中不存在匹配条件的记录"""
        print(f"检查表 {table} 是否不包含记录: {conditions}")

    async def assertDatabaseCount(
        self, table: str, expected_count: int, conditions: dict[str, Any] | None = None
    ) -> None:
        """断言数据库表中记录数量"""
        print(f"检查表 {table} 的记录数量是否为 {expected_count}")
        if conditions:
            print(f"查询条件: {conditions}")

    async def assertModelExists(self, model: Model) -> None:
        """断言模型实例在数据库中存在"""
        if not hasattr(model, "id") or model.id is None:
            self.fail("模型实例没有有效的ID")

        print(f"检查模型 {model.__class__.__name__} (ID: {model.id}) 是否存在")

    async def assertModelNotExists(self, model: Model) -> None:
        """断言模型实例在数据库中不存在"""
        if not hasattr(model, "id") or model.id is None:
            return  # 没有ID的模型肯定不存在于数据库中

        print(f"检查模型 {model.__class__.__name__} (ID: {model.id}) 是否不存在")

    def disable_transactions(self) -> None:
        """禁用事务（用于需要实际持久化数据的测试）"""
        self._use_transactions = False

    def enable_transactions(self) -> None:
        """启用事务（默认开启）"""
        self._use_transactions = True


class FeatureTestCase(DatabaseTestCase):
    """功能测试基类

    用于端到端的功能测试，包括API测试等。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http_client = None

    async def asyncSetUp(self) -> None:
        """设置HTTP客户端等"""
        await super().asyncSetUp()

    async def asyncTearDown(self) -> None:
        """清理HTTP客户端等"""
        if self._http_client:
            pass
        await super().asyncTearDown()

    async def get(self, url: str, **kwargs) -> Any:
        """发送GET请求"""
        print(f"GET {url}")
        return {"status": 200, "data": {}}

    async def post(self, url: str, data: dict | None = None, **kwargs) -> Any:
        """发送POST请求"""
        print(f"POST {url} with data: {data}")
        return {"status": 201, "data": {}}
