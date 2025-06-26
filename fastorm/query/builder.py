"""
FastORM 查询构建器

实现真正简洁的链式查询API。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union, Callable, TYPE_CHECKING

from sqlalchemy import select, and_, asc, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from fastorm.core.session_manager import execute_with_session, get_session

T = TypeVar('T')

if TYPE_CHECKING:
    from sqlalchemy.sql import Select


class QueryBuilder(Generic[T]):
    """查询构建器
    
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
        self._conditions: List[Any] = []
        self._order_clauses: List[Any] = []
        self._limit_value: Optional[int] = None
        self._offset_value: Optional[int] = None
        self._distinct_value: bool = False
        self._with_relations: Dict[str, Any] = {}
        self._query: Select = select(model_class)
    
    def where(
        self, 
        column: str, 
        operator: str = "=", 
        value: Any = None
    ) -> 'QueryBuilder[T]':
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
        self._query = self._query.where(condition)
        return self
    
    def where_in(self, column: str, values: List[Any]) -> 'QueryBuilder[T]':
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
    ) -> 'QueryBuilder[T]':
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
    
    def where_null(self, column: str) -> 'QueryBuilder[T]':
        """WHERE IS NULL 查询
        
        Args:
            column: 列名
            
        Returns:
            查询构建器实例
            
        Example:
            User.where_null('deleted_at')
        """
        return self.where(column, 'is null')
    
    def where_not_null(self, column: str) -> 'QueryBuilder[T]':
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
    ) -> 'QueryBuilder[T]':
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
            order_clause: Any = desc(column_attr)
        else:
            order_clause = asc(column_attr)
        
        self._order_clauses.append(order_clause)
        self._query = self._query.order_by(order_clause)
        return self
    
    def limit(self, count: int) -> 'QueryBuilder[T]':
        """限制记录数量
        
        Args:
            count: 记录数量
            
        Returns:
            查询构建器实例
            
        Example:
            User.limit(10)
        """
        self._limit_value = count
        self._query = self._query.limit(count)
        return self
    
    def offset(self, count: int) -> 'QueryBuilder[T]':
        """跳过记录数量
        
        Args:
            count: 跳过的记录数量
            
        Returns:
            查询构建器实例
            
        Example:
            User.offset(20)
        """
        self._offset_value = count
        self._query = self._query.offset(count)
        return self
    
    def distinct(self) -> 'QueryBuilder[T]':
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
        query = self._query
        
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
            instances = list(result.scalars().all())
            
            # 加载关系
            if self._with_relations and instances:
                await self._load_relations(instances, session)
            
            return instances
        
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
            result = await User.where('status', 'active')\
                               .paginate(page=2, per_page=10)
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
    
    async def _load_relations(
        self, 
        instances: List[T], 
        session: AsyncSession
    ) -> None:
        """加载预定义的关系
        
        Args:
            instances: 模型实例列表
            session: 数据库会话
        """
        for relation_name in self._with_relations:
            # 检查关系是否存在
            if hasattr(self._model_class, relation_name):
                # 为每个实例加载关系
                for instance in instances:
                    relation_obj = getattr(instance, relation_name)
                    if hasattr(relation_obj, 'load'):
                        # RelationProxy的load方法不需要额外参数
                        related_data = await relation_obj.load()
                        # 设置关系属性
                        setattr(instance, f'_{relation_name}_loaded', related_data)

    # =================================================================
    # 关系查询方法
    # =================================================================
    
    def with_(self, relations: Union[str, List[str]]) -> 'QueryBuilder[T]':
        """预加载关系（防止N+1查询）
        
        Args:
            relations: 关系名或关系名列表
            
        Returns:
            查询构建器实例
            
        示例：
        ```python
        # 预加载单个关系
        users = await User.query().with_('posts').get()
        
        # 预加载多个关系
        users = await User.query().with_(['posts', 'profile']).get()
        ```
        """
        if isinstance(relations, str):
            self._with_relations[relations] = None
        else:
            for relation in relations:
                self._with_relations[relation] = None
        return self
    
    def where_has(
        self, 
        relation: str, 
        callback: Optional[Callable[[QueryBuilder], QueryBuilder]] = None,
        operator: str = '>=',
        count: int = 1
    ) -> 'QueryBuilder[T]':
        """查询具有特定关系的记录（Laravel风格）
        
        Args:
            relation: 关系名
            callback: 关系查询回调函数
            operator: 计数操作符
            count: 计数阈值
            
        Returns:
            查询构建器实例
            
        示例：
        ```python
        # 查询有文章的用户
        users = await User.query().where_has('posts').get()
        
        # 查询有已发布文章的用户
        users = await User.query().where_has(
            'posts', 
            lambda q: q.where('published', True)
        ).get()
        ```
        """
        # 获取关系定义
        if hasattr(self._model_class, relation):
            relation_obj = getattr(self._model_class, relation)
            
            # 构建子查询
            if hasattr(relation_obj, 'model_class'):
                related_model = relation_obj.model_class
                
                # 创建子查询构建器
                subquery_builder = QueryBuilder(related_model)
                
                # 应用回调条件
                if callback:
                    subquery_builder = callback(subquery_builder)
                
                # 添加关系条件
                if hasattr(relation_obj, 'get_foreign_key'):
                    foreign_key = relation_obj.get_foreign_key(self._model_class())
                    local_key = relation_obj.local_key
                    
                    # 构建EXISTS子查询
                    subquery = (
                        subquery_builder._query
                        .where(getattr(related_model, foreign_key) == 
                               getattr(self._model_class, local_key))
                    )
                    
                    # 根据计数条件选择EXISTS或计数查询
                    if operator == '>=' and count == 1:
                        # 简单的EXISTS查询
                        self._query = self._query.where(subquery.exists())
                    else:
                        # 计数查询
                        count_subquery = select(func.count()).select_from(subquery.alias())
                        if operator == '>=':
                            self._query = self._query.where(count_subquery >= count)
                        elif operator == '>':
                            self._query = self._query.where(count_subquery > count)
                        elif operator == '=':
                            self._query = self._query.where(count_subquery == count)
                        elif operator == '<':
                            self._query = self._query.where(count_subquery < count)
                        elif operator == '<=':
                            self._query = self._query.where(count_subquery <= count)
        
        return self
    
    def where_doesnt_have(
        self, 
        relation: str, 
        callback: Optional[Callable[[QueryBuilder], QueryBuilder]] = None
    ) -> 'QueryBuilder[T]':
        """查询不具有特定关系的记录（Laravel风格）
        
        Args:
            relation: 关系名
            callback: 关系查询回调函数
            
        Returns:
            查询构建器实例
            
        示例：
        ```python
        # 查询没有文章的用户
        users = await User.query().where_doesnt_have('posts').get()
        ```
        """
        # 获取关系定义
        if hasattr(self._model_class, relation):
            relation_obj = getattr(self._model_class, relation)
            
            # 构建子查询
            if hasattr(relation_obj, 'model_class'):
                related_model = relation_obj.model_class
                
                # 创建子查询构建器
                subquery_builder = QueryBuilder(related_model)
                
                # 应用回调条件
                if callback:
                    subquery_builder = callback(subquery_builder)
                
                # 添加关系条件
                if hasattr(relation_obj, 'get_foreign_key'):
                    foreign_key = relation_obj.get_foreign_key(self._model_class())
                    local_key = relation_obj.local_key
                    
                    # 构建NOT EXISTS子查询
                    subquery = (
                        subquery_builder._query
                        .where(getattr(related_model, foreign_key) == 
                               getattr(self._model_class, local_key))
                    )
                    
                    self._query = self._query.where(~subquery.exists())
        
        return self 