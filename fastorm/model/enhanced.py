"""
FastORM 增强模型

实现真正简洁如ThinkORM的API。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from fastorm.model.base import BaseModel as OriginalBaseModel
from fastorm.core.session_manager import execute_with_session

T = TypeVar('T', bound='Model')


class Model(OriginalBaseModel):
    """增强的模型基类
    
    实现真正简洁的API，无需手动管理session。
    
    示例:
    ```python
    # 🎯 简洁如ThinkORM
    user = await User.create(name='John', email='john@example.com')
    users = await User.where('age', '>', 18).limit(10).get()
    await user.update(name='Jane')
    await user.delete()
    ```
    """
    
    __abstract__ = True
    
    # =================================================================
    # 简洁的创建和查询方法
    # =================================================================
    
    @classmethod
    async def create(cls: Type[T], **values: Any) -> T:
        """创建新记录 - 无需session参数！
        
        Args:
            **values: 字段值
            
        Returns:
            创建的模型实例
            
        Example:
            user = await User.create(name='John', email='john@example.com')
        """
        async def _create(session: AsyncSession) -> T:
            return await super(Model, cls).create(session, **values)
        
        return await execute_with_session(_create)
    
    @classmethod
    async def find(cls: Type[T], id: Any) -> Optional[T]:
        """通过主键查找记录 - 无需session参数！
        
        Args:
            id: 主键值
            
        Returns:
            模型实例或None
            
        Example:
            user = await User.find(1)
        """
        async def _find(session: AsyncSession) -> Optional[T]:
            return await super(Model, cls).find(session, id)
        
        return await execute_with_session(_find)
    
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
            return await super(Model, cls).find_or_fail(session, id)
        
        return await execute_with_session(_find_or_fail)
    
    @classmethod
    async def all(cls: Type[T]) -> List[T]:
        """获取所有记录 - 无需session参数！
        
        Returns:
            所有记录列表
            
        Example:
            users = await User.all()
        """
        async def _all(session: AsyncSession) -> List[T]:
            return await super(Model, cls).all(session)
        
        return await execute_with_session(_all)
    
    @classmethod
    async def count(cls: Type[T]) -> int:
        """统计记录数量 - 无需session参数！
        
        Returns:
            记录数量
            
        Example:
            count = await User.count()
        """
        async def _count(session: AsyncSession) -> int:
            result = await session.execute(select(func.count()).select_from(cls))
            return result.scalar() or 0
        
        return await execute_with_session(_count)
    
    # =================================================================
    # 便捷的查询方法
    # =================================================================
    
    @classmethod
    async def first(cls: Type[T]) -> Optional[T]:
        """获取第一条记录
        
        Returns:
            第一条记录或None
            
        Example:
            user = await User.first()
        """
        async def _first(session: AsyncSession) -> Optional[T]:
            result = await session.execute(select(cls).limit(1))
            return result.scalars().first()
        
        return await execute_with_session(_first)
    
    @classmethod
    async def last(cls: Type[T]) -> Optional[T]:
        """获取最后一条记录
        
        Returns:
            最后一条记录或None
            
        Example:
            user = await User.last()
        """
        async def _last(session: AsyncSession) -> Optional[T]:
            # 假设有id字段作为主键
            result = await session.execute(
                select(cls).order_by(cls.id.desc()).limit(1)
            )
            return result.scalars().first()
        
        return await execute_with_session(_last)
    
    # =================================================================
    # 便捷的批量操作
    # =================================================================
    
    @classmethod
    async def create_many(cls: Type[T], records: List[Dict[str, Any]]) -> List[T]:
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
        """统计符合条件的记录数量
        
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
        """保存当前实例 - 无需session参数！
        
        Example:
            user.name = 'Jane'
            await user.save()
        """
        async def _save(session: AsyncSession) -> None:
            await super(Model, self).save(session)
        
        await execute_with_session(_save)
    
    async def delete(self) -> None:
        """删除当前实例 - 无需session参数！
        
        Example:
            await user.delete()
        """
        async def _delete(session: AsyncSession) -> None:
            await super(Model, self).remove(session)
        
        await execute_with_session(_delete)
    
    async def update(self, **values: Any) -> None:
        """更新当前实例 - 无需session参数！
        
        Args:
            **values: 要更新的字段值
            
        Example:
            await user.update(name='Jane', email='jane@example.com')
        """
        for key, value in values.items():
            if hasattr(self, key):
                setattr(self, key, value)
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
    # 链式查询构建器 - 增强版
    # =================================================================
    
    @classmethod
    def where(
        cls: Type[T], 
        column: str, 
        operator: Union[str, Any] = "=", 
        value: Any = None
    ) -> 'EnhancedQueryBuilder[T]':
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
        from fastorm.query.enhanced import EnhancedQueryBuilder
        
        # 处理参数重载
        if value is None:
            # where('name', 'John') 形式
            actual_operator = "="
            actual_value = operator
        else:
            # where('age', '>', 18) 形式
            actual_operator = operator
            actual_value = value
        
        return EnhancedQueryBuilder(cls).where(column, actual_operator, actual_value)
    
    @classmethod
    def query(cls: Type[T]) -> 'EnhancedQueryBuilder[T]':
        """创建查询构建器
        
        Returns:
            查询构建器实例
            
        Example:
            users = await User.query().where('age', '>', 18).order_by('name').get()
        """
        from fastorm.query.enhanced import EnhancedQueryBuilder
        return EnhancedQueryBuilder(cls) 