"""
FastORM 查询构建器

实现真正简洁的链式查询API，支持读写分离。
"""

from __future__ import annotations

from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Generic, Union, Callable, 
    TYPE_CHECKING
)

from sqlalchemy import select, and_, asc, desc, func, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from fastorm.core.session_manager import execute_with_session

T = TypeVar('T')

if TYPE_CHECKING:
    from sqlalchemy.sql import Select
    from fastorm.query.pagination import Paginator, SimplePaginator
    from fastorm.query.batch import BatchProcessor


class QueryBuilder(Generic[T]):
    """查询构建器
    
    实现ThinkORM风格的简洁链式查询，自动支持读写分离。
    
    示例:
    ```python
    # 🎯 简洁的链式查询 - 自动使用从库
    users = await User.where('age', '>', 18)\
                     .where('status', 'active')\
                     .order_by('name')\
                     .limit(10)\
                     .get()
    
    # 🔧 强制使用主库（用于读自己的写等场景）
    user = await User.where('id', user_id).force_write().first()
    
    # 💾 写操作自动使用主库
    await User.where('status', 'inactive').delete()
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
        self._force_write: bool = False  # 强制使用写库标志
        self._operation_type: str = "read"  # 操作类型：read/write/transaction
    
    def force_write(self) -> 'QueryBuilder[T]':
        """强制使用写库（主库）
        
        在以下场景中很有用：
        - 读自己的写（避免主从延迟）
        - 对一致性要求很高的读操作
        - 事务中的读操作
        
        Returns:
            新的查询构建器实例
            
        Example:
            # 强制从主库读取最新数据
            user = await User.where('id', 1).force_write().first()
        """
        new_builder = self._clone()
        new_builder._force_write = True
        new_builder._operation_type = "write"
        return new_builder
    
    def where(
        self, 
        column: str, 
        operator: Union[str, Any] = "=", 
        value: Any = None
    ) -> 'QueryBuilder[T]':
        """添加查询条件
        
        Args:
            column: 字段名或表达式
            operator: 操作符，可以是 "=", ">", "<", ">=", "<=", "!=", "like", "in"
            value: 比较值
            
        Returns:
            新的查询构建器实例
            
        Example:
            builder = User.where('age', '>', 18)
            builder = User.where('name', 'like', 'John%')
            builder = User.where('status', 'in', ['active', 'pending'])
        """
        # 如果只传两个参数，则operator为"="
        if value is None:
            value = operator
            operator = "="
        
        new_builder = self._clone()
        
        # 获取字段属性
        if hasattr(self._model_class, column):
            field = getattr(self._model_class, column)
        else:
            raise ValueError(f"Field {column} not found in {self._model_class.__name__}")
        
        # 构建条件
        if operator == "=":
            condition = field == value
        elif operator == ">":
            condition = field > value
        elif operator == "<":
            condition = field < value
        elif operator == ">=":
            condition = field >= value
        elif operator == "<=":
            condition = field <= value
        elif operator == "!=" or operator == "<>":
            condition = field != value
        elif operator.lower() == "like":
            condition = field.like(value)
        elif operator.lower() == "in":
            condition = field.in_(value)
        elif operator.lower() == "is":
            condition = field.is_(value)
        elif operator.lower() == "is not":
            condition = field.is_not(value)
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        new_builder._conditions.append(condition)
        return new_builder
    
    def order_by(self, column: str, direction: str = "asc") -> 'QueryBuilder[T]':
        """添加排序条件
        
        Args:
            column: 排序字段
            direction: 排序方向，"asc"或"desc"
            
        Returns:
            新的查询构建器实例
            
        Example:
            builder = User.order_by('name')
            builder = User.order_by('created_at', 'desc')
        """
        new_builder = self._clone()
        
        if hasattr(self._model_class, column):
            field = getattr(self._model_class, column)
            if direction.lower() == "desc":
                new_builder._order_clauses.append(desc(field))
            else:
                new_builder._order_clauses.append(asc(field))
        else:
            raise ValueError(f"Field {column} not found in {self._model_class.__name__}")
        
        return new_builder
    
    def limit(self, count: int) -> 'QueryBuilder[T]':
        """设置查询限制
        
        Args:
            count: 最大记录数
            
        Returns:
            新的查询构建器实例
        """
        new_builder = self._clone()
        new_builder._limit_value = count
        return new_builder
    
    def offset(self, count: int) -> 'QueryBuilder[T]':
        """设置查询偏移
        
        Args:
            count: 偏移量
            
        Returns:
            新的查询构建器实例
        """
        new_builder = self._clone()
        new_builder._offset_value = count
        return new_builder
    
    def distinct(self) -> 'QueryBuilder[T]':
        """设置去重查询
        
        Returns:
            新的查询构建器实例
        """
        new_builder = self._clone()
        new_builder._distinct_value = True
        return new_builder
    
    def with_relations(self, *relations: str) -> 'QueryBuilder[T]':
        """预加载关系
        
        Args:
            *relations: 关系字段名列表
            
        Returns:
            新的查询构建器实例
        """
        new_builder = self._clone()
        for relation in relations:
            new_builder._with_relations[relation] = True
        return new_builder
    
    def _clone(self) -> 'QueryBuilder[T]':
        """创建当前查询构建器的副本
        
        Returns:
            新的查询构建器实例
        """
        new_builder = QueryBuilder(self._model_class)
        new_builder._conditions = self._conditions.copy()
        new_builder._order_clauses = self._order_clauses.copy()
        new_builder._limit_value = self._limit_value
        new_builder._offset_value = self._offset_value
        new_builder._distinct_value = self._distinct_value
        new_builder._with_relations = self._with_relations.copy()
        new_builder._force_write = self._force_write
        new_builder._operation_type = self._operation_type
        return new_builder
    
    def _build_query(self) -> Select:
        """构建最终的SQL查询
        
        Returns:
            SQLAlchemy查询对象
        """
        query = select(self._model_class)
        
        # 应用条件
        if self._conditions:
            query = query.where(and_(*self._conditions))
        
        # 应用排序
        if self._order_clauses:
            query = query.order_by(*self._order_clauses)
        
        # 应用限制和偏移
        if self._limit_value is not None:
            query = query.limit(self._limit_value)
        
        if self._offset_value is not None:
            query = query.offset(self._offset_value)
        
        # 应用去重
        if self._distinct_value:
            query = query.distinct()
        
        return query
    
    def _get_session_type(self) -> str:
        """确定应该使用的会话类型
        
        Returns:
            会话类型：read/write/transaction
        """
        if self._force_write or self._operation_type == "write":
            return "write"
        elif self._operation_type == "transaction":
            return "transaction"
        else:
            return "read"
    
    async def get(self) -> List[T]:
        """执行查询并获取所有结果 - 自动使用读库
        
        Returns:
            模型实例列表
            
        Example:
            users = await User.where('status', 'active').get()
        """
        async def _get(session: AsyncSession) -> List[T]:
            query = self._build_query()
            result = await session.execute(query)
            instances = list(result.scalars().all())
            
            # 加载关系
            if self._with_relations:
                await self._load_relations(instances, session)
            
            return instances
        
        # 使用适当的会话类型
        session_type = self._get_session_type()
        return await execute_with_session(_get, connection_type=session_type)
    
    async def first(self) -> Optional[T]:
        """获取第一条记录 - 自动使用读库
        
        Returns:
            模型实例或None
            
        Example:
            user = await User.where('email', email).first()
        """
        async def _first(session: AsyncSession) -> Optional[T]:
            query = self._build_query().limit(1)
            result = await session.execute(query)
            instance = result.scalars().first()
            
            # 加载关系
            if instance and self._with_relations:
                await self._load_relations([instance], session)
            
            return instance
        
        session_type = self._get_session_type()
        return await execute_with_session(_first, connection_type=session_type)
    
    async def count(self) -> int:
        """统计记录数量 - 自动使用读库
        
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
        
        session_type = self._get_session_type()
        return await execute_with_session(_count, connection_type=session_type)
    
    async def exists(self) -> bool:
        """检查是否存在匹配的记录 - 自动使用读库
        
        Returns:
            True如果存在记录，否则False
            
        Example:
            exists = await User.where('email', email).exists()
        """
        count = await self.count()
        return count > 0
    
    async def delete(self) -> int:
        """删除匹配的记录 - 自动使用写库
        
        Returns:
            删除的记录数量
            
        Example:
            deleted_count = await User.where('status', 'inactive').delete()
        """
        async def _delete(session: AsyncSession) -> int:
            # 构建删除查询
            delete_query = delete(self._model_class)
            
            # 添加条件
            if self._conditions:
                delete_query = delete_query.where(and_(*self._conditions))
            
            result = await session.execute(delete_query)
            return result.rowcount
        
        # 删除操作强制使用写库
        return await execute_with_session(_delete, connection_type="write")
    
    async def update(self, **values: Any) -> int:
        """更新匹配的记录 - 自动使用写库
        
        Args:
            **values: 要更新的字段值
            
        Returns:
            更新的记录数量
            
        Example:
            updated_count = await User.where('status', 'pending').update(status='active')
        """
        async def _update(session: AsyncSession) -> int:
            # 构建更新查询
            update_query = update(self._model_class)
            
            # 添加条件
            if self._conditions:
                update_query = update_query.where(and_(*self._conditions))
            
            # 添加更新值
            update_query = update_query.values(**values)
            
            result = await session.execute(update_query)
            return result.rowcount
        
        # 更新操作强制使用写库
        return await execute_with_session(_update, connection_type="write")
    
    # =================================================================
    # 分页方法
    # =================================================================
    
    async def paginate(
        self, 
        page: int = 1, 
        per_page: int = 15,
        path: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None
    ) -> 'Paginator[T]':
        """高级分页查询
        
        Args:
            page: 页码（从1开始）
            per_page: 每页记录数
            path: 基础路径（用于生成分页链接）
            query_params: 查询参数（用于生成分页链接）
            
        Returns:
            Paginator实例，包含完整分页信息
            
        Example:
            paginator = await User.where('status', 'active')\
                                  .paginate(page=2, per_page=10)
            
            print(f"总记录数: {paginator.total}")
            print(f"当前页: {paginator.current_page}")
            for user in paginator.items:
                print(user.name)
        """
        from fastorm.query.pagination import create_paginator
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取总数
        total = await self.count()
        
        # 获取当页数据
        items = await self.offset(offset).limit(per_page).get()
        
        return create_paginator(
            items=items,
            total=total,
            per_page=per_page,
            current_page=page,
            path=path,
            query_params=query_params
        )
    
    async def simple_paginate(
        self, 
        page: int = 1, 
        per_page: int = 15,
        path: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None
    ) -> 'SimplePaginator[T]':
        """简单分页查询（不计算总数）
        
        Args:
            page: 页码（从1开始）
            per_page: 每页记录数
            path: 基础路径
            query_params: 查询参数
            
        Returns:
            SimplePaginator实例
            
        Example:
            paginator = await User.where('status', 'active')\
                                  .simple_paginate(page=2, per_page=10)
        """
        from fastorm.query.pagination import create_simple_paginator
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取数据（多取一条判断是否还有更多）
        items = await self.offset(offset).limit(per_page + 1).get()
        
        # 检查是否还有更多数据
        has_more = len(items) > per_page
        if has_more:
            items = items[:per_page]
        
        return create_simple_paginator(
            items=items,
            per_page=per_page,
            current_page=page,
            has_more=has_more,
            path=path,
            query_params=query_params
        )
    
    def batch(self) -> 'BatchProcessor[T]':
        """获取批量处理器
        
        Returns:
            批量处理器实例
            
        Example:
            # 分块处理
            await User.where('active', True).batch().chunk(100, process_users)
            
            # 批量更新
            await User.where('status', 'pending').batch().batch_update({
                'status': 'processed'
            })
        """
        from fastorm.query.batch import BatchProcessor
        return BatchProcessor(self)
    
    async def chunk(
        self, 
        size: int, 
        callback: Callable[[List[T]], Any],
        preserve_order: bool = True
    ) -> int:
        """分块处理数据的便捷方法
        
        Args:
            size: 每块的大小
            callback: 处理函数
            preserve_order: 是否保持处理顺序
            
        Returns:
            处理的总记录数
        """
        return await self.batch().chunk(size, callback, preserve_order)
    
    async def each(
        self, 
        callback: Callable[[T], Any], 
        chunk_size: int = 100
    ) -> int:
        """逐个处理记录的便捷方法
        
        Args:
            callback: 处理函数
            chunk_size: 内部分块大小
            
        Returns:
            处理的总记录数
        """
        return await self.batch().each(callback, chunk_size)
    
    def _apply_conditions(self, source_builder: 'QueryBuilder[T]') -> 'QueryBuilder[T]':
        """应用另一个查询构建器的条件到当前构建器
        
        Args:
            source_builder: 源查询构建器
            
        Returns:
            应用条件后的新查询构建器
        """
        new_builder = QueryBuilder(self._model_class)
        
        # 复制条件
        new_builder._conditions = source_builder._conditions.copy()
        new_builder._order_clauses = source_builder._order_clauses.copy()
        new_builder._limit_value = source_builder._limit_value
        new_builder._offset_value = source_builder._offset_value
        new_builder._distinct_value = source_builder._distinct_value
        new_builder._with_relations = source_builder._with_relations.copy()
        new_builder._force_write = source_builder._force_write
        new_builder._operation_type = source_builder._operation_type
        
        # 重建查询
        new_builder._query = select(self._model_class)
        
        return new_builder
    
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