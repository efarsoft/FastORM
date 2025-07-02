# FastAPI + FastORM 集成指南

本指南详细介绍如何在FastAPI项目中集成和使用FastORM，实现现代化的API开发。

## 📋 目录

1. [快速开始](#快速开始)
2. [项目结构](#项目结构)
3. [数据库配置](#数据库配置)
4. [模型定义](#模型定义)
5. [依赖注入](#依赖注入)
6. [API路由](#API路由)
7. [中间件集成](#中间件集成)
8. [生命周期管理](#生命周期管理)
9. [完整示例](#完整示例)
10. [最佳实践](#最佳实践)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装FastORM（包含FastAPI支持）
pip install fastorm

# 或者从源码安装
pip install -e .
```

### 2. 基础集成

```python
# main.py
from fastapi import FastAPI
from fastorm import Model, init
from contextlib import asynccontextmanager

# 数据库初始化
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init(DATABASE_URL)
    yield
    # 关闭时清理资源

app = FastAPI(lifespan=lifespan)

# 定义模型
class User(Model):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# API路由
@app.post("/users/")
async def create_user(name: str, email: str):
    user = await User.create(name=name, email=email)
    return {"id": user.id, "name": user.name, "email": user.email}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}
```

## 🏗️ 项目结构

推荐的项目结构：

```
fastapi_project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库配置
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── product.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── product.py
│   ├── api/                 # API路由
│   │   ├── __init__.py
│   │   ├── dependencies.py  # 依赖注入
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── users.py
│   │       └── products.py
│   └── middleware/          # 中间件
│       ├── __init__.py
│       └── database.py
├── alembic/                 # 数据库迁移
├── tests/
├── requirements.txt
└── .env
```

## 🗄️ 数据库配置

### config.py
```python
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"
    DATABASE_ECHO: bool = False
    
    # 连接池配置
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    # FastORM配置
    FASTORM_ENABLE_VALIDATION: bool = True
    FASTORM_ENABLE_SERIALIZATION: bool = True
    FASTORM_ENABLE_BATCH_OPERATIONS: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### database.py
```python
from fastorm import init, Database
from app.config import settings

async def init_database():
    """初始化数据库连接"""
    await init(
        database_url=settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

async def close_database():
    """关闭数据库连接"""
    await Database.close()
```

## 📊 模型定义

### models/user.py
```python
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from fastorm import Model
from fastorm.validation import field_validator

class User(Model):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # FastORM验证器
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('无效的邮箱格式')
        return v.lower()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError('姓名长度至少2个字符')
        return v.strip()
    
    # 业务方法
    async def activate(self):
        """激活用户"""
        await self.update(is_active=True, updated_at=datetime.utcnow())
    
    async def deactivate(self):
        """停用用户"""
        await self.update(is_active=False, updated_at=datetime.utcnow())
    
    @classmethod
    async def get_active_users(cls):
        """获取活跃用户"""
        return await cls.where('is_active', True).get()
```

## 🔄 依赖注入

### api/dependencies.py
```python
from fastapi import Depends, HTTPException
from fastorm import Database
from app.models.user import User

# 数据库会话依赖
async def get_database():
    """获取数据库实例（读操作）"""
    return Database

async def get_write_database():
    """获取数据库实例（写操作）"""
    return Database

# 用户依赖
async def get_current_user(user_id: int) -> User:
    """获取当前用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已停用")
    return user

# 分页依赖
def get_pagination_params(page: int = 1, size: int = 20):
    """获取分页参数"""
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    offset = (page - 1) * size
    return {"offset": offset, "limit": size, "page": page, "size": size}
```

## 🛣️ API路由

### schemas/user.py
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
```

### api/v1/users.py
```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastorm import ValidationEngine, SerializationEngine

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.api.dependencies import get_current_user, get_pagination_params

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """创建用户"""
    try:
        # 使用FastORM验证
        validation_engine = ValidationEngine()
        validated_data = await validation_engine.validate_model(
            User, user_data.dict()
        )
        
        # 创建用户
        user = await User.create(**validated_data)
        return user
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[UserResponse])
async def list_users(
    pagination: dict = Depends(get_pagination_params),
    active_only: bool = Query(True, description="只显示活跃用户")
):
    """用户列表"""
    query = User.query()
    
    if active_only:
        query = query.where('is_active', True)
    
    users = await query.offset(pagination["offset"]).limit(pagination["limit"]).get()
    
    # 使用FastORM序列化
    serialization_engine = SerializationEngine()
    return await serialization_engine.serialize_batch(users)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """获取单个用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserUpdate):
    """更新用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 只更新提供的字段
    update_data = user_data.dict(exclude_unset=True)
    if update_data:
        update_data['updated_at'] = datetime.utcnow()
        await user.update(**update_data)
    
    return user

@router.delete("/{user_id}")
async def delete_user(user_id: int):
    """删除用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    await user.delete()
    return {"message": "用户删除成功"}

@router.post("/{user_id}/activate")
async def activate_user(user_id: int):
    """激活用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    await user.activate()
    return {"message": "用户激活成功"}

@router.post("/batch", response_model=List[UserResponse])
async def batch_create_users(users_data: List[UserCreate]):
    """批量创建用户"""
    from fastorm.query.batch import BatchEngine
    
    try:
        # 使用FastORM批量操作
        batch_engine = BatchEngine()
        data = [user.dict() for user in users_data]
        
        result = await batch_engine.batch_insert(User, data)
        
        # 获取创建的用户
        if result.get('created_ids'):
            users = await User.where('id', 'in', result['created_ids']).get()
            return users
        
        return []
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"批量创建失败: {str(e)}")
```

## 🔧 中间件集成

### middleware/database.py
```python
import time
from fastapi import Request, Response
from fastorm import Database

async def database_middleware(request: Request, call_next):
    """数据库中间件"""
    start_time = time.time()
    
    # 在请求上下文中添加数据库信息
    request.state.db_start_time = start_time
    
    try:
        response = await call_next(request)
        
        # 添加响应头
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Database-Engine"] = "FastORM"
        
        return response
        
    except Exception as e:
        # 数据库错误处理
        if "database" in str(e).lower():
            # 记录数据库错误
            pass
        raise
```

## 🚦 生命周期管理

### main.py (完整版本)
```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_database, close_database
from app.api.v1 import users
from app.middleware.database import database_middleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("🚀 启动 FastAPI + FastORM 应用")
    
    try:
        # 初始化数据库
        await init_database()
        logger.info("✅ 数据库连接初始化完成")
        
        # 这里可以添加其他启动任务
        # - 预热缓存
        # - 初始化外部服务连接
        # - 数据预加载等
        
        yield
        
    finally:
        # 关闭
        logger.info("🔄 关闭 FastAPI + FastORM 应用")
        
        try:
            await close_database()
            logger.info("✅ 数据库连接已关闭")
        except Exception as e:
            logger.error(f"❌ 数据库关闭失败: {e}")

# 创建FastAPI应用
app = FastAPI(
    title="FastAPI + FastORM 示例",
    description="使用FastORM的现代FastAPI应用",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加数据库中间件
app.middleware("http")(database_middleware)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误"}
    )

# 注册路由
app.include_router(users.router, prefix="/api/v1")

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 可以添加数据库连接检查
        return {
            "status": "healthy",
            "database": "connected",
            "fastorm_version": "0.1.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

## 📈 最佳实践

### 1. 数据库配置优化

```python
# 生产环境数据库配置
PRODUCTION_DB_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 60,
    "pool_recycle": 3600,
    "echo": False,  # 生产环境关闭SQL日志
}

# 开发环境配置
DEVELOPMENT_DB_CONFIG = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "echo": True,  # 开发环境开启SQL日志
}
```

### 2. 错误处理

```python
from fastorm.validation import ValidationError
from fastorm.serialization import SerializationError

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "数据验证失败",
            "errors": exc.errors if hasattr(exc, 'errors') else []
        }
    )

@app.exception_handler(SerializationError)
async def serialization_exception_handler(request: Request, exc: SerializationError):
    return JSONResponse(
        status_code=500,
        content={"detail": "数据序列化失败"}
    )
```

### 3. 性能监控

```python
from fastorm.performance import PerformanceMonitor

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    with PerformanceMonitor() as monitor:
        response = await call_next(request)
        
        # 记录性能数据
        response.headers["X-DB-Queries"] = str(monitor.query_count)
        response.headers["X-DB-Time"] = str(monitor.db_time)
        
        return response
```

### 4. 批量操作优化

```python
@router.post("/users/bulk-import")
async def bulk_import_users(users_data: List[UserCreate]):
    """批量导入用户（优化版）"""
    from fastorm.query.batch import BatchEngine, BatchContext
    
    batch_engine = BatchEngine()
    
    # 使用上下文管理器优化性能
    async with BatchContext(batch_size=1000) as ctx:
        result = await batch_engine.batch_insert(
            User, 
            [user.dict() for user in users_data],
            context=ctx
        )
    
    return {
        "imported": result["processed_records"],
        "failed": result["failed_records"],
        "time_taken": result["elapsed_time"]
    }
```

## 🔧 环境配置

### .env 文件
```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/dbname
DATABASE_ECHO=false

# FastORM配置
FASTORM_ENABLE_VALIDATION=true
FASTORM_ENABLE_SERIALIZATION=true
FASTORM_ENABLE_BATCH_OPERATIONS=true

# 应用配置
DEBUG=true
SECRET_KEY=your-secret-key-here
```

### requirements.txt
```
fastapi>=0.115.12
uvicorn[standard]>=0.34.0
fastorm>=0.1.0
pydantic>=2.11.0
pydantic-settings>=2.6.0
sqlalchemy[asyncio]>=2.0.40
asyncpg>=0.29.0  # PostgreSQL
python-multipart
```

## FastORM 支持无主键表/视图的最佳实践

对于无主键表/视图，推荐如下声明方式：

```python
class MyView(Model):
    __tablename__ = "my_view"
    col1: Mapped[str]
    col2: Mapped[int]
    col3: Mapped[str]

    __mapper_args__ = {
        "primary_key": [col1, col2]  # 伪主键声明
    }
```
- 只要`col1+col2`能唯一标识一行即可。
- 若未声明主键，FastORM会在模型加载时报错并给出友好提示。

通过这个完整的集成指南，你可以在FastAPI项目中充分利用FastORM的所有功能，包括简洁的模型API、强大的验证系统、高效的序列化和批量操作能力。 