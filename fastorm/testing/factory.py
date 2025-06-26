"""
FastORM 模型工厂系统

实现类似Django Factory Boy和Laravel Model Factory的功能。

示例:
```python
class UserFactory(Factory):
    class Meta:
        model = User
    
    name = faker.name()
    email = faker.email()
    age = faker.random_int(min=18, max=80)
    
    @trait
    def admin(self):
        return {'role': 'admin', 'is_staff': True}
    
    @trait
    def with_posts(self):
        return {'posts_count': 5}

# 使用方式
user = await UserFactory.create()
users = await UserFactory.create_batch(10)
admin = await UserFactory.create(trait='admin')
```
"""

from __future__ import annotations

import inspect
import random
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Callable, Union,
    get_type_hints, TYPE_CHECKING
)
from functools import wraps

if TYPE_CHECKING:
    from fastorm.model.model import Model

T = TypeVar('T', bound='Model')


class LazyAttribute:
    """延迟属性 - 在创建时才计算值"""
    
    def __init__(self, function: Callable[[], Any]):
        self.function = function
    
    def evaluate(self, instance: Any = None) -> Any:
        """计算属性值"""
        if instance:
            return self.function(instance)
        return self.function()


class Sequence:
    """序列属性 - 生成递增的序列值"""
    
    def __init__(self, function: Callable[[int], Any], start: int = 1):
        self.function = function
        self.start = start
        self._counter = start
    
    def next(self) -> Any:
        """获取下一个序列值"""
        value = self.function(self._counter)
        self._counter += 1
        return value
    
    def reset(self, start: Optional[int] = None) -> None:
        """重置序列计数器"""
        self._counter = start if start is not None else self.start


class FactoryTrait:
    """工厂特征 - 定义可复用的属性集合"""
    
    def __init__(self, name: str, attributes: Dict[str, Any]):
        self.name = name
        self.attributes = attributes
    
    def apply(self, base_attributes: Dict[str, Any]) -> Dict[str, Any]:
        """应用特征到基础属性"""
        result = base_attributes.copy()
        result.update(self.attributes)
        return result


def trait(name: Optional[str] = None):
    """特征装饰器
    
    Args:
        name: 特征名称，如果不提供则使用函数名
    
    Example:
        @trait
        def admin(self):
            return {'role': 'admin', 'is_staff': True}
    """
    def decorator(func: Callable) -> Callable:
        trait_name = name or func.__name__
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        
        wrapper._is_trait = True
        wrapper._trait_name = trait_name
        return wrapper
    
    return decorator


class FactoryMetaclass(type):
    """工厂元类 - 处理工厂类的创建"""
    
    def __new__(
        mcs, 
        name: str, 
        bases: tuple, 
        namespace: Dict[str, Any], 
        **kwargs
    ):
        # 收集属性定义
        attributes = {}
        traits = {}
        sequences = {}
        
        # 从父类继承属性
        for base in bases:
            if hasattr(base, '_attributes'):
                attributes.update(base._attributes)
            if hasattr(base, '_traits'):
                traits.update(base._traits)
            if hasattr(base, '_sequences'):
                sequences.update(base._sequences)
        
        # 处理当前类的属性
        for key, value in list(namespace.items()):
            if key.startswith('_') or key == 'Meta':
                continue
            
            # 处理特征方法
            if (callable(value) and 
                hasattr(value, '_is_trait') and 
                value._is_trait):
                traits[value._trait_name] = value
                continue
            
            # 处理序列属性
            if isinstance(value, Sequence):
                sequences[key] = value
                continue
            
            # 处理普通属性
            if not callable(value) or isinstance(value, LazyAttribute):
                attributes[key] = value
        
        # 创建新类
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        
        # 设置类属性
        cls._attributes = attributes
        cls._traits = traits
        cls._sequences = sequences
        
        # 处理Meta配置
        if hasattr(cls, 'Meta'):
            cls._model_class = getattr(cls.Meta, 'model', None)
            cls._default_count = getattr(cls.Meta, 'default_count', 1)
        else:
            cls._model_class = None
            cls._default_count = 1
        
        return cls


class Factory(metaclass=FactoryMetaclass):
    """模型工厂基类
    
    提供声明式的模型实例创建功能。
    
    Example:
        class UserFactory(Factory):
            class Meta:
                model = User
            
            name = faker.name()
            email = faker.email()
            age = LazyAttribute(lambda: random.randint(18, 80))
            username = Sequence(lambda n: f"user{n}")
            
            @trait
            def admin(self):
                return {'role': 'admin', 'is_staff': True}
    """
    
    _attributes: Dict[str, Any] = {}
    _traits: Dict[str, Callable] = {}
    _sequences: Dict[str, Sequence] = {}
    _model_class: Optional[Type[T]] = None
    _default_count: int = 1
    
    class Meta:
        """工厂元数据配置"""
        model: Optional[Type[T]] = None
        default_count: int = 1
    
    @classmethod
    async def create(
        cls, 
        trait: Optional[str] = None,
        **overrides: Any
    ) -> T:
        """创建单个模型实例
        
        Args:
            trait: 要应用的特征名称
            **overrides: 覆盖的属性值
            
        Returns:
            创建的模型实例
            
        Example:
            user = await UserFactory.create()
            admin = await UserFactory.create(trait='admin')
            user = await UserFactory.create(name='John', age=25)
        """
        if not cls._model_class:
            raise ValueError(f"Factory {cls.__name__} must define a model in Meta")
        
        # 构建属性字典
        attributes = await cls._build_attributes(trait=trait, **overrides)
        
        # 创建模型实例
        instance = await cls._model_class.create(**attributes)
        
        return instance
    
    @classmethod
    async def create_batch(
        cls, 
        count: int,
        trait: Optional[str] = None,
        **overrides: Any
    ) -> List[T]:
        """批量创建模型实例
        
        Args:
            count: 创建数量
            trait: 要应用的特征名称
            **overrides: 覆盖的属性值
            
        Returns:
            创建的模型实例列表
            
        Example:
            users = await UserFactory.create_batch(10)
            admins = await UserFactory.create_batch(5, trait='admin')
        """
        instances = []
        
        for _ in range(count):
            instance = await cls.create(trait=trait, **overrides)
            instances.append(instance)
        
        return instances
    
    @classmethod
    async def build(
        cls, 
        trait: Optional[str] = None,
        **overrides: Any
    ) -> T:
        """构建模型实例但不保存到数据库
        
        Args:
            trait: 要应用的特征名称
            **overrides: 覆盖的属性值
            
        Returns:
            构建的模型实例（未保存）
            
        Example:
            user = await UserFactory.build()
            assert user.id is None  # 未保存到数据库
        """
        if not cls._model_class:
            raise ValueError(f"Factory {cls.__name__} must define a model in Meta")
        
        # 构建属性字典
        attributes = await cls._build_attributes(trait=trait, **overrides)
        
        # 创建模型实例但不保存
        instance = cls._model_class(**attributes)
        
        return instance
    
    @classmethod
    async def build_batch(
        cls, 
        count: int,
        trait: Optional[str] = None,
        **overrides: Any
    ) -> List[T]:
        """批量构建模型实例但不保存到数据库
        
        Args:
            count: 构建数量
            trait: 要应用的特征名称
            **overrides: 覆盖的属性值
            
        Returns:
            构建的模型实例列表（未保存）
        """
        instances = []
        
        for _ in range(count):
            instance = await cls.build(trait=trait, **overrides)
            instances.append(instance)
        
        return instances
    
    @classmethod
    async def _build_attributes(
        cls, 
        trait: Optional[str] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """构建属性字典
        
        Args:
            trait: 要应用的特征名称
            **overrides: 覆盖的属性值
            
        Returns:
            构建的属性字典
        """
        attributes = {}
        
        # 处理基础属性
        for key, value in cls._attributes.items():
            if isinstance(value, LazyAttribute):
                attributes[key] = value.evaluate()
            elif callable(value):
                # 假设是Faker提供者或其他可调用对象
                try:
                    attributes[key] = value()
                except Exception:
                    # 如果调用失败，使用原值
                    attributes[key] = value
            else:
                attributes[key] = value
        
        # 处理序列属性
        for key, sequence in cls._sequences.items():
            attributes[key] = sequence.next()
        
        # 应用特征
        if trait and trait in cls._traits:
            trait_method = cls._traits[trait]
            trait_attributes = trait_method(cls)
            if isinstance(trait_attributes, dict):
                attributes.update(trait_attributes)
        
        # 应用覆盖
        attributes.update(overrides)
        
        return attributes
    
    @classmethod
    def reset_sequences(cls) -> None:
        """重置所有序列计数器"""
        for sequence in cls._sequences.values():
            sequence.reset()
    
    @classmethod
    def get_available_traits(cls) -> List[str]:
        """获取可用的特征列表"""
        return list(cls._traits.keys())
    
    @classmethod
    def describe(cls) -> Dict[str, Any]:
        """描述工厂的配置信息"""
        return {
            'model': cls._model_class.__name__ if cls._model_class else None,
            'attributes': list(cls._attributes.keys()),
            'traits': list(cls._traits.keys()),
            'sequences': list(cls._sequences.keys()),
        }


class SubFactory:
    """子工厂 - 用于创建关联对象
    
    Example:
        class PostFactory(Factory):
            class Meta:
                model = Post
            
            title = faker.sentence()
            user = SubFactory(UserFactory)
    """
    
    def __init__(
        self, 
        factory_class: Type[Factory],
        trait: Optional[str] = None,
        **kwargs: Any
    ):
        self.factory_class = factory_class
        self.trait = trait
        self.kwargs = kwargs
    
    async def create(self) -> Any:
        """创建子对象"""
        return await self.factory_class.create(
            trait=self.trait, 
            **self.kwargs
        )


# 便捷函数
def lazy_attribute(func: Callable[[], Any]) -> LazyAttribute:
    """创建延迟属性的便捷函数
    
    Example:
        age = lazy_attribute(lambda: random.randint(18, 80))
    """
    return LazyAttribute(func)


def sequence(func: Callable[[int], Any], start: int = 1) -> Sequence:
    """创建序列属性的便捷函数
    
    Example:
        username = sequence(lambda n: f"user{n}")
        email = sequence(lambda n: f"user{n}@example.com")
    """
    return Sequence(func, start) 