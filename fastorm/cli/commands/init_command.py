"""
FastORM项目初始化命令

提供快速创建新FastORM项目的功能，生成标准的项目结构和配置文件。
"""

import click
import os
import shutil
from pathlib import Path
from typing import Optional
import subprocess
import sys


@click.command()
@click.argument('project_name')
@click.option('--template', '-t', default='basic', 
              type=click.Choice(['basic', 'api', 'full']),
              help='项目模板类型 (basic/api/full)')
@click.option('--database', '-d', default='sqlite',
              type=click.Choice(['sqlite', 'postgresql', 'mysql']),
              help='数据库类型')
@click.option('--docker', is_flag=True, help='包含Docker配置')
@click.option('--git', is_flag=True, default=True, help='初始化Git仓库')
@click.pass_context
def init(ctx, project_name: str, template: str, database: str, 
         docker: bool, git: bool):
    """
    🚀 初始化新的FastORM项目
    
    创建一个包含完整项目结构、配置文件和示例代码的新项目。
    
    \b
    项目模板:
        basic  - 基础FastORM项目 (推荐入门)
        api    - FastAPI + FastORM API项目
        full   - 完整功能项目 (包含认证、权限等)
    
    \b
    示例:
        fastorm init my-blog              # 基础项目
        fastorm init my-api -t api        # API项目
        fastorm init my-app -t full -d postgresql --docker
    """
    verbose = ctx.obj.get('verbose', False)
    
    # 验证项目名称
    if not _is_valid_project_name(project_name):
        click.echo("❌ 项目名称无效。请使用字母、数字和连字符。", err=True)
        sys.exit(1)
    
    project_path = Path.cwd() / project_name
    
    # 检查目录是否已存在
    if project_path.exists():
        if not click.confirm(f"⚠️ 目录 '{project_name}' 已存在。是否继续？"):
            click.echo("❌ 项目初始化已取消")
            sys.exit(1)
    
    try:
        # 创建项目
        click.echo(f"🚀 正在创建FastORM项目: {project_name}")
        _create_project_structure(project_path, template, database, docker, verbose)
        
        # 初始化Git仓库
        if git:
            _init_git_repo(project_path, verbose)
        
        # 安装依赖
        if click.confirm("📦 是否安装Python依赖？"):
            _install_dependencies(project_path, verbose)
        
        # 显示完成信息
        _show_completion_message(project_name, template, database)
        
    except Exception as e:
        click.echo(f"❌ 项目创建失败: {e}", err=True)
        sys.exit(1)


def _is_valid_project_name(name: str) -> bool:
    """验证项目名称是否有效"""
    import re
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, name)) and len(name) >= 2


def _create_project_structure(project_path: Path, template: str, 
                            database: str, docker: bool, verbose: bool):
    """创建项目目录结构"""
    if verbose:
        click.echo(f"📁 创建项目目录: {project_path}")
    
    # 创建基础目录结构
    directories = [
        'app',
        'app/models',
        'app/api',
        'app/api/v1',
        'app/core',
        'app/db',
        'migrations',
        'tests',
        'scripts',
        'docs'
    ]
    
    # 根据模板添加额外目录
    if template in ['api', 'full']:
        directories.extend([
            'app/services',
            'app/schemas',
            'app/dependencies'
        ])
    
    if template == 'full':
        directories.extend([
            'app/auth',
            'app/middleware',
            'static',
            'templates'
        ])
    
    # 创建目录
    for directory in directories:
        dir_path = project_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        if verbose:
            click.echo(f"  ✓ {directory}/")
    
    # 生成项目文件
    _generate_project_files(project_path, template, database, docker, verbose)


def _generate_project_files(project_path: Path, template: str, 
                           database: str, docker: bool, verbose: bool):
    """生成项目配置文件和代码"""
    
    # pyproject.toml
    pyproject_content = _get_pyproject_template(
        project_path.name, database, template
    )
    _write_file(project_path / 'pyproject.toml', pyproject_content, verbose)
    
    # main.py
    main_content = _get_main_template(template)
    _write_file(project_path / 'app' / 'main.py', main_content, verbose)
    
    # __init__.py files
    init_files = [
        'app/__init__.py',
        'app/models/__init__.py', 
        'app/api/__init__.py',
        'app/api/v1/__init__.py',
        'app/core/__init__.py',
        'app/db/__init__.py',
        'tests/__init__.py'
    ]
    
    for init_file in init_files:
        _write_file(project_path / init_file, '"""Package initialization"""', verbose)
    
    # 数据库配置
    db_config = _get_database_config_template(database)
    _write_file(project_path / 'app' / 'core' / 'database.py', db_config, verbose)
    
    # 基础模型
    base_model = _get_base_model_template()
    _write_file(project_path / 'app' / 'models' / 'base.py', base_model, verbose)
    
    # 示例模型
    user_model = _get_user_model_template(template)
    _write_file(project_path / 'app' / 'models' / 'user.py', user_model, verbose)
    
    # README.md
    readme_content = _get_readme_template(project_path.name, template, database)
    _write_file(project_path / 'README.md', readme_content, verbose)
    
    # .gitignore
    gitignore_content = _get_gitignore_template()
    _write_file(project_path / '.gitignore', gitignore_content, verbose)
    
    # requirements.txt (简化版本)
    requirements_content = _get_requirements_template(database)
    _write_file(project_path / 'requirements.txt', requirements_content, verbose)
    
    if docker:
        # Dockerfile
        dockerfile_content = _get_dockerfile_template()
        _write_file(project_path / 'Dockerfile', dockerfile_content, verbose)
        
        # docker-compose.yml
        docker_compose_content = _get_docker_compose_template(database)
        _write_file(project_path / 'docker-compose.yml', docker_compose_content, verbose)


def _write_file(file_path: Path, content: str, verbose: bool):
    """写入文件内容"""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    if verbose:
        click.echo(f"  ✓ {file_path.name}")


def _init_git_repo(project_path: Path, verbose: bool):
    """初始化Git仓库"""
    if verbose:
        click.echo("🔧 初始化Git仓库...")
    
    try:
        subprocess.run(['git', 'init'], cwd=project_path, 
                      capture_output=True, check=True)
        subprocess.run(['git', 'add', '.'], cwd=project_path,
                      capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit: FastORM project'],
                      cwd=project_path, capture_output=True, check=True)
        if verbose:
            click.echo("  ✓ Git仓库初始化完成")
    except subprocess.CalledProcessError:
        click.echo("⚠️ Git仓库初始化失败 (可能未安装Git)")


def _install_dependencies(project_path: Path, verbose: bool):
    """安装Python依赖"""
    if verbose:
        click.echo("📦 安装Python依赖...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                      cwd=project_path, capture_output=not verbose, check=True)
        if verbose:
            click.echo("  ✓ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        click.echo(f"⚠️ 依赖安装失败: {e}")


def _show_completion_message(project_name: str, template: str, database: str):
    """显示项目创建完成信息"""
    click.echo(f"\n🎉 FastORM项目 '{project_name}' 创建成功！")
    click.echo(f"📋 模板类型: {template}")
    click.echo(f"🗄️  数据库: {database}")
    
    click.echo(f"\n📚 下一步操作:")
    click.echo(f"   cd {project_name}")
    click.echo(f"   fastorm migrate          # 运行数据库迁移")
    click.echo(f"   fastorm serve           # 启动开发服务器")
    
    click.echo(f"\n🔗 有用的命令:")
    click.echo(f"   fastorm create:model Blog    # 创建新模型")
    click.echo(f"   fastorm --help              # 查看所有命令")


# 模板内容生成函数（为了保持代码简洁，只显示关键部分）
def _get_pyproject_template(project_name: str, database: str, template: str) -> str:
    """生成pyproject.toml模板"""
    return f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
description = "FastORM project created with CLI"
dependencies = [
    "fastorm>=1.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    {"'asyncpg>=0.29.0'," if database == 'postgresql' else ""}
    {"'aiomysql>=0.2.0'," if database == 'mysql' else ""}
    {"'aiosqlite>=0.20.0'," if database == 'sqlite' else ""}
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "black>=24.10.0",
    "ruff>=0.8.0",
]
'''


def _get_main_template(template: str) -> str:
    """生成main.py模板"""
    return '''"""
FastORM Application Main Module
"""

from fastapi import FastAPI
from fastorm import Database

# 创建FastAPI应用
app = FastAPI(
    title="FastORM Application",
    description="Generated by FastORM CLI",
    version="0.1.0"
)

# 数据库配置
database = Database("sqlite:///./app.db")

@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    await database.connect()

@app.on_event("shutdown") 
async def shutdown():
    """应用关闭时断开数据库连接"""
    await database.disconnect()

@app.get("/")
async def root():
    """根路径"""
    return {"message": "FastORM Application is running!"}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
'''


def _get_database_config_template(database: str) -> str:
    """生成数据库配置模板"""
    return f'''"""
Database configuration for {database}
"""

from fastorm import Database
import os

# 数据库URL配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "{_get_database_url(database)}"
)

# 创建数据库实例
database = Database(DATABASE_URL)
'''


def _get_database_url(database: str) -> str:
    """获取数据库URL"""
    urls = {
        'sqlite': 'sqlite:///./app.db',
        'postgresql': 'postgresql+asyncpg://user:password@localhost/dbname',
        'mysql': 'mysql+aiomysql://user:password@localhost/dbname'
    }
    return urls.get(database, urls['sqlite'])


def _get_base_model_template() -> str:
    """生成基础模型模板"""
    return '''"""
Base model for all application models
"""

from fastorm import BaseModel
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime


class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppBaseModel(BaseModel, TimestampMixin):
    """应用基础模型"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
'''


def _get_user_model_template(template: str) -> str:
    """生成用户模型模板"""
    return '''"""
User model example
"""

from sqlalchemy import Column, String, Boolean
from .base import AppBaseModel


class User(AppBaseModel):
    """用户模型"""
    __tablename__ = "users"
    
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
'''


def _get_readme_template(project_name: str, template: str, database: str) -> str:
    """生成README.md模板"""
    return f'''# {project_name}

FastORM项目，使用FastORM CLI生成。

## 项目信息

- **模板类型**: {template}
- **数据库**: {database}
- **框架**: FastAPI + FastORM

## 快速开始

1. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

2. 运行数据库迁移:
   ```bash
   fastorm migrate
   ```

3. 启动开发服务器:
   ```bash
   fastorm serve
   # 或者
   uvicorn app.main:app --reload
   ```

## 开发命令

- `fastorm create:model ModelName` - 创建新模型
- `fastorm migrate` - 运行数据库迁移
- `fastorm --help` - 查看所有可用命令

## 项目结构

```
{project_name}/
├── app/
│   ├── main.py         # FastAPI应用入口
│   ├── models/         # 数据模型
│   ├── api/           # API路由
│   └── core/          # 核心配置
├── migrations/         # 数据库迁移文件
├── tests/             # 测试文件
└── docs/              # 文档
```

## 技术栈

- [FastORM](https://fastorm.dev) - 现代Python ORM
- [FastAPI](https://fastapi.tiangolo.com) - 高性能Web框架
- [SQLAlchemy 2.0](https://sqlalchemy.org) - SQL工具包
- [Pydantic](https://pydantic-docs.helpmanual.io) - 数据验证
'''


def _get_gitignore_template() -> str:
    """生成.gitignore模板"""
    return '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite3

# Logs
*.log
logs/

# Environment variables
.env
.env.local

# OS
.DS_Store
Thumbs.db
'''


def _get_requirements_template(database: str) -> str:
    """生成requirements.txt模板"""
    base_deps = [
        "fastorm>=1.0.0",
        "fastapi>=0.115.0", 
        "uvicorn[standard]>=0.34.0"
    ]
    
    if database == 'postgresql':
        base_deps.append("asyncpg>=0.29.0")
    elif database == 'mysql':
        base_deps.append("aiomysql>=0.2.0")
    else:  # sqlite
        base_deps.append("aiosqlite>=0.20.0")
    
    return '\n'.join(base_deps) + '\n'


def _get_dockerfile_template() -> str:
    """生成Dockerfile模板"""
    return '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''


def _get_docker_compose_template(database: str) -> str:
    """生成docker-compose.yml模板"""
    if database == 'postgresql':
        return '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@db:5432/fastorm_db
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: fastorm_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
'''
    elif database == 'mysql':
        return '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+aiomysql://user:password@db:3306/fastorm_db
    depends_on:
      - db

  db:
    image: mysql:8.0
    environment:
      MYSQL_USER: user
      MYSQL_PASSWORD: password
      MYSQL_DATABASE: fastorm_db
      MYSQL_ROOT_PASSWORD: rootpassword
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

volumes:
  mysql_data:
'''
    else:  # sqlite
        return '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./app.db:/app/app.db
''' 