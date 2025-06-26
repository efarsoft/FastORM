"""
FastORM 基础模型

基于SQLAlchemy 2.0.40的现代化ORM模型基类。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import MetaData, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase as SQLAlchemyDeclarativeBase

if TYPE_CHECKING:
    from fastorm.query.builder import QueryBuilder

T = TypeVar('T', bound='BaseModel')


class DeclarativeBase(SQLAlchemyDeclarativeBase):
    """SQLAlchemy 2.0 声明式基类
    
    使用最新的SQLAlchemy 2.0特性：
    - 🔧 优化的元数据配置
    - 🚀 编译缓存支持  
    - 📊 查询计划缓存
    """
    
    # SQLAlchemy 2.0.40+ 元数据优化
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s", 
            "fk": "fk_%(table_name)s_%(column_0_name)s_"
                  "%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


class BaseModel(DeclarativeBase):
    """FastORM基础模型类
    
    提供简洁直观的ORM接口，专为FastAPI优化。
    
    示例:
    ```python
    from sqlalchemy.orm import Mapped, mapped_column
    
    class User(BaseModel):
        __tablename__ = "users"
        
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]
        email: Mapped[str]
    ```
    """
    
    __abstract__ = True
    
    @classmethod
    async def create(
        cls: Type[T], 
        session: AsyncSession, 
        **values: Any
    ) -> T:
        """创建新记录
        
        Args:
            session: 数据库会话
            **values: 字段值
            
        Returns:
            创建的模型实例
        """
        instance = cls(**values)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance
    
    @classmethod 
    async def find(
        cls: Type[T], 
        session: AsyncSession, 
        id: Any
    ) -> Optional[T]:
        """通过主键查找记录
        
        Args:
            session: 数据库会话
            id: 主键值
            
        Returns:
            模型实例或None
        """
        return await session.get(cls, id)
    
    @classmethod
    async def find_or_fail(
        cls: Type[T], 
        session: AsyncSession, 
        id: Any
    ) -> T:
        """通过主键查找记录，不存在则抛出异常
        
        Args:
            session: 数据库会话  
            id: 主键值
            
        Returns:
            模型实例
            
        Raises:
            ValueError: 记录不存在
        """
        instance = await cls.find(session, id)
        if instance is None:
            raise ValueError(f"{cls.__name__} with id {id} not found")
        return instance
    
    @classmethod
    async def all(cls: Type[T], session: AsyncSession) -> List[T]:
        """获取所有记录
        
        Args:
            session: 数据库会话
            
        Returns:
            所有记录列表
        """
        result = await session.execute(select(cls))
        return list(result.scalars().all())
    
    @classmethod
    def where(cls: Type[T], column: str, value: Any) -> QueryBuilder[T]:
        """开始构建查询
        
        Args:
            column: 列名
            value: 值
            
        Returns:
            查询构建器
        """
        # 延迟导入避免循环导入
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls).where(column, value)
    
    @classmethod
    def query(cls: Type[T]) -> QueryBuilder[T]:
        """创建查询构建器
        
        Returns:
            查询构建器实例
        """
        # 延迟导入避免循环导入
        from fastorm.query.builder import QueryBuilder
        return QueryBuilder(cls)
    
    async def save(self, session: AsyncSession) -> None:
        """保存当前实例"""
        session.add(self)
        await session.flush()
    
    async def remove(self, session: AsyncSession) -> None:
        """删除当前实例"""
        await session.delete(self)
        await session.flush()
    
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
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    result[column.name] = value
        
        return result 