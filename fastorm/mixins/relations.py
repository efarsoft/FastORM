"""
FastORM Relations Mixin

参照ThinkORM 4设计的关系处理混入类
提供简洁的关系定义和操作
"""

from typing import Any, Dict, List, Optional, Union, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from fastorm.model.model import Model


class RelationsMixin:
    """
    关系处理混入类
    
    提供类似ThinkORM的关系定义和操作功能
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._relations = {}
        self._loaded_relations = {}
    
    def has_one(self, related_model: Type['Model'], 
                foreign_key: str, local_key: str = 'id'):
        """
        定义一对一关系
        
        Args:
            related_model: 关联模型类
            foreign_key: 外键字段
            local_key: 本地键字段
            
        Returns:
            HasOneRelation实例
        """
        from fastorm.relations.has_one import HasOneRelation
        return HasOneRelation(self, related_model, foreign_key, local_key)
    
    def has_many(self, related_model: Type['Model'], 
                 foreign_key: str, local_key: str = 'id'):
        """
        定义一对多关系
        
        Args:
            related_model: 关联模型类
            foreign_key: 外键字段
            local_key: 本地键字段
            
        Returns:
            HasManyRelation实例
        """
        from fastorm.relations.has_many import HasManyRelation
        return HasManyRelation(self, related_model, foreign_key, local_key)
    
    def belongs_to(self, related_model: Type['Model'], 
                   foreign_key: str, owner_key: str = 'id'):
        """
        定义反向关系（属于）
        
        Args:
            related_model: 关联模型类
            foreign_key: 外键字段
            owner_key: 主键字段
            
        Returns:
            BelongsToRelation实例
        """
        from fastorm.relations.belongs_to import BelongsToRelation
        return BelongsToRelation(self, related_model, foreign_key, owner_key)
    
    def belongs_to_many(self, related_model: Type['Model'],
                        pivot_table: str,
                        foreign_pivot_key: str,
                        related_pivot_key: str,
                        parent_key: str = 'id',
                        related_key: str = 'id'):
        """
        定义多对多关系
        
        Args:
            related_model: 关联模型类
            pivot_table: 中间表名
            foreign_pivot_key: 外键字段
            related_pivot_key: 关联键字段
            parent_key: 父键字段
            related_key: 关联键字段
            
        Returns:
            BelongsToManyRelation实例
        """
        from fastorm.relations.many_to_many import BelongsToManyRelation
        return BelongsToManyRelation(
            self, related_model, pivot_table,
            foreign_pivot_key, related_pivot_key,
            parent_key, related_key
        )
    
    async def load_relation(self, relation_name: str) -> None:
        """
        延迟加载单个关系
        
        Args:
            relation_name: 关系名称
        """
        if relation_name in self._loaded_relations:
            return
        
        # 获取关系定义方法
        if hasattr(self, relation_name):
            relation_method = getattr(self, relation_name)
            if callable(relation_method):
                relation = relation_method()
                # 执行关系查询
                result = await relation.get()
                self._loaded_relations[relation_name] = result
    
    async def load_relations(self, *relations: str) -> None:
        """
        批量加载关系
        
        Args:
            *relations: 关系名称列表
        """
        for relation_name in relations:
            await self.load_relation(relation_name)
    
    @classmethod
    async def with_relations(cls, *relations: str):
        """
        预加载关系的查询
        
        Args:
            *relations: 关系名称列表
            
        Returns:
            带预加载的查询构建器
        """
        from fastorm.query.builder import QueryBuilder
        query = QueryBuilder(cls)
        return query.with_relations(*relations)
    
    def get_relation(self, relation_name: str) -> Any:
        """
        获取已加载的关系
        
        Args:
            relation_name: 关系名称
            
        Returns:
            关系数据
        """
        if relation_name in self._loaded_relations:
            return self._loaded_relations[relation_name]
        
        # 如果未加载，尝试动态加载
        if hasattr(self, relation_name):
            relation_method = getattr(self, relation_name)
            if callable(relation_method):
                # 返回关系对象，用于链式调用
                return relation_method()
        
        return None
    
    def set_relation(self, relation_name: str, value: Any) -> None:
        """
        设置关系数据
        
        Args:
            relation_name: 关系名称
            value: 关系数据
        """
        self._loaded_relations[relation_name] = value
    
    def is_relation_loaded(self, relation_name: str) -> bool:
        """
        检查关系是否已加载
        
        Args:
            relation_name: 关系名称
            
        Returns:
            是否已加载
        """
        return relation_name in self._loaded_relations
    
    def get_loaded_relations(self) -> Dict[str, Any]:
        """
        获取所有已加载的关系
        
        Returns:
            关系字典
        """
        return self._loaded_relations.copy()
    
    def to_dict_with_relations(self, *relations: str) -> Dict[str, Any]:
        """
        转换为字典并包含关系数据
        
        Args:
            *relations: 要包含的关系名称
            
        Returns:
            包含关系的字典
        """
        result = self.to_dict()
        
        for relation_name in relations:
            if relation_name in self._loaded_relations:
                relation_data = self._loaded_relations[relation_name]
                if hasattr(relation_data, 'to_dict'):
                    result[relation_name] = relation_data.to_dict()
                elif isinstance(relation_data, list):
                    result[relation_name] = [
                        item.to_dict() if hasattr(item, 'to_dict') else item
                        for item in relation_data
                    ]
                else:
                    result[relation_name] = relation_data
        
        return result
    
    def __getattr__(self, name: str) -> Any:
        """
        动态访问关系
        """
        # 检查是否为关系方法
        if hasattr(self.__class__, name):
            attr = getattr(self.__class__, name)
            if callable(attr):
                # 如果是方法，直接调用并返回关系对象
                return attr(self)
        
        # 检查是否为已加载的关系
        if name in self._loaded_relations:
            return self._loaded_relations[name]
        
        # 继续正常的属性访问
        try:
            return super().__getattribute__(name)
        except AttributeError:
            # 如果属性不存在，可能是关系名称，返回None
            return None


class RelationQueryMixin:
    """
    关系查询混入类
    
    提供关系查询的便捷方法
    """
    
    async def associate(self, related_model: 'Model') -> None:
        """
        关联模型（用于belongs_to关系）
        
        Args:
            related_model: 要关联的模型
        """
        # 设置外键值
        foreign_key = self._get_foreign_key()
        if hasattr(related_model, 'id'):
            setattr(self, foreign_key, related_model.id)
            await self.save()
    
    async def dissociate(self) -> None:
        """
        取消关联（用于belongs_to关系）
        """
        foreign_key = self._get_foreign_key()
        setattr(self, foreign_key, None)
        await self.save()
    
    async def attach(self, related_ids: Union[int, List[int]], 
                    extra_data: Optional[Dict[str, Any]] = None) -> None:
        """
        附加关系（用于many_to_many关系）
        
        Args:
            related_ids: 关联ID或ID列表
            extra_data: 额外的中间表数据
        """
        if not isinstance(related_ids, list):
            related_ids = [related_ids]
        
        # 实现多对多关系的附加逻辑
        # 这里需要根据具体的中间表结构来实现
        pass
    
    async def detach(self, related_ids: Union[int, List[int]] = None) -> None:
        """
        分离关系（用于many_to_many关系）
        
        Args:
            related_ids: 要分离的关联ID，None表示分离所有
        """
        # 实现多对多关系的分离逻辑
        pass
    
    async def sync(self, related_ids: List[int], 
                  extra_data: Optional[Dict[str, Any]] = None) -> None:
        """
        同步关系（用于many_to_many关系）
        
        Args:
            related_ids: 新的关联ID列表
            extra_data: 额外的中间表数据
        """
        # 先分离所有，再附加新的
        await self.detach()
        await self.attach(related_ids, extra_data)
    
    def _get_foreign_key(self) -> str:
        """
        获取外键字段名
        
        Returns:
            外键字段名
        """
        # 这里应该根据具体的关系定义来获取外键字段名
        # 简化实现，实际需要根据关系配置来确定
        return f"{self.__class__.__name__.lower()}_id"


# 示例用法
"""
from fastorm.mixins.relations import RelationsMixin, RelationQueryMixin

class User(Model, RelationsMixin, RelationQueryMixin):
    def posts(self):
        '''用户的文章'''
        return self.has_many(Post, 'user_id')
    
    def profile(self):
        '''用户资料'''
        return self.has_one(Profile, 'user_id')
    
    def roles(self):
        '''用户角色（多对多）'''
        return self.belongs_to_many(
            Role, 'user_roles', 'user_id', 'role_id'
        )

class Post(Model, RelationsMixin):
    def user(self):
        '''文章作者'''
        return self.belongs_to(User, 'user_id')
    
    def comments(self):
        '''文章评论'''
        return self.has_many(Comment, 'post_id')

class Profile(Model, RelationsMixin):
    def user(self):
        '''资料所属用户'''
        return self.belongs_to(User, 'user_id')

# 使用示例

# 基础关系访问
user = await User.find(1)
posts = await user.posts().get()           # 获取用户的所有文章
profile = await user.profile().first()     # 获取用户资料
roles = await user.roles().get()           # 获取用户角色

# 预加载关系
users = await User.with_relations('posts', 'profile').limit(10).get()
for user in users:
    print(f"用户: {user.name}")
    print(f"文章数: {len(user.posts)}")      # 已预加载，不会产生N+1查询
    print(f"资料: {user.profile.bio}")       # 已预加载

# 关系查询链式调用
recent_posts = await user.posts().where('status', 'published').order_by('created_at', 'desc').limit(5).get()

# 关系操作
post = await Post.find(1)
await post.associate(user)                  # 设置文章作者
await post.dissociate()                     # 取消关联

# 多对多关系操作
await user.roles().attach([1, 2, 3])        # 附加角色
await user.roles().detach([2])              # 分离角色
await user.roles().sync([1, 3, 4])          # 同步角色

# 转换为字典并包含关系
user_data = user.to_dict_with_relations('posts', 'profile')
""" 