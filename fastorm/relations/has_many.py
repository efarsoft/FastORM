"""
FastORM HasMany 关系

实现一对多关系。
"""

from __future__ import annotations

from typing import Any, List, Dict, TYPE_CHECKING

from sqlalchemy import select, insert, delete as sql_delete

from .base import Relation
from fastorm.core.session_manager import execute_with_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class HasMany(Relation[List[Any]]):
    """一对多关系
    
    表示当前模型拥有多个其他模型实例。
    
    示例：
    ```python
    class User(Model):
        # 用户拥有多篇文章
        posts = HasMany('Post', foreign_key='user_id')
    
    # 使用
    user = await User.find(1)
    posts = await user.posts.load()  # 加载所有关联的文章
    
    # 创建关联数据
    post = await user.posts.create(title="新文章", content="内容")
    
    # 保存关联数据
    new_post = Post(title="另一篇文章")
    await user.posts.save(new_post)
    ```
    """
    
    async def load(self, parent: Any, session: AsyncSession) -> List[Any]:
        """加载关联数据
        
        Args:
            parent: 父模型实例
            session: 数据库会话
            
        Returns:
            关联的模型实例列表
        """
        # 检查缓存
        if self.is_loaded():
            return self.get_cache() or []
        
        # 获取本地键值
        local_key_value = self.get_local_key_value(parent)
        if local_key_value is None:
            self.set_cache([])
            return []
        
        # 获取外键名
        foreign_key = self.get_foreign_key(parent)
        
        # 构建查询
        query = select(self.model_class).where(
            getattr(self.model_class, foreign_key) == local_key_value
        )
        
        # 执行查询
        result = await session.execute(query)
        instances = result.scalars().all()
        
        # 缓存结果
        self.set_cache(instances)
        return instances
    
    def get_foreign_key(self, parent: Any) -> str:
        """获取外键字段名
        
        对于HasMany关系，外键在关联模型中，指向父模型
        """
        if self.foreign_key:
            return self.foreign_key
        
        # 自动推断：父模型名_id
        return f"{parent.__class__.__name__.lower()}_id"
    
    # =================================================================
    # 关系操作方法
    # =================================================================
    
    async def create(self, parent: Any, **attributes: Any) -> Any:
        """通过关系创建新的关联记录
        
        Args:
            parent: 父模型实例
            **attributes: 新记录的属性
            
        Returns:
            创建的关联模型实例
        """
        async def _create(session: AsyncSession) -> Any:
            # 设置外键值
            foreign_key = self.get_foreign_key(parent)
            local_key_value = self.get_local_key_value(parent)
            attributes[foreign_key] = local_key_value
            
            # 创建实例
            instance = self.model_class(**attributes)
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            
            # 清空缓存以便重新加载
            self.clear_cache()
            
            return instance
        
        return await execute_with_session(_create)
    
    async def save(self, parent: Any, instance: Any) -> Any:
        """保存关联模型实例
        
        Args:
            parent: 父模型实例
            instance: 要保存的关联模型实例
            
        Returns:
            保存的模型实例
        """
        async def _save(session: AsyncSession) -> Any:
            # 设置外键值
            foreign_key = self.get_foreign_key(parent)
            local_key_value = self.get_local_key_value(parent)
            setattr(instance, foreign_key, local_key_value)
            
            # 保存实例
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            
            # 清空缓存
            self.clear_cache()
            
            return instance
        
        return await execute_with_session(_save)
    
    async def save_many(self, parent: Any, instances: List[Any]) -> List[Any]:
        """批量保存关联模型实例
        
        Args:
            parent: 父模型实例
            instances: 要保存的关联模型实例列表
            
        Returns:
            保存的模型实例列表
        """
        async def _save_many(session: AsyncSession) -> List[Any]:
            foreign_key = self.get_foreign_key(parent)
            local_key_value = self.get_local_key_value(parent)
            
            saved_instances = []
            for instance in instances:
                setattr(instance, foreign_key, local_key_value)
                session.add(instance)
                saved_instances.append(instance)
            
            await session.flush()
            
            # 刷新所有实例
            for instance in saved_instances:
                await session.refresh(instance)
            
            # 清空缓存
            self.clear_cache()
            
            return saved_instances
        
        return await execute_with_session(_save_many)
    
    async def create_many(
        self, 
        parent: Any, 
        records: List[Dict[str, Any]]
    ) -> List[Any]:
        """批量创建关联记录
        
        Args:
            parent: 父模型实例
            records: 记录数据列表
            
        Returns:
            创建的模型实例列表
        """
        async def _create_many(session: AsyncSession) -> List[Any]:
            foreign_key = self.get_foreign_key(parent)
            local_key_value = self.get_local_key_value(parent)
            
            # 为每条记录设置外键
            for record in records:
                record[foreign_key] = local_key_value
            
            # 批量插入
            result = await session.execute(
                insert(self.model_class).returning(self.model_class)
            )
            instances = result.scalars().all()
            
            # 清空缓存
            self.clear_cache()
            
            return instances
        
        return await execute_with_session(_create_many)
    
    async def delete_all(self, parent: Any) -> int:
        """删除所有关联记录
        
        Args:
            parent: 父模型实例
            
        Returns:
            删除的记录数量
        """
        async def _delete_all(session: AsyncSession) -> int:
            foreign_key = self.get_foreign_key(parent)
            local_key_value = self.get_local_key_value(parent)
            
            result = await session.execute(
                sql_delete(self.model_class).where(
                    getattr(self.model_class, foreign_key) == local_key_value
                )
            )
            
            # 清空缓存
            self.clear_cache()
            
            return result.rowcount
        
        return await execute_with_session(_delete_all)
    
    async def count(self, parent: Any) -> int:
        """统计关联记录数量
        
        Args:
            parent: 父模型实例
            
        Returns:
            关联记录数量
        """
        async def _count(session: AsyncSession) -> int:
            from sqlalchemy import func
            
            foreign_key = self.get_foreign_key(parent)
            local_key_value = self.get_local_key_value(parent)
            
            result = await session.execute(
                select(func.count()).select_from(self.model_class).where(
                    getattr(self.model_class, foreign_key) == local_key_value
                )
            )
            
            return result.scalar() or 0
        
        return await execute_with_session(_count) 