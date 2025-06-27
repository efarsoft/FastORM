"""
FastORM 缓存集成示例

参考Laravel和ThinkORM的设计，展示FastORM的缓存集成功能：
- 查询缓存（remember模式）
- 模型缓存
- 装饰器缓存
- 缓存管理
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 模拟的FastORM模型类
class BaseModel:
    """模拟的基础模型类"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    @classmethod
    async def find(cls, id: int):
        """模拟查找记录"""
        await asyncio.sleep(0.1)  # 模拟数据库延迟
        return cls(id=id, name=f"Record {id}", status="active", created_at=datetime.now())
    
    @classmethod
    def query(cls):
        """返回查询构建器"""
        return MockQueryBuilder(cls)


class MockQueryBuilder:
    """模拟的查询构建器"""
    
    def __init__(self, model_class):
        self.model_class = model_class
        self._wheres = []
        self._limit = None
        self._offset = None
    
    def where(self, column: str, operator: str, value=None):
        """添加WHERE条件"""
        if value is None:
            value = operator
            operator = '='
        self._wheres.append((column, operator, value))
        return self
    
    def limit(self, limit: int):
        """设置LIMIT"""
        self._limit = limit
        return self
    
    def offset(self, offset: int):
        """设置OFFSET"""
        self._offset = offset
        return self
    
    async def get(self) -> List[BaseModel]:
        """执行查询并返回结果列表"""
        await asyncio.sleep(0.2)  # 模拟数据库查询延迟
        
        # 模拟根据条件返回不同数据
        results = []
        for i in range(1, 6):
            results.append(self.model_class(
                id=i,
                name=f"User {i}",
                status="active" if i % 2 == 0 else "inactive",
                created_at=datetime.now()
            ))
        
        # 应用WHERE条件过滤
        if self._wheres:
            filtered_results = []
            for item in results:
                match = True
                for column, operator, value in self._wheres:
                    item_value = getattr(item, column, None)
                    if operator == '=' and item_value != value:
                        match = False
                        break
                    elif operator == '!=' and item_value == value:
                        match = False
                        break
                if match:
                    filtered_results.append(item)
            results = filtered_results
        
        # 应用LIMIT和OFFSET
        if self._offset:
            results = results[self._offset:]
        if self._limit:
            results = results[:self._limit]
        
        return results
    
    async def first(self) -> Optional[BaseModel]:
        """返回第一条记录"""
        results = await self.get()
        return results[0] if results else None


# 带缓存支持的用户模型
class User(BaseModel):
    """带缓存支持的用户模型"""
    
    # 缓存配置
    _cache_ttl = 600  # 10分钟
    _cache_tags = {'users'}
    _cache_prefix = 'demo'
    
    @classmethod
    async def get_active_users_cached(cls, ttl: int = 300) -> List['User']:
        """获取活跃用户（使用缓存）
        
        参考Laravel的Cache::remember模式
        """
        from fastorm.cache import remember
        
        return await remember(
            key='active_users',
            ttl=ttl,
            callback=lambda: cls.query().where('status', 'active').get(),
            tags={'users', 'active'}
        )
    
    @classmethod
    async def find_or_cache(cls, user_id: int, ttl: int = 600) -> Optional['User']:
        """查找用户，使用缓存加速"""
        from fastorm.cache import remember
        
        cache_key = f"user:{user_id}"
        
        return await remember(
            key=cache_key,
            ttl=ttl,
            callback=lambda: cls.find(user_id),
            tags={'users', f'user:{user_id}'}
        )
    
    @classmethod
    async def invalidate_user_cache(cls, user_id: int):
        """清除用户缓存"""
        from fastorm.cache import forget, flush
        
        # 清除特定用户缓存
        await forget(f"user:{user_id}")
        
        # 清除相关标签缓存
        await flush(f'user:{user_id}')


# 产品模型示例
class Product(BaseModel):
    """产品模型示例"""
    
    _cache_ttl = 1800  # 30分钟
    _cache_tags = {'products'}


async def demo_basic_cache():
    """基础缓存功能演示"""
    print("\n=== 基础缓存功能演示 ===")
    
    # 设置缓存后端
    from fastorm.cache import setup_cache
    cache_manager = setup_cache("memory", max_size=1000)
    
    print("✓ 内存缓存后端已设置")
    
    # 基础缓存操作
    await cache_manager.set("test_key", "test_value", ttl=60)
    value = await cache_manager.get("test_key")
    print(f"✓ 缓存操作: {value}")
    
    # 标签缓存
    await cache_manager.set("user:1", {"id": 1, "name": "Alice"}, ttl=300, tags={'users', 'user:1'})
    await cache_manager.set("user:2", {"id": 2, "name": "Bob"}, ttl=300, tags={'users', 'user:2'})
    
    # 清除标签缓存
    count = await cache_manager.invalidate_tag('users')
    print(f"✓ 清除用户标签缓存: {count} 个条目")


async def demo_laravel_style_cache():
    """Laravel风格缓存演示"""
    print("\n=== Laravel风格缓存演示 ===")
    
    from fastorm.cache import remember, forget
    
    # 模拟耗时查询
    async def expensive_query():
        print("  执行数据库查询...")
        await asyncio.sleep(0.5)  # 模拟查询延迟
        return {"result": "expensive_data", "timestamp": datetime.now().isoformat()}
    
    # 第一次调用 - 执行查询
    print("第一次调用:")
    start_time = datetime.now()
    result1 = await remember('expensive_query', 60, expensive_query)
    time1 = (datetime.now() - start_time).total_seconds()
    print(f"  结果: {result1}")
    print(f"  耗时: {time1:.2f}s")
    
    # 第二次调用 - 从缓存获取
    print("\n第二次调用:")
    start_time = datetime.now()
    result2 = await remember('expensive_query', 60, expensive_query)
    time2 = (datetime.now() - start_time).total_seconds()
    print(f"  结果: {result2}")
    print(f"  耗时: {time2:.2f}s")
    print(f"  ✓ 缓存命中，速度提升: {time1/time2:.1f}x")
    
    # 清除缓存
    await forget('expensive_query')
    print("✓ 缓存已清除")


async def demo_model_cache():
    """模型缓存演示"""
    print("\n=== 模型缓存演示 ===")
    
    # 用户查询缓存
    print("获取活跃用户（第一次，查询数据库）:")
    start_time = datetime.now()
    users1 = await User.get_active_users_cached(ttl=300)
    time1 = (datetime.now() - start_time).total_seconds()
    print(f"  找到 {len(users1)} 个用户")
    print(f"  耗时: {time1:.2f}s")
    
    print("\n获取活跃用户（第二次，从缓存）:")
    start_time = datetime.now()
    users2 = await User.get_active_users_cached(ttl=300)
    time2 = (datetime.now() - start_time).total_seconds()
    print(f"  找到 {len(users2)} 个用户")
    print(f"  耗时: {time2:.2f}s")
    print(f"  ✓ 缓存命中，速度提升: {time1/time2:.1f}x")
    
    # 单个用户缓存
    print("\n用户实例缓存:")
    user = await User.find_or_cache(1, ttl=600)
    print(f"  用户: {user.name} (ID: {user.id})")
    
    # 再次获取同一用户（从缓存）
    user_cached = await User.find_or_cache(1, ttl=600)
    print(f"  缓存用户: {user_cached.name} (ID: {user_cached.id})")
    
    # 清除用户缓存
    await User.invalidate_user_cache(1)
    print("✓ 用户缓存已清除")


async def demo_decorator_cache():
    """装饰器缓存演示"""
    print("\n=== 装饰器缓存演示 ===")
    
    from fastorm.cache.decorators import cache_query
    
    @cache_query(ttl=180, tags={'calculations'})
    async def complex_calculation(x: int, y: int) -> dict:
        """模拟复杂计算"""
        print(f"  执行复杂计算: {x} + {y}")
        await asyncio.sleep(0.3)  # 模拟计算时间
        return {
            "input": [x, y],
            "result": x + y,
            "timestamp": datetime.now().isoformat()
        }
    
    # 第一次调用
    print("第一次计算:")
    start_time = datetime.now()
    result1 = await complex_calculation(10, 20)
    time1 = (datetime.now() - start_time).total_seconds()
    print(f"  结果: {result1['result']}")
    print(f"  耗时: {time1:.2f}s")
    
    # 第二次调用（相同参数）
    print("\n第二次计算（相同参数）:")
    start_time = datetime.now()
    result2 = await complex_calculation(10, 20)
    time2 = (datetime.now() - start_time).total_seconds()
    print(f"  结果: {result2['result']}")
    print(f"  耗时: {time2:.2f}s")
    print(f"  ✓ 缓存命中，速度提升: {time1/time2:.1f}x")
    
    # 第三次调用（不同参数）
    print("\n第三次计算（不同参数）:")
    start_time = datetime.now()
    result3 = await complex_calculation(30, 40)
    time3 = (datetime.now() - start_time).total_seconds()
    print(f"  结果: {result3['result']}")
    print(f"  耗时: {time3:.2f}s")


async def demo_cache_management():
    """缓存管理演示"""
    print("\n=== 缓存管理演示 ===")
    
    from fastorm.cache import get_cache, flush
    
    cache_manager = get_cache()
    
    # 设置一些测试数据
    await cache_manager.set("item1", "value1", ttl=300, tags={'test', 'group1'})
    await cache_manager.set("item2", "value2", ttl=300, tags={'test', 'group2'})
    await cache_manager.set("item3", "value3", ttl=300, tags={'test', 'group1'})
    
    print("✓ 设置了3个测试缓存项")
    
    # 查看缓存统计
    print(f"当前缓存条目数: {len(cache_manager.backend._data)}")
    
    # 按标签清除
    count = await flush('group1')
    print(f"✓ 清除 'group1' 标签: {count} 个条目")
    
    count = await flush('test')
    print(f"✓ 清除 'test' 标签: {count} 个条目")
    
    print(f"剩余缓存条目数: {len(cache_manager.backend._data)}")


async def demo_performance_comparison():
    """性能对比演示"""
    print("\n=== 性能对比演示 ===")
    
    # 模拟重复查询
    async def simulate_query():
        await asyncio.sleep(0.1)  # 模拟数据库查询
        return [{"id": i, "name": f"Item {i}"} for i in range(100)]
    
    # 不使用缓存
    print("不使用缓存 - 执行5次查询:")
    start_time = datetime.now()
    for i in range(5):
        result = await simulate_query()
    no_cache_time = (datetime.now() - start_time).total_seconds()
    print(f"  总耗时: {no_cache_time:.2f}s")
    
    # 使用缓存
    from fastorm.cache import remember
    
    print("\n使用缓存 - 执行5次查询:")
    start_time = datetime.now()
    for i in range(5):
        result = await remember('query_result', 60, simulate_query)
    cache_time = (datetime.now() - start_time).total_seconds()
    print(f"  总耗时: {cache_time:.2f}s")
    
    print(f"\n✓ 性能提升: {no_cache_time/cache_time:.1f}x")


async def main():
    """主演示函数"""
    print("FastORM 缓存集成演示")
    print("=" * 50)
    
    try:
        # 运行各种演示
        await demo_basic_cache()
        await demo_laravel_style_cache()
        await demo_model_cache()
        await demo_decorator_cache()
        await demo_cache_management()
        await demo_performance_comparison()
        
        print("\n" + "=" * 50)
        print("✓ 所有演示完成")
        
    except Exception as e:
        logger.error(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 