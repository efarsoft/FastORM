"""
FastORM 模型

实现真正简洁如ThinkORM的API。
"""

from __future__ import annotations

from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Union, TYPE_CHECKING
)

from sqlalchemy import MetaData, select, delete, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    DeclarativeBase as SQLAlchemyDeclarativeBase, 
    declared_attr,
    Mapped,
    mapped_column
)

from fastorm.core.session_manager import execute_with_session
from fastorm.mixins.events import EventMixin
from fastorm.mixins.pydantic_integration import PydanticIntegrationMixin
from fastorm.mixins.scopes import ScopeMixin, create_scoped_query

if TYPE_CHECKING:
    from fastorm.query.builder import QueryBuilder

T = TypeVar('T', bound='Model')


class DeclarativeBase(SQLAlchemyDeclarativeBase):
    """SQLAlchemy 2.0 声明式基类
    
    使用最新的SQLAlchemy 2.0特性：
    - 🔧 优化的元数据配置
    - 🚀 编译缓存支持  
    - 📊 查询计划缓存
    """
    
    # SQLAlchemy 2.0.40+ 元数据优化
    metadata = MetaData(
        # 启用编译缓存以提升性能
        info={
            "compiled_cache": {},
            "render_postcompile": True,
        }
    )


class Model(DeclarativeBase, EventMixin, PydanticIntegrationMixin, ScopeMixin):
    """FastORM模型基类
    
    实现真正简洁的API，无需手动管理session，自动集成事件系统和Pydantic V2验证。
    
    示例:
    ```python
    # 🎯 简洁如ThinkORM + 事件支持 + Pydantic验证
    user = await User.create(name='John', email='john@example.com')
    users = await User.where('age', '>', 18).limit(10).get()
    await user.update(name='Jane')
    await user.delete()
    
    # Pydantic验证和序列化
    user_dict = user.to_dict()
    user_json = user.to_json()
    schema = User.get_pydantic_schema()
    
    # 事件处理器自动工作
    class User(Model):
        def on_before_insert(self):
            print(f"准备创建用户: {self.name}")
    ```
    """
    
    __abstract__ = True
    
    # 通用主键字段（子类可以覆盖）
    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # =================================================================
    # 简洁的创建和查询方法
    # =================================================================
    
    @classmethod
    async def create(cls: Type[T], **values: Any) -> T:
        """创建新记录 - 无需session参数，自动触发事件！自动使用写库
        
        Args:
            **values: 字段值
            
        Returns:
            创建的模型实例
            
        Example:
            user = await User.create(name='John', email='john@example.com')
        """
        async def _create(session: AsyncSession) -> T:
            instance = cls(**values)
            
            # 触发 before_insert 事件
            await instance.fire_event('before_insert')
            
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            
            # 触发 after_insert 事件  
            await instance.fire_event('after_insert')
            
            # 在记录创建完成后保存其状态作为原始状态
            instance._reset_original_state()
            
            return instance
        
        # 创建操作使用写库
        return await execute_with_session(_create, connection_type="write")
    
    @classmethod
    async def find(cls: Type[T], id: Any, *, force_write: bool = False) -> Optional[T]:
        """通过主键查找记录 - 无需session参数！自动使用读库
        
        Args:
            id: 主键值
            force_write: 强制使用写库（用于读自己的写等场景）
            
        Returns:
            模型实例或None
            
        Example:
            user = await User.find(1)  # 使用读库
            user = await User.find(1, force_write=True)  # 强制使用写库
        """
        async def _find(session: AsyncSession) -> Optional[T]:
            return await session.get(cls, id)
        
        connection_type = "write" if force_write else "read"
        return await execute_with_session(_find, connection_type=connection_type)
    
    @classmethod
    async def find_or_fail(cls: Type[T], id: Any) -> T:
        """通过主键查找记录，不存在则抛出异常 - 无需session参数！
        
        Args:
            id: 主键值
            
        Returns:
            模型实例
            
        Raises:
            ValueError: 记录不存在
            
        Example:
            user = await User.find_or_fail(1)
        """
        async def _find_or_fail(session: AsyncSession) -> T:
            instance = await session.get(cls, id)
            if instance is None:
                raise ValueError(f"{cls.__name__} with id {id} not found")
            return instance
        
        return await execute_with_session(_find_or_fail)
    
    @classmethod
    async def all(cls: Type[T]) -> List[T]:
        """获取所有记录 - 无需session参数！使用读库
        
        Returns:
            所有记录列表
            
        Example:
            users = await User.all()
        """
        async def _all(session: AsyncSession) -> List[T]:
            result = await session.execute(select(cls))
            return list(result.scalars().all())
        
        return await execute_with_session(_all, connection_type="read")
    
    @classmethod
    async def count(cls: Type[T]) -> int:
        """统计记录数量 - 无需session参数！使用读库
        
        Returns:
            记录数量
            
        Example:
            count = await User.count()
        """
        async def _count(session: AsyncSession) -> int:
            result = await session.execute(
                select(func.count()).select_from(cls)
            )
            return result.scalar() or 0
        
        return await execute_with_session(_count, connection_type="read")
    
    # =================================================================
    # 便捷的查询方法
    # =================================================================
    
    @classmethod
    async def first(cls: Type[T]) -> Optional[T]:
        """获取第一条记录，使用读库
        
        Returns:
            第一条记录或None
            
        Example:
            user = await User.first()
        """
        async def _first(session: AsyncSession) -> Optional[T]:
            result = await session.execute(select(cls).limit(1))
            return result.scalars().first()
        
        return await execute_with_session(_first, connection_type="read")
    
    @classmethod
    async def last(cls: Type[T]) -> Optional[T]:
        """获取最后一条记录，使用读库
        
        Returns:
            最后一条记录或None
            
        Example:
            user = await User.last()
        """
        async def _last(session: AsyncSession) -> Optional[T]:
            # 假设有id字段作为主键，尝试获取
            try:
                result = await session.execute(
                    select(cls).order_by(cls.id.desc()).limit(1)  # type: ignore  # noqa: E501
                )
                return result.scalars().first()
            except AttributeError:
                # 如果没有id字段，获取最后插入的记录
                result = await session.execute(select(cls))
                records = list(result.scalars().all())
                return records[-1] if records else None
        
        return await execute_with_session(_last, connection_type="read")
    
    # =================================================================
    # 便捷的批量操作
    # =================================================================
    
    @classmethod
    async def create_many(
        cls: Type[T], 
        records: List[Dict[str, Any]]
    ) -> List[T]:
        """批量创建记录
        
        Args:
            records: 记录数据列表
            
        Returns:
            创建的模型实例列表
            
        Example:
            users = await User.create_many([
                {'name': 'John', 'email': 'john@example.com'},
                {'name': 'Jane', 'email': 'jane@example.com'}
            ])
        """
        async def _create_many(session: AsyncSession) -> List[T]:
            instances = [cls(**record) for record in records]
            session.add_all(instances)
            await session.flush()
            for instance in instances:
                await session.refresh(instance)
            return instances
        
        return await execute_with_session(_create_many)
    
    @classmethod
    async def delete_where(cls: Type[T], column: str, value: Any) -> int:
        """删除符合条件的记录
        
        Args:
            column: 列名
            value: 值
            
        Returns:
            删除的记录数量
            
        Example:
            count = await User.delete_where('age', 0)
        """
        async def _delete_where(session: AsyncSession) -> int:
            column_attr = getattr(cls, column)
            result = await session.execute(
                delete(cls).where(column_attr == value)
            )
            return result.rowcount or 0
        
        return await execute_with_session(_delete_where)
    
    @classmethod
    async def count_where(cls: Type[T], column: str, value: Any) -> int:
        """统计符合条件的记录数量，使用读库
        
        Args:
            column: 列名
            value: 值
            
        Returns:
            记录数量
            
        Example:
            count = await User.count_where('status', 'active')
        """
        async def _count_where(session: AsyncSession) -> int:
            column_attr = getattr(cls, column)
            result = await session.execute(
                select(func.count()).select_from(cls).where(
                    column_attr == value
                )
            )
            return result.scalar() or 0
        
        return await execute_with_session(_count_where)
    
    # =================================================================
    # 实例方法 - 简洁的更新和删除
    # =================================================================
    
    async def save(self) -> None:
        """保存当前实例 - 无需session参数，自动触发事件！
        
        Example:
            user.name = 'Jane'
            await user.save()
        """
        async def _save(session: AsyncSession) -> None:
            # 保存原始状态用于事件和脏检查
            self._save_original_state()
            
            # 判断是新增还是更新
            is_new = self.is_new_record()
            
            if is_new:
                # 新增记录
                await self.fire_event('before_insert')
                session.add(self)
                await session.flush()
                await session.refresh(self)
                await self.fire_event('after_insert')
            else:
                # 更新记录
                await self.fire_event('before_update')
                session.add(self)
                await session.flush()
                await self.fire_event('after_update')
            
            # 重置状态标志，为下次保存做准备
            self._reset_original_state()
        
        await execute_with_session(_save)
    
    async def delete(self) -> None:
        """删除当前实例 - 无需session参数，自动触发事件！
        
        Example:
            await user.delete()
        """
        async def _delete(session: AsyncSession) -> None:
            # 触发 before_delete 事件
            await self.fire_event('before_delete')
            
            await session.delete(self)
            await session.flush()
            
            # 触发 after_delete 事件
            await self.fire_event('after_delete')
        
        await execute_with_session(_delete)
    
    async def update(self, **values: Any) -> None:
        """更新当前实例 - 无需session参数，自动触发事件！
        
        Args:
            **values: 要更新的字段值
            
        Example:
            await user.update(name='Jane', email='jane@example.com')
        """
        # 保存原始状态
        self._save_original_state()
        
        # 更新字段值
        for key, value in values.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # 直接保存，由save()方法统一处理事件触发
        await self.save()
    
    async def refresh(self) -> None:
        """刷新当前实例数据
        
        Example:
            await user.refresh()
        """
        async def _refresh(session: AsyncSession) -> None:
            await session.refresh(self)
        
        await execute_with_session(_refresh)
    
    # =================================================================
    # 链式查询构建器
    # =================================================================
    
    @classmethod
    def where(
        cls: Type[T], 
        column: str, 
        operator: Union[str, Any] = "=", 
        value: Any = None
    ) -> 'QueryBuilder[T]':
        """开始构建查询 - 支持操作符
        
        Args:
            column: 列名
            operator: 操作符或值（如果省略value）
            value: 值
            
        Returns:
            查询构建器
            
        Example:
            users = await User.where('age', '>', 18).get()
            users = await User.where('name', 'John').get()
        """
        from fastorm.query.builder import QueryBuilder
        
        # 处理参数重载
        if value is None:
            # where('name', 'John') 形式
            actual_operator = "="
            actual_value = operator
        else:
            # where('age', '>', 18) 形式
            actual_operator = operator
            actual_value = value
        
        return QueryBuilder(cls).where(
            column, actual_operator, actual_value
        )
    
    @classmethod
    def query(cls: Type[T]) -> 'QueryBuilder[T]':
        """创建作用域查询构建器
        
        Returns:
            作用域查询构建器实例（自动应用全局作用域）
            
        Example:
            # 基础查询
            users = await User.query().where('age', '>', 18).get()
            
            # 使用作用域
            active_users = await User.query().active().get()
            
            # 移除全局作用域
            all_users = await User.query().without_global_scopes().get()
        """
        return create_scoped_query(cls)
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """转换为字典
        
        Args:
            exclude: 要排除的字段列表
            
        Returns:
            字典表示
        """
        exclude = exclude or []
        result = {}
        
        if hasattr(self, '__table__'):
            for column in self.__table__.columns:
                if column.name not in exclude:
                    value = getattr(self, column.name)
                    # 处理日期时间类型
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    result[column.name] = value
        
        return result 