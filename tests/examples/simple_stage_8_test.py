"""
FastORM 第八阶段简单测试

验证核心功能是否正常工作。
"""

import asyncio
import sys
import os

# 添加FastORM到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """测试导入功能"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试工厂系统导入
        from fastorm.testing.factory import Factory, trait, LazyAttribute, Sequence
        print("✅ Factory系统导入成功")
        
        # 测试Faker导入
        from fastorm.testing.faker_providers import faker, ChineseProvider
        print("✅ Faker系统导入成功")
        
        # 测试Seeder导入
        from fastorm.testing.seeder import Seeder, DatabaseSeeder
        print("✅ Seeder系统导入成功")
        
        # 测试TestCase导入
        from fastorm.testing.testcase import TestCase, DatabaseTestCase
        print("✅ TestCase系统导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_faker_functionality():
    """测试Faker功能"""
    print("\n🎲 测试Faker功能...")
    
    try:
        from fastorm.testing.faker_providers import faker
        
        # 测试基础功能
        name = faker.name()
        email = faker.email()
        print(f"✅ 基础数据生成: {name}, {email}")
        
        # 测试中文功能
        chinese_name = faker.chinese_name()
        chinese_phone = faker.chinese_phone()
        print(f"✅ 中文数据生成: {chinese_name}, {chinese_phone}")
        
        # 测试企业功能
        department = faker.department()
        employee_id = faker.employee_id()
        print(f"✅ 企业数据生成: {department}, {employee_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Faker测试失败: {e}")
        return False


def test_factory_system():
    """测试工厂系统"""
    print("\n🏭 测试工厂系统...")
    
    try:
        from fastorm.testing.factory import Factory, trait, LazyAttribute, Sequence
        
        # 创建简单模型
        class TestUser:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        # 创建工厂
        class TestUserFactory(Factory):
            class Meta:
                model = TestUser
            
            name = "Test User"
            age = LazyAttribute(lambda: 25)
            username = Sequence(lambda n: f"user_{n}")
            
            @trait
            def admin(self):
                return {'role': 'admin', 'is_staff': True}
        
        print("✅ 工厂类创建成功")
        
        # 测试工厂信息
        info = TestUserFactory.describe()
        print(f"✅ 工厂描述: {info}")
        
        # 测试序列重置
        TestUserFactory.reset_sequences()
        print("✅ 序列重置成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 工厂系统测试失败: {e}")
        return False


async def test_seeder_system():
    """测试Seeder系统"""
    print("\n🌱 测试Seeder系统...")
    
    try:
        from fastorm.testing.seeder import Seeder, DatabaseSeeder, run_seeder
        
        class TestSeeder(Seeder):
            async def run(self):
                print("  📝 执行测试数据填充...")
                return "completed"
        
        # 测试单个Seeder
        await run_seeder(TestSeeder, verbose=False)
        print("✅ 单个Seeder执行成功")
        
        # 测试DatabaseSeeder
        db_seeder = DatabaseSeeder([TestSeeder])
        await db_seeder.execute(verbose=False)
        print("✅ DatabaseSeeder执行成功")
        
        return True
        
    except Exception as e:
        print(f"❌ Seeder系统测试失败: {e}")
        return False


def test_testcase_system():
    """测试TestCase系统"""
    print("\n🧪 测试TestCase系统...")
    
    try:
        from fastorm.testing.testcase import TestCase, DatabaseTestCase
        
        class SimpleTest(TestCase):
            def test_basic_assertions(self):
                self.assertEqual(1, 1)
                self.assertIsNotNone("test")
                self.assertInRange(25, 18, 65)
                
        # 创建测试实例
        test = SimpleTest()
        test.setUp()
        test.test_basic_assertions()
        test.tearDown()
        
        print("✅ 基础TestCase功能正常")
        
        # 测试数据库测试用例
        class SimpleDatabaseTest(DatabaseTestCase):
            def test_model_tracking(self):
                # 模拟模型
                class MockModel:
                    def __init__(self):
                        self.id = 123
                
                model = MockModel()
                tracked = self.track_model(model)
                self.assertEqual(model, tracked)
        
        db_test = SimpleDatabaseTest()
        db_test.test_model_tracking()
        print("✅ DatabaseTestCase功能正常")
        
        return True
        
    except Exception as e:
        print(f"❌ TestCase系统测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 FastORM 第八阶段简单测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("Faker功能", test_faker_functionality), 
        ("工厂系统", test_factory_system),
        ("Seeder系统", test_seeder_system),
        ("TestCase系统", test_testcase_system),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 执行测试: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
                
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n🎉 测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过! 第八阶段功能正常!")
    else:
        print("⚠️  部分测试失败，需要进一步检查")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 