"""
FastORM 项目集成指南

提供多种方式将FastORM集成到您的项目中
"""

import os
import sys
from pathlib import Path


def create_setup_py():
    """创建setup.py用于包安装"""
    
    setup_content = '''
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fastorm",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="FastAPI + SQLAlchemy 2.0 + Pydantic 2.11 的完美融合",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/fastorm",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Framework :: AsyncIO",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "asyncpg>=0.28.0",  # PostgreSQL异步驱动
        "aiosqlite>=0.19.0",  # SQLite异步驱动
    ],
    extras_require={
        "mysql": ["aiomysql>=0.1.1"],
        "postgresql": ["asyncpg>=0.28.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
    include_package_data=True,
    package_data={
        "fastorm": ["py.typed"],
    },
)
'''
    
    with open('setup.py', 'w', encoding='utf-8') as f:
        f.write(setup_content)
    
    print("✅ setup.py 已创建")


def create_project_structure_guide():
    """创建项目结构集成指南"""
    
    guide_content = '''
# FastORM 项目集成指南

## 📦 安装方式

### 方式1：开发模式安装（推荐）
```bash
# 克隆或复制FastORM到您的项目目录
cd your_project/
cp -r /path/to/FastORM/fastorm ./

# 安装依赖
pip install sqlalchemy>=2.0.0 pydantic>=2.0.0 asyncpg aiosqlite
```

### 方式2：pip安装（如果您已打包）
```bash
# 在FastORM目录下执行
pip install -e .

# 或者如果您已发布到PyPI
pip install fastorm
```

## 🏗️ 项目结构集成

### 推荐的项目结构
```
your_project/
├── fastorm/                 # FastORM库（复制整个目录）
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI应用主文件
│   ├── config.py           # 项目配置
│   ├── models/             # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── product.py
│   ├── api/                # API路由
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── products.py
│   └── database.py         # 数据库配置
├── requirements.txt
└── main.py                 # 应用入口
```

## ⚙️ 基本配置示例

### 1. 数据库配置 (app/database.py)
```python
from fastorm.config import set_config
from fastorm.connection.database import DatabaseManager

# 配置FastORM
set_config(
    database_url="sqlite+aiosqlite:///./test.db",  # 开发环境
    # database_url="postgresql+asyncpg://user:pass@localhost/db",  # 生产环境
    debug=True,  # 开发环境
    echo_sql=True,  # 显示SQL语句
)

# 初始化数据库管理器
db_manager = DatabaseManager()

async def init_database():
    """初始化数据库"""
    await db_manager.create_all_tables()

async def close_database():
    """关闭数据库连接"""
    await db_manager.close()
```

### 2. 模型定义 (app/models/user.py)
```python
from fastorm.model.model import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean
from typing import Optional

class User(Model):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    def __repr__(self) -> str:
        return f"<User(name='{self.name}', email='{self.email}')>"
```

### 3. FastAPI集成 (app/main.py)
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_database, close_database
from app.api import users

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_database()
    yield
    # 关闭时清理数据库连接
    await close_database()

app = FastAPI(
    title="Your Project with FastORM",
    description="使用FastORM的FastAPI项目",
    version="1.0.0",
    lifespan=lifespan
)

# 包含API路由
app.include_router(users.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Hello FastORM!"}
```

### 4. API路由 (app/api/users.py)
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

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
    
    class Config:
        from_attributes = True

@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """创建用户"""
    user = await User.create(
        name=user_data.name,
        email=user_data.email,
        age=user_data.age
    )
    return user

@router.get("/", response_model=List[UserResponse])
async def get_users():
    """获取所有用户"""
    users = await User.all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """获取单个用户"""
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_data: UserCreate):
    """更新用户"""
    user = await User.find_or_fail(user_id)
    await user.update(
        name=user_data.name,
        email=user_data.email,
        age=user_data.age
    )
    return user

@router.delete("/{user_id}")
async def delete_user(user_id: int):
    """删除用户"""
    user = await User.find_or_fail(user_id)
    await user.delete()
    return {"message": "User deleted successfully"}
```

### 5. 应用入口 (main.py)
```python
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发环境
        log_level="info"
    )
```

### 6. 依赖文件 (requirements.txt)
```
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
asyncpg>=0.28.0
aiosqlite>=0.19.0
python-multipart>=0.0.6
```

## 🚀 启动应用

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python main.py

# 或者使用uvicorn直接启动
uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看自动生成的API文档！

## 🔧 高级配置

### 生产环境配置
```python
# app/config.py
import os
from fastorm.config import set_config

def configure_production():
    set_config(
        database_url=os.getenv("DATABASE_URL"),
        debug=False,
        echo_sql=False,
        pool_size=20,
        max_overflow=30,
    )

def configure_development():
    set_config(
        database_url="sqlite+aiosqlite:///./dev.db",
        debug=True,
        echo_sql=True,
    )
```

### 数据库迁移（可选）
```python
# scripts/migrate.py
from fastorm.connection.database import DatabaseManager
from app.models import *  # 导入所有模型

async def migrate():
    """创建所有表"""
    db_manager = DatabaseManager()
    await db_manager.create_all_tables()
    print("✅ 数据库迁移完成")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate())
```

## 📝 使用提示

1. **模型定义**：继承 `fastorm.model.model.Model`
2. **查询操作**：使用 `Model.where().get()` 等链式API
3. **关系操作**：使用 `belongs_to`, `has_many` 等关系定义
4. **安全优先**：所有SQL操作已自动防SQL注入
5. **异步优先**：所有数据库操作都是异步的

开始使用FastORM构建您的现代Web应用吧！🚀
'''
    
    with open('PROJECT_INTEGRATION_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print("✅ 项目集成指南已创建: PROJECT_INTEGRATION_GUIDE.md")


def create_quick_start_script():
    """创建快速启动脚本"""
    
    script_content = '''
#!/usr/bin/env python3
"""
FastORM 快速启动脚本

自动创建一个基本的FastAPI + FastORM项目结构
"""

import os
import shutil
from pathlib import Path

def create_basic_project(project_name: str):
    """创建基本项目结构"""
    
    print(f"🚀 创建FastORM项目: {project_name}")
    
    # 创建项目目录
    project_path = Path(project_name)
    project_path.mkdir(exist_ok=True)
    
    # 复制FastORM库
    if Path("fastorm").exists():
        shutil.copytree("fastorm", project_path / "fastorm", dirs_exist_ok=True)
        print("✅ FastORM库已复制")
    else:
        print("❌ 找不到fastorm目录，请确保在FastORM项目根目录下运行此脚本")
        return
    
    # 创建应用目录结构
    app_path = project_path / "app"
    app_path.mkdir(exist_ok=True)
    (app_path / "models").mkdir(exist_ok=True)
    (app_path / "api").mkdir(exist_ok=True)
    
    # 创建基本文件
    files = {
        "app/__init__.py": "",
        "app/models/__init__.py": "",
        "app/api/__init__.py": "",
        "app/database.py": database_py_content(),
        "app/main.py": main_py_content(),
        "app/models/user.py": user_model_content(),
        "app/api/users.py": users_api_content(),
        "main.py": main_entry_content(),
        "requirements.txt": requirements_content(),
        ".env.example": env_example_content(),
    }
    
    for file_path, content in files.items():
        full_path = project_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"✅ 项目 '{project_name}' 创建完成！")
    print(f"📁 项目位置: {project_path.absolute()}")
    print("\\n🚀 下一步:")
    print(f"1. cd {project_name}")
    print("2. pip install -r requirements.txt")
    print("3. python main.py")
    print("4. 访问 http://localhost:8000/docs")

def database_py_content():
    return '''from fastorm.config import set_config
from fastorm.connection.database import DatabaseManager

# 配置FastORM
set_config(
    database_url="sqlite+aiosqlite:///./app.db",
    debug=True,
    echo_sql=True,
)

db_manager = DatabaseManager()

async def init_database():
    await db_manager.create_all_tables()

async def close_database():
    await db_manager.close()
'''

def main_py_content():
    return '''from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_database, close_database
from app.api import users

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield
    await close_database()

app = FastAPI(
    title="FastORM项目",
    description="使用FastORM的FastAPI项目",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(users.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Hello FastORM!", "docs": "/docs"}
'''

def user_model_content():
    return '''from fastorm.model.model import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean
from typing import Optional

class User(Model):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
'''

def users_api_content():
    return '''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

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
    
    class Config:
        from_attributes = True

@router.post("/", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    user = await User.create(**user_data.dict())
    return user

@router.get("/", response_model=List[UserResponse])
async def get_users():
    return await User.all()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = await User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
'''

def main_entry_content():
    return '''import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
'''

def requirements_content():
    return '''fastapi>=0.100.0
uvicorn[standard]>=0.20.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
aiosqlite>=0.19.0
'''

def env_example_content():
    return '''# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./app.db

# 应用配置
DEBUG=True
ECHO_SQL=True
'''

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("使用方法: python quick_start.py <project_name>")
        print("示例: python quick_start.py my_fastorm_app")
        sys.exit(1)
    
    project_name = sys.argv[1]
    create_basic_project(project_name)
'''
    
    with open('quick_start.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print("✅ 快速启动脚本已创建: quick_start.py")


def main():
    """主函数"""
    print("🔧 创建FastORM项目集成文件...")
    print("=" * 50)
    
    create_setup_py()
    create_project_structure_guide()
    create_quick_start_script()
    
    print("\n" + "=" * 50)
    print("✅ 所有集成文件已创建完成！")
    print("\n📚 可用的集成方式:")
    print("1. 📖 查看详细指南: PROJECT_INTEGRATION_GUIDE.md")
    print("2. 🚀 快速创建项目: python quick_start.py <项目名>")
    print("3. 📦 作为包安装: pip install -e .")
    print("\n💡 推荐使用快速启动脚本创建新项目！")


if __name__ == "__main__":
    main() 