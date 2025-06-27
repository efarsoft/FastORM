"""
FastORM批量操作模块

定义各种具体的批量操作类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy import insert, update, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .exceptions import BatchError


class BatchOperation(ABC):
    """批量操作基类"""
    
    def __init__(self, model_class: Type, config: Optional[Dict[str, Any]] = None):
        self.model_class = model_class
        self.config = config or {}
    
    @abstractmethod
    async def execute(self, session, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行批量操作"""
        pass


class BatchInsert(BatchOperation):
    """批量插入操作"""
    
    async def execute(self, session, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行批量插入"""
        stmt = insert(self.model_class.__table__)
        result = await session.execute(stmt, data)
        return {'inserted_count': len(data)}


class BatchUpdate(BatchOperation):
    """批量更新操作"""
    
    def __init__(self, model_class: Type, where_fields: List[str], **kwargs):
        super().__init__(model_class, **kwargs)
        self.where_fields = where_fields
    
    async def execute(self, session, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行批量更新"""
        updated_count = 0
        for record in data:
            where_clause = {field: record[field] for field in self.where_fields}
            update_data = {k: v for k, v in record.items() if k not in self.where_fields}
            
            stmt = update(self.model_class.__table__).where(
                **where_clause
            ).values(**update_data)
            
            result = await session.execute(stmt)
            updated_count += result.rowcount
        
        return {'updated_count': updated_count}


class BatchDelete(BatchOperation):
    """批量删除操作"""
    
    async def execute(self, session, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行批量删除"""
        deleted_count = 0
        for condition in conditions:
            stmt = delete(self.model_class.__table__).where(**condition)
            result = await session.execute(stmt)
            deleted_count += result.rowcount
        
        return {'deleted_count': deleted_count}


class BatchUpsert(BatchOperation):
    """批量插入或更新操作"""
    
    def __init__(self, model_class: Type, conflict_fields: List[str], **kwargs):
        super().__init__(model_class, **kwargs)
        self.conflict_fields = conflict_fields
    
    async def execute(self, session, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行批量Upsert（PostgreSQL示例）"""
        stmt = pg_insert(self.model_class.__table__)
        
        # 定义冲突时的更新操作
        update_dict = {
            col.name: stmt.excluded[col.name] 
            for col in self.model_class.__table__.columns 
            if col.name not in self.conflict_fields
        }
        
        stmt = stmt.on_conflict_do_update(
            index_elements=self.conflict_fields,
            set_=update_dict
        )
        
        result = await session.execute(stmt, data)
        return {'upserted_count': len(data)} 