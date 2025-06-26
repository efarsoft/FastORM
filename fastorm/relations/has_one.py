"""
FastORM HasOne 关系

实现一对一关系（拥有）。
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import select

from .base import Relation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class HasOne(Relation[Any]):
    """一对一关系（拥有）
    
    表示当前模型拥有另一个模型的一对一关系。
    
    示例：
    ```python
    class User(Model):
        # 用户拥有一个档案
        profile = HasOne('Profile', foreign_key='user_id')
    
    # 使用
    user = await User.find(1)
    profile = await user.profile.load()  # 加载关联的档案
    ```
    """
    
    async def load(self, parent: Any, session: AsyncSession) -> Optional[Any]:
        """加载关联数据
        
        Args:
            parent: 父模型实例
            session: 数据库会话
            
        Returns:
            关联的模型实例，如果不存在则返回None
        """
        # 检查缓存
        if self.is_loaded():
            return self.get_cache()
        
        # 获取本地键值
        local_key_value = self.get_local_key_value(parent)
        if local_key_value is None:
            self.set_cache(None)
            return None
        
        # 获取外键名
        foreign_key = self.get_foreign_key(parent)
        
        # 构建查询
        query = select(self.model_class).where(
            getattr(self.model_class, foreign_key) == local_key_value
        )
        
        # 执行查询
        result = await session.execute(query)
        instance = result.scalars().first()
        
        # 缓存结果
        self.set_cache(instance)
        return instance
    
    def get_foreign_key(self, parent: Any) -> str:
        """获取外键字段名
        
        对于HasOne关系，外键在关联模型中，指向父模型
        """
        if self.foreign_key:
            return self.foreign_key
        
        # 自动推断：父模型名_id
        return f"{parent.__class__.__name__.lower()}_id" 