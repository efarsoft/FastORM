"""
FastORM Queries Mixin

参照ThinkORM 4设计的查询增强混入类
提供简洁的静态查询方法
"""

from typing import Any, Dict, List, Optional, Union, Type, TYPE_CHECKING
from sqlalchemy import select, delete, update
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from fastorm.model.model import Model


class QueriesMixin:
    """
    查询增强混入类
    
    提供类似ThinkORM的简洁查询API
    """
    
    @classmethod
    async def find(cls, pk: Any) -> Optional['Model']:
        """
        根据主键查找记录
        
        Args:
            pk: 主键值
            
        Returns:
            模型实例或None
        """
        from fastorm.connection.session import get_session
        
        async with get_session() as session:
            stmt = select(cls).where(cls.id == pk)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()
            
            if instance:
                # 创建模型实例并填充数据
                model = cls()
                model._fill_from_db(instance)
                return model
            return None
    
    @classmethod
    async def find_or_fail(cls, pk: Any) -> 'Model':
        """
        根据主键查找记录，找不到则抛出异常
        
        Args:
            pk: 主键值
            
        Returns:
            模型实例
            
        Raises:
            NoResultFound: 记录不存在
        """
        result = await cls.find(pk)
        if result is None:
            raise NoResultFound(f"No {cls.__name__} found with id {pk}")
        return result
    
    @classmethod
    async def first(cls) -> Optional['Model']:
        """
        获取第一条记录
        
        Returns:
            模型实例或None
        """
        from fastorm.connection.session import get_session
        
        async with get_session() as session:
            stmt = select(cls).limit(1)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()
            
            if instance:
                model = cls()
                model._fill_from_db(instance)
                return model
            return None
    
    @classmethod
    async def first_or_fail(cls) -> 'Model':
        """
        获取第一条记录，找不到则抛出异常
        
        Returns:
            模型实例
            
        Raises:
            NoResultFound: 记录不存在
        """
        result = await cls.first()
        if result is None:
            raise NoResultFound(f"No {cls.__name__} records found")
        return result
    
    @classmethod
    async def last(cls) -> Optional['Model']:
        """
        获取最后一条记录（按主键倒序）
        
        Returns:
            模型实例或None
        """
        from fastorm.connection.session import get_session
        
        async with get_session() as session:
            stmt = select(cls).order_by(cls.id.desc()).limit(1)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()
            
            if instance:
                model = cls()
                model._fill_from_db(instance)
                return model
            return None
    
    @classmethod
    async def all(cls) -> List['Model']:
        """
        获取所有记录
        
        Returns:
            模型实例列表
        """
        from fastorm.connection.session import get_session
        
        async with get_session() as session:
            stmt = select(cls)
            result = await session.execute(stmt)
            instances = result.scalars().all()
            
            models = []
            for instance in instances:
                model = cls()
                model._fill_from_db(instance)
                models.append(model)
            return models
    
    @classmethod
    async def create(cls, **data) -> 'Model':
        """
        创建新记录
        
        Args:
            **data: 字段数据
            
        Returns:
            创建的模型实例
        """
        model = cls()
        model.fill(data)
        await model.save()
        return model
    
    @classmethod
    async def create_many(cls, data_list: List[Dict[str, Any]]) -> List['Model']:
        """
        批量创建记录
        
        Args:
            data_list: 数据列表
            
        Returns:
            创建的模型实例列表
        """
        models = []
        for data in data_list:
            model = await cls.create(**data)
            models.append(model)
        return models
    
    @classmethod
    async def update_or_create(cls, defaults: Dict[str, Any], 
                              **lookup) -> tuple['Model', bool]:
        """
        更新或创建记录
        
        Args:
            defaults: 默认值
            **lookup: 查找条件
            
        Returns:
            (模型实例, 是否创建)
        """
        # 先尝试查找
        query = cls.where(**lookup)
        instance = await query.first()
        
        if instance:
            # 更新现有记录
            await instance.update(**defaults)
            return instance, False
        else:
            # 创建新记录
            create_data = {**lookup, **defaults}
            instance = await cls.create(**create_data)
            return instance, True
    
    @classmethod
    async def destroy(cls, ids: Union[Any, List[Any]]) -> int:
        """
        根据主键批量删除记录
        
        Args:
            ids: 主键或主键列表
            
        Returns:
            删除的记录数
        """
        from fastorm.connection.session import get_session
        
        if not isinstance(ids, list):
            ids = [ids]
        
        async with get_session() as session:
            stmt = delete(cls).where(cls.id.in_(ids))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
    
    @classmethod
    async def count(cls) -> int:
        """
        统计记录数
        
        Returns:
            记录数
        """
        from fastorm.connection.session import get_session
        from sqlalchemy import func
        
        async with get_session() as session:
            stmt = select(func.count(cls.id))
            result = await session.execute(stmt)
            return result.scalar()
    
    @classmethod
    async def exists(cls) -> bool:
        """
        检查是否存在记录
        
        Returns:
            是否存在
        """
        count = await cls.count()
        return count > 0
    
    @classmethod
    def where(cls, *args, **kwargs):
        """
        添加where条件
        
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).where(*args, **kwargs)
    
    @classmethod
    def select(cls, *columns):
        """
        指定选择的列
        
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).select(*columns)
    
    @classmethod
    def order_by(cls, *args):
        """
        添加排序
        
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).order_by(*args)
    
    @classmethod
    def limit(cls, count: int):
        """
        限制结果数量
        
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).limit(count)
    
    @classmethod
    def offset(cls, count: int):
        """
        设置偏移量
        
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).offset(count)
    
    @classmethod
    def paginate(cls, page: int = 1, per_page: int = 15):
        """
        分页查询
        
        Args:
            page: 页码
            per_page: 每页记录数
            
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).paginate(page, per_page)
    
    @classmethod
    def with_relations(cls, *relations):
        """
        预加载关联关系
        
        Args:
            *relations: 关联关系名称
            
        Returns:
            查询构建器实例
        """
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).with_relations(*relations)
    
    def _fill_from_db(self, db_instance) -> None:
        """
        从数据库实例填充模型数据
        
        Args:
            db_instance: SQLAlchemy实例
        """
        if hasattr(self, '_attributes'):
            # 填充属性
            for column in self.__table__.columns:
                value = getattr(db_instance, column.name, None)
                self._attributes[column.name] = value
            # 同步原始值
            self.sync_original()


class ScopesMixin:
    """
    查询作用域混入类
    
    提供查询作用域功能
    """
    
    @classmethod
    def _apply_scope(cls, query, scope_name: str, *args, **kwargs):
        """
        应用查询作用域
        
        Args:
            query: 查询构建器
            scope_name: 作用域名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            应用作用域后的查询构建器
        """
        scope_method = f"scope_{scope_name}"
        if hasattr(cls, scope_method):
            scope_func = getattr(cls, scope_method)
            return scope_func(query, *args, **kwargs)
        return query
    
    def __getattr__(self, name: str):
        """
        动态调用作用域方法
        """
        if name.startswith('scope_'):
            # 直接访问作用域方法
            return super().__getattribute__(name)
        
        # 检查是否为作用域调用
        scope_method = f"scope_{name}"
        if hasattr(self.__class__, scope_method):
            def scope_caller(*args, **kwargs):
                if isinstance(self, type):
                    # 类方法调用
                    from fastorm.query.builder import QueryBuilder
                    query = QueryBuilder(self)
                    return self._apply_scope(query, name, *args, **kwargs)
                else:
                    # 实例方法调用
                    return self._apply_scope(self, name, *args, **kwargs)
            return scope_caller
        
        # 继续正常的属性访问
        return super().__getattribute__(name)


# 示例用法
"""
from fastorm.mixins.queries import QueriesMixin, ScopesMixin

class User(Model, QueriesMixin, ScopesMixin):
    # 定义查询作用域
    @staticmethod
    def scope_active(query):
        return query.where('status', 'active')
    
    @staticmethod  
    def scope_recent(query):
        return query.order_by('created_at', 'desc')
    
    @staticmethod
    def scope_by_age(query, min_age, max_age):
        return query.where('age', '>=', min_age).where('age', '<=', max_age)

# 使用示例
# 基础查询
user = await User.find(1)                    # 主键查找
user = await User.find_or_fail(1)            # 查找失败抛异常
users = await User.all()                     # 获取所有
user = await User.first()                    # 第一条记录

# 创建
user = await User.create(name='张三', email='test@example.com')
users = await User.create_many([
    {'name': '李四', 'email': 'li@example.com'},
    {'name': '王五', 'email': 'wang@example.com'}
])

# 更新或创建
user, created = await User.update_or_create(
    {'email': 'test@example.com'},
    name='张三更新'
)

# 删除
count = await User.destroy([1, 2, 3])        # 批量删除

# 统计
count = await User.count()                   # 总数
exists = await User.exists()                 # 是否存在

# 链式查询
users = await User.where('status', 'active').order_by('created_at').limit(10).get()
user = await User.where('email', 'test@example.com').first()

# 作用域使用
users = await User.active().recent().limit(10).get()
users = await User.by_age(18, 65).active().get()

# 分页
page = await User.active().paginate(page=1, per_page=20)

# 预加载关系
users = await User.with_relations('posts', 'profile').limit(10).get()
""" 