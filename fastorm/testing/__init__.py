"""
FastORM 测试支持模块

提供完整的测试和开发支持工具：
- 模型工厂系统（Factory）
- 数据填充器（Seeder）
- 测试基类（TestCase）
- Faker集成
- CLI工具

示例:
```python
# 模型工厂
class UserFactory(Factory):
    class Meta:
        model = User
    
    name = faker.name()
    email = faker.email()

user = await UserFactory.create()
users = await UserFactory.create_batch(10)

# 数据填充器
class UserSeeder(Seeder):
    async def run(self):
        await UserFactory.create_batch(100)

# 测试支持
class UserTestCase(TestCase):
    async def test_user_creation(self):
        user = await UserFactory.create()
        await self.assertDatabaseHas('users', {'id': user.id})
```
"""

from .factory import Factory, trait, LazyAttribute, Sequence
from .seeder import Seeder, DatabaseSeeder
from .testcase import TestCase, DatabaseTestCase
from .faker_providers import (
    ChineseProvider, 
    CompanyProvider, 
    TestDataProvider,
    faker
)

__all__ = [
    # 工厂系统
    'Factory',
    'trait', 
    'LazyAttribute',
    'Sequence',
    
    # 数据填充
    'Seeder',
    'DatabaseSeeder',
    
    # 测试支持
    'TestCase',
    'DatabaseTestCase',
    
    # Faker支持
    'ChineseProvider',
    'CompanyProvider', 
    'TestDataProvider',
    'faker',
] 