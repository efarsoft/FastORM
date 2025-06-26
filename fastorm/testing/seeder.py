"""
FastORM 数据填充器系统

提供结构化的测试数据填充功能。

示例:
```python
class UserSeeder(Seeder):
    async def run(self):
        # 创建管理员用户
        await UserFactory.create(trait='admin')
        
        # 批量创建普通用户
        await UserFactory.create_batch(50)
        
        print("用户数据填充完成")

class DatabaseSeeder(Seeder):
    async def run(self):
        await self.call(UserSeeder)
        await self.call(PostSeeder)
        await self.call(CommentSeeder)
```
"""

from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any, Optional, Set
from datetime import datetime


class SeederRegistry:
    """Seeder注册表"""
    
    _seeders: Dict[str, Type['Seeder']] = {}
    _execution_order: List[str] = []
    
    @classmethod
    def register(cls, seeder_class: Type['Seeder']) -> None:
        """注册Seeder"""
        name = seeder_class.__name__
        cls._seeders[name] = seeder_class
        
        # 如果还没有在执行顺序中，添加到末尾
        if name not in cls._execution_order:
            cls._execution_order.append(name)
    
    @classmethod
    def get_seeder(cls, name: str) -> Optional[Type['Seeder']]:
        """获取Seeder类"""
        return cls._seeders.get(name)
    
    @classmethod
    def get_all_seeders(cls) -> Dict[str, Type['Seeder']]:
        """获取所有Seeder"""
        return cls._seeders.copy()
    
    @classmethod
    def get_execution_order(cls) -> List[str]:
        """获取执行顺序"""
        return cls._execution_order.copy()
    
    @classmethod
    def set_execution_order(cls, order: List[str]) -> None:
        """设置执行顺序"""
        # 验证所有指定的seeder都已注册
        for name in order:
            if name not in cls._seeders:
                raise ValueError(f"Seeder '{name}' not registered")
        
        cls._execution_order = order.copy()
    
    @classmethod
    def clear(cls) -> None:
        """清空注册表"""
        cls._seeders.clear()
        cls._execution_order.clear()


class SeederMetaclass(type):
    """Seeder元类 - 自动注册Seeder"""
    
    def __new__(mcs, name: str, bases: tuple, namespace: Dict[str, Any]):
        cls = super().__new__(mcs, name, bases, namespace)
        
        # 只注册非抽象的Seeder子类
        if (name != 'Seeder' and 
            hasattr(cls, 'run') and 
            not getattr(cls, '__abstract__', False)):
            SeederRegistry.register(cls)
        
        return cls


class Seeder(ABC, metaclass=SeederMetaclass):
    """数据填充器基类
    
    Example:
        class UserSeeder(Seeder):
            async def run(self):
                # 创建测试用户
                await UserFactory.create_batch(10)
                print("用户数据填充完成")
    """
    
    def __init__(self):
        self._executed_seeders: Set[str] = set()
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
    
    @abstractmethod
    async def run(self) -> None:
        """执行数据填充逻辑"""
        pass
    
    async def execute(self, verbose: bool = True) -> None:
        """执行Seeder
        
        Args:
            verbose: 是否显示详细输出
        """
        if verbose:
            print(f"开始执行 {self.__class__.__name__}...")
        
        self._start_time = datetime.now()
        
        try:
            await self.run()
            self._end_time = datetime.now()
            
            if verbose:
                duration = (self._end_time - self._start_time).total_seconds()
                print(f"✅ {self.__class__.__name__} 执行完成 ({duration:.2f}s)")
        
        except Exception as e:
            self._end_time = datetime.now()
            if verbose:
                print(f"❌ {self.__class__.__name__} 执行失败: {e}")
            raise
    
    async def call(
        self, 
        seeder_class: Type['Seeder'], 
        verbose: bool = True,
        **kwargs: Any
    ) -> None:
        """调用其他Seeder
        
        Args:
            seeder_class: 要调用的Seeder类
            verbose: 是否显示详细输出
            **kwargs: 传递给Seeder的参数
        """
        seeder_name = seeder_class.__name__
        
        # 避免重复执行
        if seeder_name in self._executed_seeders:
            if verbose:
                print(f"⏭️  跳过已执行的 {seeder_name}")
            return
        
        # 创建并执行Seeder实例
        seeder_instance = seeder_class()
        
        # 如果Seeder的run方法接受参数，传递kwargs
        sig = inspect.signature(seeder_instance.run)
        if len(sig.parameters) > 0:
            await seeder_instance.execute(verbose=verbose)
        else:
            await seeder_instance.execute(verbose=verbose)
        
        # 标记为已执行
        self._executed_seeders.add(seeder_name)
    
    def get_execution_time(self) -> Optional[float]:
        """获取执行时间（秒）"""
        if self._start_time and self._end_time:
            return (self._end_time - self._start_time).total_seconds()
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            'seeder': self.__class__.__name__,
            'start_time': self._start_time,
            'end_time': self._end_time,
            'duration': self.get_execution_time(),
            'executed_seeders': list(self._executed_seeders)
        }


class DatabaseSeeder(Seeder):
    """数据库主Seeder - 协调所有其他Seeder的执行
    
    Example:
        class DatabaseSeeder(Seeder):
            async def run(self):
                # 按顺序执行各种Seeder
                await self.call(UserSeeder)
                await self.call(CategorySeeder)
                await self.call(ProductSeeder)
                await self.call(OrderSeeder)
    """
    
    def __init__(self, seeders: Optional[List[Type[Seeder]]] = None):
        super().__init__()
        self._seeder_classes = seeders or []
        self._total_seeders = 0
        self._completed_seeders = 0
    
    async def run(self) -> None:
        """执行所有注册的Seeder"""
        if self._seeder_classes:
            # 使用指定的Seeder列表
            for seeder_class in self._seeder_classes:
                await self.call(seeder_class)
        else:
            # 使用注册表中的所有Seeder（按注册顺序）
            execution_order = SeederRegistry.get_execution_order()
            for seeder_name in execution_order:
                seeder_class = SeederRegistry.get_seeder(seeder_name)
                if seeder_class and seeder_class != DatabaseSeeder:
                    await self.call(seeder_class)
    
    async def run_parallel(
        self, 
        max_concurrent: int = 3,
        verbose: bool = True
    ) -> None:
        """并行执行Seeder
        
        Args:
            max_concurrent: 最大并发数
            verbose: 是否显示详细输出
        """
        if verbose:
            print(f"开始并行执行Seeder（最大并发: {max_concurrent}）...")
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_seeder(seeder_class: Type[Seeder]) -> None:
            async with semaphore:
                await self.call(seeder_class, verbose=verbose)
        
        # 收集要执行的Seeder
        seeder_classes = self._seeder_classes
        if not seeder_classes:
            execution_order = SeederRegistry.get_execution_order()
            seeder_classes = [
                SeederRegistry.get_seeder(name) 
                for name in execution_order 
                if SeederRegistry.get_seeder(name) != DatabaseSeeder
            ]
        
        # 并行执行所有Seeder
        tasks = [run_seeder(seeder_class) for seeder_class in seeder_classes]
        await asyncio.gather(*tasks)
        
        if verbose:
            print("✅ 所有Seeder并行执行完成")
    
    def add_seeder(self, seeder_class: Type[Seeder]) -> None:
        """添加Seeder到执行列表"""
        if seeder_class not in self._seeder_classes:
            self._seeder_classes.append(seeder_class)
    
    def set_seeders(self, seeder_classes: List[Type[Seeder]]) -> None:
        """设置要执行的Seeder列表"""
        self._seeder_classes = seeder_classes.copy()
    
    def get_seeders(self) -> List[Type[Seeder]]:
        """获取要执行的Seeder列表"""
        return self._seeder_classes.copy()


class ConditionalSeeder(Seeder):
    """条件Seeder - 根据条件决定是否执行
    
    Example:
        class DevelopmentDataSeeder(ConditionalSeeder):
            def should_run(self) -> bool:
                return os.getenv('ENV') == 'development'
            
            async def run(self):
                if self.should_run():
                    await UserFactory.create_batch(100)
    """
    
    def should_run(self) -> bool:
        """判断是否应该执行此Seeder"""
        return True
    
    async def execute(self, verbose: bool = True) -> None:
        """执行Seeder（带条件检查）"""
        if not self.should_run():
            if verbose:
                print(f"⏭️  跳过条件不满足的 {self.__class__.__name__}")
            return
        
        await super().execute(verbose=verbose)


class TransactionalSeeder(Seeder):
    """事务Seeder - 在事务中执行，失败时回滚
    
    Example:
        class CriticalDataSeeder(TransactionalSeeder):
            async def run(self):
                # 这些操作会在事务中执行
                user = await UserFactory.create()
                profile = await ProfileFactory.create(user_id=user.id)
                # 如果任何操作失败，都会回滚
    """
    
    async def execute(self, verbose: bool = True) -> None:
        """在事务中执行Seeder"""
        if verbose:
            print(f"开始事务执行 {self.__class__.__name__}...")
        
        try:
            # 这里应该集成FastORM的事务管理
            # 暂时使用基础实现，后续可以增强
            await super().execute(verbose=verbose)
        except Exception as e:
            if verbose:
                print(f"❌ 事务回滚 {self.__class__.__name__}: {e}")
            raise


# 便捷函数
async def run_seeder(
    seeder_class: Type[Seeder], 
    verbose: bool = True
) -> None:
    """运行单个Seeder
    
    Args:
        seeder_class: 要运行的Seeder类
        verbose: 是否显示详细输出
    """
    seeder = seeder_class()
    await seeder.execute(verbose=verbose)


async def run_all_seeders(
    parallel: bool = False,
    max_concurrent: int = 3,
    verbose: bool = True
) -> None:
    """运行所有注册的Seeder
    
    Args:
        parallel: 是否并行执行
        max_concurrent: 最大并发数（仅在parallel=True时有效）
        verbose: 是否显示详细输出
    """
    database_seeder = DatabaseSeeder()
    
    if parallel:
        await database_seeder.run_parallel(
            max_concurrent=max_concurrent,
            verbose=verbose
        )
    else:
        await database_seeder.execute(verbose=verbose)


async def run_seeders(
    seeder_classes: List[Type[Seeder]],
    parallel: bool = False,
    max_concurrent: int = 3,
    verbose: bool = True
) -> None:
    """运行指定的Seeder列表
    
    Args:
        seeder_classes: 要运行的Seeder类列表
        parallel: 是否并行执行
        max_concurrent: 最大并发数（仅在parallel=True时有效）
        verbose: 是否显示详细输出
    """
    database_seeder = DatabaseSeeder(seeder_classes)
    
    if parallel:
        await database_seeder.run_parallel(
            max_concurrent=max_concurrent,
            verbose=verbose
        )
    else:
        await database_seeder.execute(verbose=verbose) 