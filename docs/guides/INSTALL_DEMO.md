# 🚀 FastORM 安装与快速上手指南

## 📦 简介

FastORM是专为FastAPI优化的现代异步ORM框架，基于SQLAlchemy 2.0和Pydantic 2.11构建。本指南将帮助您快速安装和使用FastORM。

## 🎯 安装方式

### **🚀 一键安装（开箱即用）**

```bash
pip install fastorm
```

**🎉 包含完整功能栈：**
- ✅ **SQLAlchemy 2.0** - 现代异步ORM核心
- ✅ **Pydantic 2.11** - 类型安全与数据验证
- ✅ **FastAPI支持** - 深度集成，开箱即用
- ✅ **全数据库支持** - SQLite、PostgreSQL、MySQL
- ✅ **缓存支持** - Redis集成
- ✅ **CLI工具** - 强大的命令行工具
- ✅ **性能监控** - 内置查询分析
- ✅ **测试工厂** - 完整测试支持

### **📋 环境要求**
- **Python 3.10+** （推荐 3.11+）
- **支持平台**: Windows、macOS、Linux

## 🏃‍♂️ 2分钟快速上手

### **方式一：全新项目（推荐）**

```bash
# 1. 安装FastORM
pip install fastorm

# 2. 创建新项目
fastorm init my-blog --template api --database postgresql

# 3. 进入项目目录
cd my-blog

# 4. 创建第一个模型
fastorm create:model Post \
  -f "title:str:required,length:200" \
  -f "content:text:required" \
  -f "published:bool:default:false"

# 5. 运行数据库迁移
fastorm migrate --auto -m "创建文章表"
fastorm migrate --upgrade

# 6. 启动开发服务器
fastorm serve
```

### **方式二：现有项目集成**

```bash
# 1. 进入现有FastAPI项目
cd your-existing-project

# 2. 安装FastORM
pip install fastorm

# 3. 一键集成
fastorm setup --database postgresql

# 4. 转换现有模型（可选）
fastorm convert app/models.py

# 5. 测试集成效果
python -m pytest tests/
```

### **方式三：手动集成**

```python
# requirements.txt
fastorm>=1.0.0

# models.py
from fastorm import BaseModel, Database
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class User(BaseModel):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# main.py
from fastapi import FastAPI
from fastorm import Database

app = FastAPI()

@app.on_event("startup")
async def startup():
    await Database.init("postgresql+asyncpg://user:pass@localhost/db")

@app.on_event("shutdown") 
async def shutdown():
    await Database.close()

@app.get("/users")
async def get_users():
    async with Database.session() as session:
        users = await User.all(session)
        return [user.to_dict() for user in users]
```

## 🛠️ CLI工具演示

FastORM提供了强大的命令行工具来提升开发效率：

### **项目管理**
```bash
# 创建新项目
fastorm init my-project --template api --database postgresql --docker

# 现有项目集成
fastorm setup --dry-run  # 预览集成步骤
fastorm setup           # 执行集成

# 模型转换
fastorm convert models.py --backup --dry-run
```

### **开发工具**
```bash
# 模型生成
fastorm create:model User \
  -f "name:str:required,length:100" \
  -f "email:str:unique" \
  -f "age:int:default:0"

# 数据库迁移
fastorm migrate --auto -m "添加用户表"
fastorm migrate --upgrade
fastorm migrate --history

# 数据库操作
fastorm db create
fastorm db seed    # 填充测试数据
fastorm db reset   # 重置数据库
```

### **开发服务器**
```bash
# 启动开发服务器
fastorm serve --host 0.0.0.0 --port 8000 --reload

# 交互式Shell
fastorm shell
```

## 🎯 完整使用示例

### **1. 模型定义**
```python
from fastorm import BaseModel, Database
from fastorm.mixins import TimestampMixin, SoftDeleteMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from typing import List

class User(BaseModel, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(length=100)
    email: Mapped[str] = mapped_column(unique=True)
    
    # 关系定义
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="user")

class Post(BaseModel, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(length=200)
    content: Mapped[str]
    published: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # 关系定义
    user: Mapped["User"] = relationship("User", back_populates="posts")
```

### **2. 数据库操作**
```python
async def main():
    # 初始化数据库
    await Database.init("postgresql+asyncpg://user:pass@localhost/blog")
    
    async with Database.session() as session:
        # 创建用户
        user = await User.create(session, 
            name="张三", 
            email="zhang@example.com"
        )
        
        # 创建文章
        post = await Post.create(session,
            title="FastORM使用指南",
            content="这是一篇关于FastORM的文章",
            user_id=user.id,
            published=True
        )
        
        # 复杂查询
        published_posts = await Post.query(session)\
            .where(Post.published == True)\
            .join(Post.user)\
            .order_by(Post.created_at.desc())\
            .limit(10)\
            .all()
        
        # 预加载关系
        posts_with_users = await Post.query(session)\
            .options(selectinload(Post.user))\
            .all()
        
        # 分页查询
        page_result = await Post.query(session)\
            .where(Post.published == True)\
            .paginate(page=1, size=20)
        
        print(f"总共 {page_result.total} 篇文章")
        print(f"当前页 {len(page_result.items)} 篇文章")
```

### **3. FastAPI集成**
```python
from fastapi import FastAPI, Depends, HTTPException
from fastorm import UserRepository, get_repository
from pydantic import BaseModel

app = FastAPI(title="FastORM Blog API")

# Pydantic schemas
class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

# API路由
@app.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_repository(UserRepository))
):
    user = await user_repo.create(user_data.dict())
    return UserResponse.from_orm(user)

@app.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    size: int = 20,
    user_repo: UserRepository = Depends(get_repository(UserRepository))
):
    result = await user_repo.paginate(page=page, size=size)
    return [UserResponse.from_orm(user) for user in result.items]
```

### **4. 性能监控**
```python
from fastorm import QueryProfiler, PerformanceMonitor

# 启用性能监控
monitor = PerformanceMonitor()
await monitor.start()

# 查询性能分析
with QueryProfiler() as profiler:
    users = await User.query(session).with_relations("posts").all()
    
    # 检查N+1问题
    if profiler.has_n_plus_one():
        print("⚠️ 检测到N+1查询问题")
        for suggestion in profiler.get_suggestions():
            print(f"建议: {suggestion}")

# 生成性能报告
report = await monitor.generate_report()
await report.export_html("performance_report.html")
```

### **5. 测试支持**
```python
from fastorm.testing import Factory, DatabaseTestCase
import pytest

# 数据工厂
class UserFactory(Factory):
    class Meta:
        model = User
    
    name = "用户{sequence}"
    email = "user{sequence}@example.com"

# 测试用例
class TestUserAPI(DatabaseTestCase):
    async def test_create_user(self):
        # 使用工厂创建测试数据
        user = await UserFactory.create()
        assert user.name.startswith("用户")
        
        # 批量创建
        users = await UserFactory.create_batch(5)
        assert len(users) == 5
    
    async def test_user_relationships(self):
        user = await UserFactory.create()
        post = await PostFactory.create(user=user)
        
        # 测试关系
        await user.posts.load()
        assert len(user.posts) == 1
        assert user.posts[0].title == post.title
```

## 🚀 数据库支持

FastORM 开箱即用支持三大主流数据库：

### **SQLite（开发/测试）**
```python
# 本地文件数据库
await Database.init("sqlite+aiosqlite:///app.db")

# 内存数据库（测试）
await Database.init("sqlite+aiosqlite:///:memory:")
```

### **PostgreSQL（推荐生产）**
```python
# 基本连接
await Database.init("postgresql+asyncpg://user:pass@localhost/dbname")

# 完整配置
await Database.init(
    "postgresql+asyncpg://user:pass@localhost:5432/dbname",
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)
```

### **MySQL/MariaDB**
```python
# MySQL连接
await Database.init("mysql+aiomysql://user:pass@localhost/dbname")

# 带字符集配置
await Database.init(
    "mysql+aiomysql://user:pass@localhost/dbname?charset=utf8mb4"
)
```

## 🐳 Docker部署

### **Dockerfile示例**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装FastORM
COPY requirements.txt .
RUN pip install --no-cache-dir fastorm

# 复制应用代码
COPY . .

# 启动应用
CMD ["fastorm", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

### **docker-compose.yml示例**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: myapp
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    
volumes:
  postgres_data:
```

## 🚀 生产环境部署

### **配置管理**
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### **环境变量**
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/prod_db
REDIS_URL=redis://localhost:6379
DEBUG=false
```

### **性能优化建议**
```python
# 连接池配置
await Database.init(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)

# 启用查询缓存
await User.query(session).cache(ttl=3600).all()

# 使用读写分离
from fastorm import ReadWriteRepository

class UserRepository(ReadWriteRepository):
    model = User

# 批量操作优化
await User.bulk_create(session, user_data_list)
```

## 📚 学习资源

### **官方资源**
- 📖 **[完整文档](https://fastorm.dev)** - 详细API参考
- 🎬 **[视频教程](https://fastorm.dev/tutorials)** - 从入门到精通  
- 💡 **[最佳实践](https://fastorm.dev/best-practices)** - 企业级开发指南
- 🏗️ **[项目模板](https://github.com/fastorm/templates)** - 快速启动项目

### **社区支持**
- 💬 **[Discord社区](https://discord.gg/fastorm)** - 实时技术交流
- 🐛 **[GitHub Issues](https://github.com/fastorm/fastorm/issues)** - 问题报告
- 💡 **[GitHub Discussions](https://github.com/fastorm/fastorm/discussions)** - 功能讨论

## 🔧 故障排除

### **常见问题**

#### 1. 安装问题
```bash
# 清理缓存重新安装
pip uninstall fastorm
pip cache purge
pip install fastorm

# 升级到最新版本
pip install --upgrade fastorm
```

#### 2. 数据库连接问题
```python
# 检查连接字符串
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/dbname"

# 测试连接
from fastorm import Database
await Database.test_connection(DATABASE_URL)
```

#### 3. 导入错误
```python
# 确保正确导入
from fastorm import BaseModel, Database
from fastorm.mixins import TimestampMixin

# 而不是
from sqlalchemy.orm import declarative_base  # ❌ 错误
```

### **获取帮助**
- 📧 **邮件支持**: support@fastorm.dev
- 💬 **即时聊天**: [Discord](https://discord.gg/fastorm)
- 📋 **问题报告**: [GitHub Issues](https://github.com/fastorm/fastorm/issues)

---

## 🎉 开始您的FastORM之旅！

现在您已经掌握了FastORM的安装和基础使用方法。只需一个命令 `pip install fastorm`，就能获得完整的现代异步ORM解决方案！

**记住**：FastORM的设计理念是"简洁如ThinkORM，优雅如Eloquent，现代如FastAPI"。享受开发的乐趣！🚀 