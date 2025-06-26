"""
FastORM 查询构建器

提供流畅的链式API用于构建SQL查询。
"""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select

T = TypeVar('T')


class QueryBuilder(Generic[T]):
    """SQL查询构建器
    
    提供流畅的链式API用于构建SQL查询。
    """
    
    def __init__(self, model_class: Type[T]):
        """初始化查询构建器
        
        Args:
            model_class: 模型类
        """
        self.model_class = model_class
        self._query: Optional[Select] = None
        self._where_conditions: List[Any] = []
        self._limit_value: Optional[int] = None
        self._offset_value: Optional[int] = None
        self._order_by_clauses: List[Any] = []
    
    def _build_query(self) -> Select:
        """构建查询对象"""
        if self._query is not None:
            return self._query
        
        query = select(self.model_class)
        
        # 应用WHERE条件
        if self._where_conditions:
            query = query.where(and_(*self._where_conditions))
        
        # 应用ORDER BY
        for order_clause in self._order_by_clauses:
            query = query.order_by(order_clause)
        
        # 应用LIMIT
        if self._limit_value is not None:
            query = query.limit(self._limit_value)
        
        # 应用OFFSET
        if self._offset_value is not None:
            query = query.offset(self._offset_value)
        
        self._query = query
        return query
    
    def where(self, column: str, value: Any) -> QueryBuilder[T]:
        """添加WHERE条件
        
        Args:
            column: 列名
            value: 值
            
        Returns:
            查询构建器实例
        """
        column_attr = getattr(self.model_class, column)
        condition = column_attr == value
        self._where_conditions.append(condition)
        self._query = None  # 重置查询
        return self
    
    def limit(self, value: int) -> QueryBuilder[T]:
        """设置LIMIT
        
        Args:
            value: 限制数量
            
        Returns:
            查询构建器实例
        """
        self._limit_value = value
        self._query = None
        return self
    
    def offset(self, value: int) -> QueryBuilder[T]:
        """设置OFFSET
        
        Args:
            value: 偏移量
            
        Returns:
            查询构建器实例
        """
        self._offset_value = value
        self._query = None
        return self
    
    def order_by(self, column: str, direction: str = "asc") -> QueryBuilder[T]:
        """添加ORDER BY
        
        Args:
            column: 列名
            direction: 排序方向 (asc/desc)
            
        Returns:
            查询构建器实例
        """
        column_attr = getattr(self.model_class, column)
        if direction.lower() == "desc":
            order_clause = column_attr.desc()
        else:
            order_clause = column_attr.asc()
        
        self._order_by_clauses.append(order_clause)
        self._query = None
        return self
    
    async def get(self, session: AsyncSession) -> List[T]:
        """执行查询并返回结果列表
        
        Args:
            session: 数据库会话
            
        Returns:
            查询结果列表
        """
        query = self._build_query()
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def first(self, session: AsyncSession) -> Optional[T]:
        """执行查询并返回第一个结果
        
        Args:
            session: 数据库会话
            
        Returns:
            第一个结果或None
        """
        query = self._build_query().limit(1)
        result = await session.execute(query)
        return result.scalars().first()
    
    async def count(self, session: AsyncSession) -> int:
        """执行查询并返回结果数量
        
        Args:
            session: 数据库会话
            
        Returns:
            结果数量
        """
        from sqlalchemy import func
        
        query = select(func.count()).select_from(self.model_class)
        
        # 应用WHERE条件
        if self._where_conditions:
            query = query.where(and_(*self._where_conditions))
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    async def paginate(
        self, 
        session: AsyncSession, 
        page: int = 1, 
        per_page: int = 15
    ) -> Dict[str, Any]:
        """分页查询
        
        Args:
            session: 数据库会话
            page: 页码（从1开始）
            per_page: 每页数量
            
        Returns:
            分页结果字典
        """
        # 计算总数
        total = await self.count(session)
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取当前页数据
        items = await self.limit(per_page).offset(offset).get(session)
        
        # 计算总页数
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        } 