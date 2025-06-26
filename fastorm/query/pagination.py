"""
FastORM 分页器

提供Eloquent风格的优雅分页功能。

示例:
```python
# 基础分页
paginator = await User.where('status', 'active').paginate(page=1, per_page=20)

# 高级分页
paginator = await User.query()\
    .where('age', '>', 18)\
    .with_('posts')\
    .order_by('created_at', 'desc')\
    .paginate(page=2, per_page=15)

# 分页器响应
print(f"总记录数: {paginator.total}")
print(f"当前页: {paginator.current_page}")
print(f"总页数: {paginator.last_page}")
print(f"是否有下一页: {paginator.has_next_page}")

# 遍历数据
for user in paginator.items:
    print(user.name)

# 分页器 JSON 序列化
json_data = paginator.to_dict()
```
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Generic, TypeVar

T = TypeVar('T')


class Paginator(Generic[T]):
    """分页器类 - 提供Eloquent风格的分页功能"""
    
    def __init__(
        self, 
        items: List[T],
        total: int,
        per_page: int,
        current_page: int,
        path: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None
    ):
        """初始化分页器
        
        Args:
            items: 当前页的数据项
            total: 总记录数
            per_page: 每页记录数
            current_page: 当前页码
            path: 基础路径（用于生成分页链接）
            query_params: 查询参数（用于生成分页链接）
        """
        self.items = items
        self.total = total
        self.per_page = per_page
        self.current_page = current_page
        self.path = path or ""
        self.query_params = query_params or {}
        
        # 计算分页信息
        self.last_page = max(1, math.ceil(total / per_page))
        self.from_index = (current_page - 1) * per_page + 1 if items else 0
        self.to_index = min(self.from_index + len(items) - 1, total) if items else 0
        self.has_pages = self.last_page > 1
        self.has_more_pages = current_page < self.last_page
        self.on_first_page = current_page == 1
        self.on_last_page = current_page == self.last_page
    
    @property
    def count(self) -> int:
        """当前页的记录数"""
        return len(self.items)
    
    @property
    def first_item(self) -> Optional[T]:
        """当前页的第一条记录"""
        return self.items[0] if self.items else None
    
    @property
    def last_item(self) -> Optional[T]:
        """当前页的最后一条记录"""
        return self.items[-1] if self.items else None
    
    @property
    def has_next_page(self) -> bool:
        """是否有下一页"""
        return self.current_page < self.last_page
    
    @property
    def has_previous_page(self) -> bool:
        """是否有上一页"""
        return self.current_page > 1
    
    @property
    def next_page(self) -> Optional[int]:
        """下一页页码"""
        return self.current_page + 1 if self.has_next_page else None
    
    @property
    def previous_page(self) -> Optional[int]:
        """上一页页码"""
        return self.current_page - 1 if self.has_previous_page else None
    
    def get_page_range(
        self, 
        on_each_side: int = 3, 
        on_ends: int = 1
    ) -> List[int]:
        """获取分页范围
        
        Args:
            on_each_side: 当前页两侧显示的页码数
            on_ends: 首尾显示的页码数
            
        Returns:
            页码列表
            
        示例:
            当前页=5, 总页数=20, on_each_side=2, on_ends=1
            返回: [1, 3, 4, 5, 6, 7, 20]
        """
        if self.last_page <= 10:
            return list(range(1, self.last_page + 1))
        
        pages = set()
        
        # 添加首尾页码
        for i in range(1, min(on_ends + 1, self.last_page + 1)):
            pages.add(i)
        for i in range(max(self.last_page - on_ends + 1, 1), self.last_page + 1):
            pages.add(i)
        
        # 添加当前页附近的页码
        start = max(1, self.current_page - on_each_side)
        end = min(self.last_page + 1, self.current_page + on_each_side + 1)
        for i in range(start, end):
            pages.add(i)
        
        return sorted(list(pages))
    
    def get_url_range(
        self, 
        start: int, 
        end: int
    ) -> Dict[int, str]:
        """获取指定范围的分页URL字典
        
        Args:
            start: 开始页码
            end: 结束页码
            
        Returns:
            页码到URL的映射字典
        """
        urls = {}
        for page in range(start, end + 1):
            if 1 <= page <= self.last_page:
                urls[page] = self.url(page)
        return urls
    
    def url(self, page: int) -> str:
        """生成指定页码的URL
        
        Args:
            page: 页码
            
        Returns:
            分页URL
        """
        if not self.path:
            return f"?page={page}"
        
        params = self.query_params.copy()
        params['page'] = page
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.path}?{query_string}"
    
    def next_page_url(self) -> Optional[str]:
        """下一页URL"""
        return self.url(self.next_page) if self.has_next_page else None
    
    def previous_page_url(self) -> Optional[str]:
        """上一页URL"""
        return self.url(self.previous_page) if self.has_previous_page else None
    
    def first_page_url(self) -> str:
        """首页URL"""
        return self.url(1)
    
    def last_page_url(self) -> str:
        """末页URL"""
        return self.url(self.last_page)
    
    def is_empty(self) -> bool:
        """是否为空分页"""
        return len(self.items) == 0
    
    def is_not_empty(self) -> bool:
        """是否不为空"""
        return not self.is_empty()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            包含完整分页信息的字典
        """
        return {
            'data': [
                item.to_dict() if hasattr(item, 'to_dict') else item 
                for item in self.items
            ],
            'current_page': self.current_page,
            'last_page': self.last_page,
            'per_page': self.per_page,
            'total': self.total,
            'from': self.from_index,
            'to': self.to_index,
            'has_pages': self.has_pages,
            'has_more_pages': self.has_more_pages,
            'has_next_page': self.has_next_page,
            'has_previous_page': self.has_previous_page,
            'next_page': self.next_page,
            'previous_page': self.previous_page,
            'links': {
                'first': self.first_page_url(),
                'last': self.last_page_url(),
                'prev': self.previous_page_url(),
                'next': self.next_page_url(),
            }
        }
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """转换为简化的字典格式（仅包含基础信息）
        
        Returns:
            简化的分页信息字典
        """
        return {
            'data': [
                item.to_dict() if hasattr(item, 'to_dict') else item 
                for item in self.items
            ],
            'current_page': self.current_page,
            'last_page': self.last_page,
            'per_page': self.per_page,
            'total': self.total
        }
    
    def __iter__(self):
        """支持遍历当前页的数据"""
        return iter(self.items)
    
    def __len__(self) -> int:
        """返回当前页的记录数"""
        return len(self.items)
    
    def __getitem__(self, index: int) -> T:
        """支持索引访问当前页的数据"""
        return self.items[index]
    
    def __bool__(self) -> bool:
        """布尔值检查 - 有数据时为True"""
        return bool(self.items)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Paginator(items={len(self.items)}, "
            f"page={self.current_page}/{self.last_page}, "
            f"total={self.total})"
        )


class SimplePaginator(Generic[T]):
    """简单分页器 - 只提供上一页/下一页功能，不计算总数"""
    
    def __init__(
        self, 
        items: List[T],
        per_page: int,
        current_page: int,
        has_more: bool = False,
        path: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None
    ):
        """初始化简单分页器
        
        Args:
            items: 当前页的数据项
            per_page: 每页记录数
            current_page: 当前页码
            has_more: 是否还有更多数据
            path: 基础路径
            query_params: 查询参数
        """
        self.items = items
        self.per_page = per_page
        self.current_page = current_page
        self.has_more = has_more
        self.path = path or ""
        self.query_params = query_params or {}
        
        self.on_first_page = current_page == 1
    
    @property
    def count(self) -> int:
        """当前页的记录数"""
        return len(self.items)
    
    @property
    def has_previous_page(self) -> bool:
        """是否有上一页"""
        return self.current_page > 1
    
    @property
    def has_next_page(self) -> bool:
        """是否有下一页"""
        return self.has_more
    
    @property
    def next_page(self) -> Optional[int]:
        """下一页页码"""
        return self.current_page + 1 if self.has_more else None
    
    @property
    def previous_page(self) -> Optional[int]:
        """上一页页码"""
        return self.current_page - 1 if self.has_previous_page else None
    
    def url(self, page: int) -> str:
        """生成指定页码的URL"""
        if not self.path:
            return f"?page={page}"
        
        params = self.query_params.copy()
        params['page'] = page
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.path}?{query_string}"
    
    def next_page_url(self) -> Optional[str]:
        """下一页URL"""
        return self.url(self.next_page) if self.has_next_page else None
    
    def previous_page_url(self) -> Optional[str]:
        """上一页URL"""
        return self.url(self.previous_page) if self.has_previous_page else None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'data': [
                item.to_dict() if hasattr(item, 'to_dict') else item 
                for item in self.items
            ],
            'current_page': self.current_page,
            'per_page': self.per_page,
            'has_more': self.has_more,
            'has_next_page': self.has_next_page,
            'has_previous_page': self.has_previous_page,
            'next_page': self.next_page,
            'previous_page': self.previous_page,
            'links': {
                'prev': self.previous_page_url(),
                'next': self.next_page_url(),
            }
        }
    
    def __iter__(self):
        """支持遍历当前页的数据"""
        return iter(self.items)
    
    def __len__(self) -> int:
        """返回当前页的记录数"""
        return len(self.items)
    
    def __getitem__(self, index: int) -> T:
        """支持索引访问当前页的数据"""
        return self.items[index]
    
    def __bool__(self) -> bool:
        """布尔值检查 - 有数据时为True"""
        return bool(self.items)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"SimplePaginator(items={len(self.items)}, "
            f"page={self.current_page}, "
            f"has_more={self.has_more})"
        )


def create_paginator(
    items: List[T],
    total: int,
    per_page: int,
    current_page: int,
    path: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None
) -> Paginator[T]:
    """创建分页器的工厂函数
    
    Args:
        items: 当前页的数据项
        total: 总记录数
        per_page: 每页记录数
        current_page: 当前页码
        path: 基础路径
        query_params: 查询参数
        
    Returns:
        分页器实例
    """
    return Paginator(
        items=items,
        total=total,
        per_page=per_page,
        current_page=current_page,
        path=path,
        query_params=query_params
    )


def create_simple_paginator(
    items: List[T],
    per_page: int,
    current_page: int,
    has_more: bool = False,
    path: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None
) -> SimplePaginator[T]:
    """创建简单分页器的工厂函数
    
    Args:
        items: 当前页的数据项
        per_page: 每页记录数
        current_page: 当前页码
        has_more: 是否还有更多数据
        path: 基础路径
        query_params: 查询参数
        
    Returns:
        简单分页器实例
    """
    return SimplePaginator(
        items=items,
        per_page=per_page,
        current_page=current_page,
        has_more=has_more,
        path=path,
        query_params=query_params
    ) 