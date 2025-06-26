"""
FastORM BelongsTo 关系

实现一对一关系（属于）。
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import select

from .base import Relation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BelongsTo(Relation[Any]):
    """一对一关系（属于）
    
    表示当前模型属于另一个模型的一对一关系。
    
    示例：
    ```python
    class Profile(Model):
        user_id: Mapped[int]
        
        # 档案属于一个用户
        user = BelongsTo('User', foreign_key='user_id')
    
    # 使用
    profile = await Profile.find(1)
    user = await profile.user.load()  # 加载关联的用户
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
        
        # 获取外键值
        foreign_key = self.get_foreign_key(parent)
        foreign_key_value = getattr(parent, foreign_key, None)
        
        if foreign_key_value is None:
            self.set_cache(None)
            return None
        
        # 构建查询
        query = select(self.model_class).where(
            getattr(self.model_class, self.local_key) == foreign_key_value
        )
        
        # 执行查询
        result = await session.execute(query)
        instance = result.scalars().first()
        
        # 缓存结果
        self.set_cache(instance)
        return instance
    
    def get_foreign_key(self, parent: Any) -> str:
        """获取外键字段名
        
        对于BelongsTo关系，外键在当前模型中，指向关联模型
        """
        if self.foreign_key:
            return self.foreign_key
        
        # 自动推断：关联模型名_id
        return f"{self.model_class.__name__.lower()}_id" 