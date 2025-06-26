"""
FastORM 批量操作

提供Eloquent风格的批量数据处理功能。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from fastorm.query.builder import QueryBuilder

T = TypeVar('T')


class BatchProcessor:
    """批量处理器 - 提供各种批量操作功能"""
    
    def __init__(self, query_builder: 'QueryBuilder[T]'):
        self.query_builder = query_builder
        self._model_class = query_builder._model_class
    
    async def chunk(
        self, 
        size: int, 
        callback: Callable[[List[T]], Any],
        preserve_order: bool = True
    ) -> int:
        """分块处理数据"""
        if size <= 0:
            raise ValueError("Chunk size must be greater than 0")
        
        total_processed = 0
        page = 1
        
        while True:
            # 获取当前块的数据
            offset = (page - 1) * size
            chunk_data = await (self.query_builder
                               .offset(offset)
                               .limit(size)
                               .get())
            
            if not chunk_data:
                break
            
            # 执行回调函数
            import asyncio
            if asyncio.iscoroutinefunction(callback):
                await callback(chunk_data)
            else:
                callback(chunk_data)
            
            total_processed += len(chunk_data)
            
            if len(chunk_data) < size:
                break
            
            page += 1
        
        return total_processed
    
    async def each(
        self, 
        callback: Callable[[T], Any],
        chunk_size: int = 100
    ) -> int:
        """逐个处理记录"""
        total_processed = 0
        
        async def chunk_processor(items: List[T]) -> None:
            nonlocal total_processed
            import asyncio
            for item in items:
                if asyncio.iscoroutinefunction(callback):
                    await callback(item)
                else:
                    callback(item)
                total_processed += 1
        
        await self.chunk(chunk_size, chunk_processor)
        return total_processed
    
    async def batch_update(
        self, 
        values: Dict[str, Any],
        chunk_size: int = 1000
    ) -> int:
        """批量更新记录"""
        return await self.query_builder.update(**values)
    
    async def batch_insert(
        self, 
        records: List[Dict[str, Any]],
        chunk_size: int = 1000
    ) -> List[T]:
        """批量插入记录"""
        if not records:
            return []
        
        instances = []
        for record in records:
            instance = self._model_class(**record)
            instances.append(instance)
        
        return instances
    
    async def cursor_paginate(
        self, 
        cursor_column: str,
        cursor_value: Any = None,
        limit: int = 100,
        direction: str = 'next'
    ) -> Dict[str, Any]:
        """基于游标的分页"""
        query = self.query_builder
        
        if cursor_value is not None:
            if direction == 'next':
                query = query.where(cursor_column, '>', cursor_value)
            else:
                query = query.where(cursor_column, '<', cursor_value)
        
        items = await query.order_by(cursor_column).limit(limit + 1).get()
        
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]
        
        next_cursor = None
        if items and has_more:
            next_cursor = getattr(items[-1], cursor_column)
        
        return {
            'data': items,
            'next_cursor': next_cursor,
            'has_more': has_more,
            'limit': limit
        } 