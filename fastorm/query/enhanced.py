"""
FastORM 增强查询构建器

实现真正简洁的链式查询API。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic

from sqlalchemy import select, and_, asc, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from fastorm.core.session_manager import execute_with_session

T = TypeVar('T')


class EnhancedQueryBuilder(Generic[T]):
    """增强的查询构建器
    
    实现ThinkORM风格的简洁链式查询。
    
    示例:
    ```python
    # 🎯 简洁的链式查询
    users = await User.where('age', '>', 18)\
                     .where('status', 'active')\
                     .order_by('name')\
                     .limit(10)\
                     .get()
    ```
    """
    
    def __init__(self, model_class: Type[T]):
        self._model_class = model_class
        self._conditions = []
        self._order_clauses = []
        self._limit_value: Optional[int] = None
        self._offset_value: Optional[int] = None
        self._distinct_value: bool = False
    
    def where(
        self, 
        column: str, 
        operator: str = "=", 
        value: Any = None
    ) -> 'EnhancedQueryBuilder[T]':
        """添加WHERE条件
        
        Args:
            column: 列名
            operator: 操作符 ('=', '>', '<', '>=', '<=', '!=', 'like', 'in')
            value: 值
            
        Returns:
            查询构建器实例（支持链式调用）
            
        Example:
            User.where('age', '>', 18)
            User.where('name', 'like', '%John%')
            User.where('status', 'in', ['active', 'pending'])
        """
        column_attr = getattr(self._model_class, column)
        
        if operator.lower() == '=':
            condition = column_attr == value
        elif operator.lower() == '>':
            condition = column_attr > value
        elif operator.lower() == '<':
            condition = column_attr < value
        elif operator.lower() == '>=':
            condition = column_attr >= value
        elif operator.lower() == '<=':
            condition = column_attr <= value
        elif operator.lower() in ('!=', '<>'):
            condition = column_attr != value
        elif operator.lower() == 'like':
            condition = column_attr.like(value)
        elif operator.lower() == 'ilike':
            condition = column_attr.ilike(value)
        elif operator.lower() == 'in':
            condition = column_attr.in_(value)
        elif operator.lower() == 'not in':
            condition = ~column_attr.in_(value)
        elif operator.lower() == 'is null':
            condition = column_attr.is_(None)
        elif operator.lower() == 'is not null':
            condition = column_attr.is_not(None)
        else:
            raise ValueError(f"不支持的操作符: {operator}")
        
        self._conditions.append(condition)
        return self
    
    def where_in(self, column: str, values: List[Any]) -> 'EnhancedQueryBuilder[T]':
        """WHERE IN 查询
        
        Args:
            column: 列名
            values: 值列表
            
        Returns:
            查询构建器实例
            
        Example:
            User.where_in('status', ['active', 'pending'])
        """
        return self.where(column, 'in', values)
    
    def where_not_in(
        self, 
        column: str, 
        values: List[Any]
    ) -> 'EnhancedQueryBuilder[T]':
        """WHERE NOT IN 查询
        
        Args:
            column: 列名
            values: 值列表
            
        Returns:
            查询构建器实例
            
        Example:
            User.where_not_in('status', ['deleted', 'banned'])
        """
        return self.where(column, 'not in', values)
    
    def where_null(self, column: str) -> 'EnhancedQueryBuilder[T]':
        """WHERE IS NULL 查询
        
        Args:
            column: 列名
            
        Returns:
            查询构建器实例
            
        Example:
            User.where_null('deleted_at')
        """
        return self.where(column, 'is null')
    
    def where_not_null(self, column: str) -> 'EnhancedQueryBuilder[T]':
        """WHERE IS NOT NULL 查询
        
        Args:
            column: 列名
            
        Returns:
            查询构建器实例
            
        Example:
            User.where_not_null('email')
        """
        return self.where(column, 'is not null')
    
    def order_by(
        self, 
        column: str, 
        direction: str = 'asc'
    ) -> 'EnhancedQueryBuilder[T]':
        """添加排序
        
        Args:
            column: 列名
            direction: 排序方向 ('asc' 或 'desc')
            
        Returns:
            查询构建器实例
            
        Example:
            User.order_by('created_at', 'desc')
            User.order_by('name')  # 默认升序
        """
        column_attr = getattr(self._model_class, column)
        
        if direction.lower() == 'desc':
            order_clause = desc(column_attr)
        else:
            order_clause = asc(column_attr)
        
        self._order_clauses.append(order_clause)
        return self
    
    def limit(self, count: int) -> 'EnhancedQueryBuilder[T]':
        """限制记录数量
        
        Args:
            count: 记录数量
            
        Returns:
            查询构建器实例
            
        Example:
            User.limit(10)
        """
        self._limit_value = count
        return self
    
    def offset(self, count: int) -> 'EnhancedQueryBuilder[T]':
        """跳过记录数量
        
        Args:
            count: 跳过的记录数量
            
        Returns:
            查询构建器实例
            
        Example:
            User.offset(20)
        """
        self._offset_value = count
        return self
    
    def distinct(self) -> 'EnhancedQueryBuilder[T]':
        """去重查询
        
        Returns:
            查询构建器实例
            
        Example:
            User.distinct()
        """
        self._distinct_value = True
        return self
    
    def _build_query(self):
        """构建SQLAlchemy查询"""
        query = select(self._model_class)
        
        # 添加条件
        if self._conditions:
            query = query.where(and_(*self._conditions))
        
        # 添加排序
        if self._order_clauses:
            query = query.order_by(*self._order_clauses)
        
        # 添加去重
        if self._distinct_value:
            query = query.distinct()
        
        # 添加偏移和限制
        if self._offset_value is not None:
            query = query.offset(self._offset_value)
        
        if self._limit_value is not None:
            query = query.limit(self._limit_value)
        
        return query
    
    # =================================================================
    # 执行方法 - 无需session参数
    # =================================================================
    
    async def get(self) -> List[T]:
        """执行查询并获取所有结果
        
        Returns:
            模型实例列表
            
        Example:
            users = await User.where('age', '>', 18).get()
        """
        async def _get(session: AsyncSession) -> List[T]:
            query = self._build_query()
            result = await session.execute(query)
            return list(result.scalars().all())
        
        return await execute_with_session(_get)
    
    async def first(self) -> Optional[T]:
        """获取第一条记录
        
        Returns:
            模型实例或None
            
        Example:
            user = await User.where('email', email).first()
        """
        async def _first(session: AsyncSession) -> Optional[T]:
            query = self._build_query().limit(1)
            result = await session.execute(query)
            return result.scalars().first()
        
        return await execute_with_session(_first)
    
    async def count(self) -> int:
        """统计记录数量
        
        Returns:
            记录数量
            
        Example:
            count = await User.where('status', 'active').count()
        """
        async def _count(session: AsyncSession) -> int:
            # 构建count查询
            count_query = select(func.count()).select_from(self._model_class)
            
            # 添加条件
            if self._conditions:
                count_query = count_query.where(and_(*self._conditions))
            
            result = await session.execute(count_query)
            return result.scalar() or 0
        
        return await execute_with_session(_count)
    
    async def exists(self) -> bool:
        """检查是否存在匹配的记录
        
        Returns:
            True如果存在记录，否则False
            
        Example:
            exists = await User.where('email', email).exists()
        """
        count = await self.count()
        return count > 0
    
    async def delete(self) -> int:
        """删除匹配的记录
        
        Returns:
            删除的记录数量
            
        Example:
            deleted = await User.where('status', 'inactive').delete()
        """
        async def _delete(session: AsyncSession) -> int:
            from sqlalchemy import delete
            
            delete_query = delete(self._model_class)
            
            # 添加条件
            if self._conditions:
                delete_query = delete_query.where(and_(*self._conditions))
            
            result = await session.execute(delete_query)
            return result.rowcount or 0
        
        return await execute_with_session(_delete)
    
    # =================================================================
    # 分页方法
    # =================================================================
    
    async def paginate(
        self, 
        page: int = 1, 
        per_page: int = 15
    ) -> Dict[str, Any]:
        """分页查询
        
        Args:
            page: 页码（从1开始）
            per_page: 每页记录数
            
        Returns:
            包含分页信息的字典
            
        Example:
            result = await User.where('status', 'active').paginate(page=2, per_page=10)
        """
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取总数
        total = await self.count()
        
        # 获取当页数据
        items = await self.offset(offset).limit(per_page).get()
        
        # 计算分页信息
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_page': page - 1 if has_prev else None,
            'next_page': page + 1 if has_next else None,
        } 