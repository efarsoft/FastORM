# 🚀 FastORM 快速集成指南

## 📦 3种集成方式

### 方式1：直接复制（最简单）⭐ **推荐**

```bash
# 1. 复制fastorm目录到你的项目
cp -r fastorm/ your_project/

# 2. 安装依赖
pip install sqlalchemy>=2.0.0 pydantic>=2.0.0 aiosqlite
```

### 方式2：pip安装
```bash
# 在FastORM目录下
pip install -e .
```

### 方式3：Git子模块
```bash
git submodule add https://github.com/your/fastorm.git fastorm
```

## 🏗️ 基本使用示例

### 1. 创建基本项目结构
```
your_project/
├── fastorm/           # 复制的FastORM库
├── app/
│   ├── main.py       # FastAPI应用
│   ├── database.py   # 数据库配置
│   └── models.py     # 数据模型
├── requirements.txt
└── run.py           # 启动文件
```

### 2. 数据库配置 (app/database.py)
```python
from fastorm.config import set_config
from fastorm.connection.database import DatabaseManager

# 配置数据库
set_config(
    database_url="sqlite+aiosqlite:///./app.db",  # SQLite（开发）
    # database_url="postgresql+asyncpg://user:pass@localhost/db",  # PostgreSQL（生产）
    debug=True,
    echo_sql=True,
)

# 数据库管理器
db_manager = DatabaseManager()

async def init_db():
    """初始化数据库"""
    await db_manager.create_all_tables()

async def close_db():
    """关闭数据库"""
    await db_manager.close()
```

### 3. 定义模型 (app/models.py)
```python
from fastorm.model.model import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from typing import Optional

class User(Model):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

### 4. FastAPI应用 (app/main.py)
```python
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional

from .database import init_db, close_db
from .models import User

# 应用生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # 启动时初始化
    yield
    await close_db()  # 关闭时清理

# 创建FastAPI应用
app = FastAPI(
    title="FastORM应用",
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
    
    class Config:
        from_attributes = True

# API路由
@app.get("/")
async def root():
    return {"message": "Hello FastORM!"}

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
    return await User.all()

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
    """删除用户"""
    user = await User.find_or_fail(user_id)
    await user.delete()
    return {"message": "用户删除成功"}
```

### 5. 启动文件 (run.py)
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

### 6. 依赖文件 (requirements.txt)
```
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
aiosqlite>=0.19.0
```

## 🚀 启动应用

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用
python run.py

# 3. 访问应用
# http://localhost:8000        - 首页
# http://localhost:8000/docs   - API文档
# http://localhost:8000/users  - 用户API
```

## 🔧 进阶配置

### 生产环境配置
```python
# 生产环境设置
set_config(
    database_url="postgresql+asyncpg://user:pass@localhost/prod_db",
    debug=False,
    echo_sql=False,
    pool_size=20,
    max_overflow=30,
)
```

### 环境变量配置
```python
import os
from fastorm.config import set_config

set_config(
    database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db"),
    debug=os.getenv("DEBUG", "False").lower() == "true",
)
```

## 💡 核心功能示例

### 查询操作
```python
# 基本查询
users = await User.all()
user = await User.find(1)

# 条件查询
active_users = await User.where('is_active', True).get()
adult_users = await User.where('age', '>=', 18).get()

# 链式查询
result = await User.where('age', '>', 18)\
                  .where('status', 'active')\
                  .order_by('name')\
                  .limit(10)\
                  .get()
```

### CRUD操作
```python
# 创建
user = await User.create(name="张三", email="zhang@example.com")

# 读取
user = await User.find(1)
users = await User.all()

# 更新
await user.update(name="李四")

# 删除（软删除）
await user.delete()

# 硬删除
await user.delete(force=True)
```

## ✅ 验证安装

创建 `test_fastorm.py` 测试文件：
```python
import asyncio
from app.models import User

async def test_fastorm():
    # 创建用户
    user = await User.create(
        name="测试用户",
        email="test@example.com",
        age=25
    )
    print(f"创建用户: {user.name} (ID: {user.id})")
    
    # 查询用户
    all_users = await User.all()
    print(f"总用户数: {len(all_users)}")
    
    # 删除用户
    await user.delete()
    print("用户删除成功")

if __name__ == "__main__":
    asyncio.run(test_fastorm())
```

## 🎯 总结

**1分钟集成FastORM：**
1. 复制 `fastorm/` 目录到项目
2. 安装依赖：`pip install sqlalchemy pydantic aiosqlite`
3. 复制上面的代码示例
4. 运行：`python run.py`
5. 访问：`http://localhost:8000/docs`

🎉 **恭喜！您已成功集成FastORM！**

---

📞 **需要帮助？**
- 查看生产配置：`fastorm_production_config.py`
- 运行测试：`python test_p1_functionality.py`
- 安全检查：`python production_readiness_check.py` 