#!/usr/bin/env python3
"""
FastORM 演示项目生成器

自动创建一个完整可运行的FastORM演示项目
"""

import os
import shutil
from pathlib import Path


def create_demo_project():
    """创建演示项目"""
    
    project_name = "fastorm_demo"
    print(f"🚀 创建FastORM演示项目: {project_name}")
    
    # 创建项目目录
    project_path = Path(project_name)
    if project_path.exists():
        print(f"❌ 目录 {project_name} 已存在，请先删除或重命名")
        return False
    
    project_path.mkdir()
    
    # 复制FastORM库
    if Path("fastorm").exists():
        shutil.copytree("fastorm", project_path / "fastorm")
        print("✅ FastORM库已复制")
    else:
        print("❌ 找不到fastorm目录")
        return False
    
    # 创建app目录
    app_path = project_path / "app"
    app_path.mkdir()
    
    # 创建文件
    files = {
        "app/__init__.py": "",
        "app/database.py": get_database_content(),
        "app/models.py": get_models_content(),
        "app/main.py": get_main_content(),
        "run.py": get_run_content(),
        "requirements.txt": get_requirements_content(),
        "README.md": get_readme_content(),
        ".env.example": get_env_content(),
    }
    
    for file_path, content in files.items():
        full_path = project_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"✅ 演示项目 '{project_name}' 创建完成！")
    print(f"📁 项目位置: {project_path.absolute()}")
    print("\n🚀 快速启动:")
    print(f"cd {project_name}")
    print("pip install -r requirements.txt")
    print("python run.py")
    print("\n🌐 然后访问:")
    print("- http://localhost:8000 - 首页")
    print("- http://localhost:8000/docs - API文档")
    
    return True


def get_database_content():
    return '''"""数据库配置"""
from fastorm.config import set_config
from fastorm.connection.database import DatabaseManager

# 配置FastORM
set_config(
    database_url="sqlite+aiosqlite:///./demo.db",
    debug=True,
    echo_sql=True,
)

# 数据库管理器
db_manager = DatabaseManager()

async def init_database():
    """初始化数据库"""
    await db_manager.create_all_tables()
    print("✅ 数据库初始化完成")

async def close_database():
    """关闭数据库连接"""
    await db_manager.close()
    print("✅ 数据库连接已关闭")
'''


def get_models_content():
    return '''"""数据模型"""
from fastorm.model.model import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Boolean
from typing import Optional

class User(Model):
    """用户模型"""
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="姓名")
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="邮箱")
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年龄")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    
    def __repr__(self) -> str:
        return f"<User(name='{self.name}', email='{self.email}')>"

class Post(Model):
    """文章模型"""
    __tablename__ = "posts"
    
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容")
    author_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="作者ID")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否发布")
    
    def __repr__(self) -> str:
        return f"<Post(title='{self.title}')>"
'''


def get_main_content():
    return '''"""FastAPI应用主文件"""
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional

from .database import init_database, close_database
from .models import User, Post

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    await init_database()
    
    # 创建示例数据
    await create_sample_data()
    
    yield
    
    # 关闭时
    await close_database()

async def create_sample_data():
    """创建示例数据"""
    # 检查是否已有数据
    user_count = await User.count()
    if user_count == 0:
        # 创建示例用户
        users = [
            {"name": "张三", "email": "zhangsan@example.com", "age": 25},
            {"name": "李四", "email": "lisi@example.com", "age": 30},
            {"name": "王五", "email": "wangwu@example.com", "age": 28},
        ]
        
        for user_data in users:
            await User.create(**user_data)
        
        # 创建示例文章
        posts = [
            {"title": "FastORM简介", "content": "FastORM是一个现代化的ORM框架...", "author_id": 1},
            {"title": "Python异步编程", "content": "异步编程是现代Python开发的重要技能...", "author_id": 2},
            {"title": "FastAPI最佳实践", "content": "FastAPI提供了构建现代API的强大工具...", "author_id": 1},
        ]
        
        for post_data in posts:
            await Post.create(**post_data)
        
        print("✅ 示例数据创建完成")

# 创建FastAPI应用
app = FastAPI(
    title="FastORM演示项目",
    description="使用FastORM构建的演示API",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic模型
class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int]
    is_active: bool
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    title: str
    content: str
    author_id: int

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    is_published: bool
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True

# 根路由
@app.get("/")
async def root():
    return {
        "message": "欢迎使用FastORM演示项目!",
        "docs": "/docs",
        "endpoints": {
            "users": "/users",
            "posts": "/posts",
            "stats": "/stats"
        }
    }

# 统计信息
@app.get("/stats")
async def get_stats():
    """获取统计信息"""
    user_count = await User.count()
    post_count = await Post.count()
    
    return {
        "users": user_count,
        "posts": post_count,
        "database": "SQLite",
        "orm": "FastORM"
    }

# 用户相关API
@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """创建用户"""
    new_user = await User.create(
        name=user.name,
        email=user.email,
        age=user.age
    )
    return new_user

@app.get("/users/", response_model=List[UserResponse])
async def get_users():
    """获取所有用户"""
    users = await User.all()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """获取单个用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserCreate):
    """更新用户"""
    user = await User.find_or_fail(user_id)
    await user.update(
        name=user_data.name,
        email=user_data.email,
        age=user_data.age
    )
    return user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """删除用户（软删除）"""
    user = await User.find_or_fail(user_id)
    await user.delete()
    return {"message": "用户删除成功"}

# 文章相关API
@app.post("/posts/", response_model=PostResponse)
async def create_post(post: PostCreate):
    """创建文章"""
    # 验证作者存在
    author = await User.find(post.author_id)
    if not author:
        raise HTTPException(status_code=400, detail="作者不存在")
    
    new_post = await Post.create(
        title=post.title,
        content=post.content,
        author_id=post.author_id
    )
    return new_post

@app.get("/posts/", response_model=List[PostResponse])
async def get_posts():
    """获取所有文章"""
    posts = await Post.all()
    return posts

@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int):
    """获取单个文章"""
    post = await Post.find(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return post

@app.put("/posts/{post_id}/publish")
async def publish_post(post_id: int):
    """发布文章"""
    post = await Post.find_or_fail(post_id)
    await post.update(is_published=True)
    return {"message": "文章发布成功"}

# 查询示例
@app.get("/users/search/")
async def search_users(name: Optional[str] = None, min_age: Optional[int] = None):
    """搜索用户（演示查询功能）"""
    query = User.query()
    
    if name:
        query = query.where('name', 'like', f'%{name}%')
    
    if min_age:
        query = query.where('age', '>=', min_age)
    
    users = await query.get()
    return users
'''


def get_run_content():
    return '''#!/usr/bin/env python3
"""启动FastORM演示项目"""

import uvicorn

if __name__ == "__main__":
    print("🚀 启动FastORM演示项目...")
    print("📚 API文档: http://localhost:8000/docs")
    print("🌐 项目首页: http://localhost:8000")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
'''


def get_requirements_content():
    return '''# FastORM演示项目依赖

# Web框架
fastapi>=0.100.0
uvicorn[standard]>=0.20.0

# 数据库相关
sqlalchemy>=2.0.0
pydantic>=2.0.0
aiosqlite>=0.19.0

# 可选：其他数据库驱动
# asyncpg>=0.28.0        # PostgreSQL
# aiomysql>=0.1.1        # MySQL

# 工具
python-multipart>=0.0.6
'''


def get_readme_content():
    return '''# FastORM 演示项目

这是一个使用FastORM构建的完整演示项目，展示了FastORM的核心功能。

## 🚀 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用
python run.py

# 3. 访问应用
# http://localhost:8000      - 项目首页
# http://localhost:8000/docs - API文档
```

## 📁 项目结构

```
fastorm_demo/
├── fastorm/           # FastORM库
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI应用
│   ├── database.py   # 数据库配置
│   └── models.py     # 数据模型
├── run.py            # 启动脚本
├── requirements.txt  # 依赖列表
└── README.md         # 说明文档
```

## 🔧 功能特性

### 数据模型
- **User模型**: 用户管理（姓名、邮箱、年龄）
- **Post模型**: 文章管理（标题、内容、作者）

### API功能
- ✅ 用户CRUD操作
- ✅ 文章CRUD操作
- ✅ 查询和搜索
- ✅ 软删除功能
- ✅ 时间戳自动管理
- ✅ API文档自动生成

### FastORM特性展示
- ✅ 简洁的模型定义
- ✅ 链式查询API
- ✅ 自动SQL安全防护
- ✅ 异步数据库操作
- ✅ SQLAlchemy 2.0集成
- ✅ Pydantic 2.0集成

## 📚 API使用示例

### 创建用户
```bash
curl -X POST "http://localhost:8000/users/" \\
     -H "Content-Type: application/json" \\
     -d '{"name": "张三", "email": "zhang@example.com", "age": 25}'
```

### 获取所有用户
```bash
curl "http://localhost:8000/users/"
```

### 搜索用户
```bash
curl "http://localhost:8000/users/search/?name=张&min_age=20"
```

### 创建文章
```bash
curl -X POST "http://localhost:8000/posts/" \\
     -H "Content-Type: application/json" \\
     -d '{"title": "我的第一篇文章", "content": "这是内容...", "author_id": 1}'
```

## 🎯 核心代码示例

### 模型定义
```python
from fastorm.model.model import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer

class User(Model):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

### 查询操作
```python
# 简单查询
users = await User.all()
user = await User.find(1)

# 条件查询
adults = await User.where('age', '>=', 18).get()

# 链式查询
result = await User.where('name', 'like', '%张%')\\
                  .where('age', '>', 20)\\
                  .order_by('age')\\
                  .limit(10)\\
                  .get()
```

## 🔒 安全特性

- ✅ SQL注入防护：所有查询自动使用参数化
- ✅ 类型安全：基于SQLAlchemy 2.0和Pydantic 2.0
- ✅ 输入验证：自动验证API输入数据
- ✅ 软删除：默认使用软删除，数据更安全

## 📈 性能特性

- ✅ 异步操作：所有数据库操作都是异步的
- ✅ 连接池：自动管理数据库连接池
- ✅ 查询优化：基于SQLAlchemy的查询优化
- ✅ 缓存支持：内置查询缓存机制

## 🛠️ 扩展开发

这个演示项目提供了完整的基础架构，您可以基于此：

1. 添加更多数据模型
2. 实现用户认证和权限
3. 添加文件上传功能
4. 集成Redis缓存
5. 添加定时任务
6. 部署到生产环境

## 📝 更多资源

- 📖 [FastORM文档](docs/)
- 🔧 [配置指南](fastorm_production_config.py)
- 🧪 [测试示例](test_p1_functionality.py)
- 🔒 [安全检查](production_readiness_check.py)

---

🎉 **恭喜！您已成功运行FastORM演示项目！**

现在您可以开始使用FastORM构建自己的项目了。
'''


def get_env_content():
    return '''# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./demo.db

# 应用配置
DEBUG=true
ECHO_SQL=true
'''


if __name__ == "__main__":
    success = create_demo_project()
    if success:
        print("\n🎉 演示项目创建成功！")
        print("💡 接下来您可以:")
        print("1. 查看项目代码了解FastORM的使用方法")
        print("2. 运行项目体验FastORM的功能")
        print("3. 基于演示项目开发您自己的应用")
    else:
        print("\n❌ 演示项目创建失败") 