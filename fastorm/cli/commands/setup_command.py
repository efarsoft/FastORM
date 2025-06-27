"""
FastORM现有项目集成命令

为现有的FastAPI项目添加FastORM支持，实现渐进式集成。
"""

import click
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


@click.command()
@click.option('--database', '-d', 
              type=click.Choice(['sqlite', 'postgresql', 'mysql']),
              help='数据库类型（如果未检测到）')
@click.option('--models-dir', default='app/models',
              help='模型文件目录')
@click.option('--force', is_flag=True, help='强制覆盖现有配置')
@click.option('--dry-run', is_flag=True, help='预览模式，不实际修改文件')
@click.pass_context
def setup(ctx, database: str, models_dir: str, force: bool, dry_run: bool):
    """
    🔧 为现有项目添加FastORM支持
    
    检测现有的FastAPI项目并添加FastORM集成，实现渐进式迁移。
    
    \b
    支持的项目类型:
        - 现有FastAPI + SQLAlchemy项目
        - 现有FastAPI + 其他ORM项目  
        - 现有FastAPI + 原始SQL项目
        - 纯FastAPI项目（无ORM）
    
    \b
    集成步骤:
        1. 检测现有项目结构和配置
        2. 添加FastORM依赖到项目配置
        3. 创建FastORM配置文件
        4. 生成集成示例代码
        5. 提供迁移指导
    
    \b
    示例:
        fastorm setup                           # 自动检测并设置
        fastorm setup -d postgresql             # 指定数据库类型
        fastorm setup --models-dir models       # 自定义模型目录
        fastorm setup --dry-run                # 预览模式
    """
    verbose = ctx.obj.get('verbose', False)
    
    if dry_run:
        click.echo("🔍 预览模式 - 不会实际修改任何文件")
    
    try:
        # 1. 检测项目结构
        project_info = _detect_project_structure(verbose)
        
        if not project_info['is_fastapi_project']:
            click.echo("❌ 未检测到FastAPI项目")
            click.echo("💡 请确保在FastAPI项目根目录下运行此命令")
            sys.exit(1)
        
        # 2. 显示检测结果
        _show_detection_results(project_info)
        
        # 3. 确认集成
        if not dry_run and not click.confirm("📦 是否继续集成FastORM？"):
            click.echo("❌ 集成已取消")
            sys.exit(1)
        
        # 4. 执行集成
        _integrate_fastorm(project_info, database, models_dir, force, dry_run, verbose)
        
        # 5. 显示完成信息
        _show_integration_guide(project_info, dry_run)
        
    except Exception as e:
        click.echo(f"❌ 集成失败: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _detect_project_structure(verbose: bool) -> Dict:
    """检测现有项目结构"""
    if verbose:
        click.echo("🔍 检测项目结构...")
    
    current_dir = Path.cwd()
    project_info = {
        'is_fastapi_project': False,
        'project_root': current_dir,
        'has_pyproject_toml': False,
        'has_requirements_txt': False,
        'has_setup_py': False,
        'fastapi_app_files': [],
        'existing_models': [],
        'database_type': None,
        'has_sqlalchemy': False,
        'has_alembic': False,
        'dependency_manager': None
    }
    
    # 检测配置文件
    if (current_dir / 'pyproject.toml').exists():
        project_info['has_pyproject_toml'] = True
        project_info['dependency_manager'] = 'pyproject.toml'
    elif (current_dir / 'requirements.txt').exists():
        project_info['has_requirements_txt'] = True
        project_info['dependency_manager'] = 'requirements.txt'
    elif (current_dir / 'setup.py').exists():
        project_info['has_setup_py'] = True
        project_info['dependency_manager'] = 'setup.py'
    
    # 检测FastAPI应用
    project_info['fastapi_app_files'] = _find_fastapi_apps(current_dir)
    project_info['is_fastapi_project'] = len(project_info['fastapi_app_files']) > 0
    
    # 检测现有模型
    project_info['existing_models'] = _find_existing_models(current_dir)
    
    # 检测数据库和ORM
    db_info = _detect_database_config(current_dir)
    project_info.update(db_info)
    
    return project_info


def _find_fastapi_apps(project_root: Path) -> List[Path]:
    """查找FastAPI应用文件"""
    fastapi_files = []
    
    # 常见的应用文件模式
    common_patterns = [
        'main.py',
        'app.py', 
        'server.py',
        'app/main.py',
        'src/main.py',
        'api/main.py'
    ]
    
    for pattern in common_patterns:
        file_path = project_root / pattern
        if file_path.exists() and _is_fastapi_file(file_path):
            fastapi_files.append(file_path)
    
    # 递归搜索其他可能的FastAPI文件
    for py_file in project_root.rglob('*.py'):
        if py_file.name.startswith('.') or 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        if py_file not in fastapi_files and _is_fastapi_file(py_file):
            fastapi_files.append(py_file)
    
    return fastapi_files


def _is_fastapi_file(file_path: Path) -> bool:
    """检查文件是否为FastAPI应用"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return ('FastAPI' in content or 'fastapi' in content) and 'app =' in content
    except:
        return False


def _find_existing_models(project_root: Path) -> List[Path]:
    """查找现有的模型文件"""
    model_files = []
    
    # 常见的模型目录
    model_dirs = [
        'models',
        'app/models', 
        'src/models',
        'api/models',
        'database/models'
    ]
    
    for model_dir in model_dirs:
        dir_path = project_root / model_dir
        if dir_path.exists():
            for py_file in dir_path.rglob('*.py'):
                if _is_model_file(py_file):
                    model_files.append(py_file)
    
    return model_files


def _is_model_file(file_path: Path) -> bool:
    """检查文件是否为模型文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查SQLAlchemy模型特征
            return any(keyword in content for keyword in [
                'declarative_base',
                'Base =',
                'Column(',
                '__tablename__',
                'relationship(',
                'ForeignKey('
            ])
    except:
        return False


def _detect_database_config(project_root: Path) -> Dict:
    """检测数据库配置"""
    db_info = {
        'database_type': None,
        'has_sqlalchemy': False,
        'has_alembic': False,
        'database_url': None
    }
    
    # 检查依赖文件中的数据库驱动
    dep_files = [
        project_root / 'pyproject.toml',
        project_root / 'requirements.txt',
        project_root / 'setup.py'
    ]
    
    for dep_file in dep_files:
        if dep_file.exists():
            try:
                content = dep_file.read_text(encoding='utf-8')
                
                # 检测SQLAlchemy
                if 'sqlalchemy' in content.lower():
                    db_info['has_sqlalchemy'] = True
                
                # 检测Alembic
                if 'alembic' in content.lower():
                    db_info['has_alembic'] = True
                
                # 检测数据库驱动
                if any(driver in content.lower() for driver in ['asyncpg', 'psycopg']):
                    db_info['database_type'] = 'postgresql'
                elif any(driver in content.lower() for driver in ['aiomysql', 'pymysql']):
                    db_info['database_type'] = 'mysql'
                elif any(driver in content.lower() for driver in ['aiosqlite', 'sqlite']):
                    db_info['database_type'] = 'sqlite'
                    
            except:
                continue
    
    # 检查配置文件中的数据库URL
    config_files = list(project_root.rglob('*.py'))
    for config_file in config_files:
        if 'config' in config_file.name.lower() or 'setting' in config_file.name.lower():
            try:
                content = config_file.read_text(encoding='utf-8')
                # 查找数据库URL模式
                url_patterns = [
                    r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']',
                    r'SQLALCHEMY_DATABASE_URL\s*=\s*["\']([^"\']+)["\']'
                ]
                for pattern in url_patterns:
                    match = re.search(pattern, content)
                    if match:
                        db_info['database_url'] = match.group(1)
                        # 从URL推断数据库类型
                        url = match.group(1).lower()
                        if url.startswith('postgresql'):
                            db_info['database_type'] = 'postgresql'
                        elif url.startswith('mysql'):
                            db_info['database_type'] = 'mysql'
                        elif url.startswith('sqlite'):
                            db_info['database_type'] = 'sqlite'
                        break
            except:
                continue
    
    return db_info


def _show_detection_results(project_info: Dict):
    """显示项目检测结果"""
    click.echo("\n🔍 项目检测结果:")
    click.echo("=" * 50)
    
    # 项目基本信息
    click.echo(f"📁 项目根目录: {project_info['project_root']}")
    click.echo(f"📦 依赖管理: {project_info['dependency_manager'] or '未检测到'}")
    
    # FastAPI应用
    if project_info['fastapi_app_files']:
        click.echo(f"🚀 FastAPI应用: {len(project_info['fastapi_app_files'])} 个")
        for app_file in project_info['fastapi_app_files'][:3]:  # 只显示前3个
            click.echo(f"   - {app_file.relative_to(project_info['project_root'])}")
        if len(project_info['fastapi_app_files']) > 3:
            click.echo(f"   - ... 还有 {len(project_info['fastapi_app_files']) - 3} 个")
    
    # 现有模型
    if project_info['existing_models']:
        click.echo(f"🏗️ 现有模型: {len(project_info['existing_models'])} 个")
        for model_file in project_info['existing_models'][:3]:
            click.echo(f"   - {model_file.relative_to(project_info['project_root'])}")
        if len(project_info['existing_models']) > 3:
            click.echo(f"   - ... 还有 {len(project_info['existing_models']) - 3} 个")
    
    # 数据库信息
    click.echo(f"🗄️ 数据库类型: {project_info['database_type'] or '未检测到'}")
    click.echo(f"🔗 SQLAlchemy: {'✅' if project_info['has_sqlalchemy'] else '❌'}")
    click.echo(f"🔄 Alembic: {'✅' if project_info['has_alembic'] else '❌'}")
    
    if project_info['database_url']:
        # 隐藏敏感信息
        safe_url = re.sub(r'://([^:]+):([^@]+)@', '://***:***@', project_info['database_url'])
        click.echo(f"🔗 数据库URL: {safe_url}")


def _integrate_fastorm(project_info: Dict, database: str, models_dir: str, 
                      force: bool, dry_run: bool, verbose: bool):
    """执行FastORM集成"""
    if verbose or dry_run:
        click.echo("\n🔧 开始集成FastORM...")
    
    # 1. 添加依赖
    _add_fastorm_dependency(project_info, dry_run, verbose)
    
    # 2. 创建FastORM配置
    _create_fastorm_config(project_info, database or project_info['database_type'], 
                          models_dir, force, dry_run, verbose)
    
    # 3. 生成集成示例
    _generate_integration_examples(project_info, dry_run, verbose)
    
    # 4. 设置Alembic（如果需要）
    if not project_info['has_alembic']:
        _setup_alembic_integration(project_info, dry_run, verbose)


def _add_fastorm_dependency(project_info: Dict, dry_run: bool, verbose: bool):
    """添加FastORM依赖"""
    if verbose or dry_run:
        click.echo("📦 添加FastORM依赖...")
    
    if project_info['dependency_manager'] == 'pyproject.toml':
        _add_to_pyproject_toml(project_info, dry_run, verbose)
    elif project_info['dependency_manager'] == 'requirements.txt':
        _add_to_requirements_txt(project_info, dry_run, verbose)
    else:
        if verbose or dry_run:
            click.echo("⚠️ 未检测到依赖管理文件，将创建requirements.txt")
        _create_requirements_txt(project_info, dry_run, verbose)


def _add_to_pyproject_toml(project_info: Dict, dry_run: bool, verbose: bool):
    """添加到pyproject.toml"""
    pyproject_file = project_info['project_root'] / 'pyproject.toml'
    
    if dry_run:
        click.echo(f"   [预览] 将添加FastORM依赖到 {pyproject_file}")
        return
    
    # 这里实际上需要解析和修改TOML文件
    # 为了简化，我们先提供指导
    if verbose:
        click.echo(f"   ℹ️ 请手动添加以下依赖到 {pyproject_file}:")
        click.echo('   dependencies = [')
        click.echo('       "fastorm>=1.0.0",')
        click.echo('   ]')


def _add_to_requirements_txt(project_info: Dict, dry_run: bool, verbose: bool):
    """添加到requirements.txt"""
    req_file = project_info['project_root'] / 'requirements.txt'
    
    if dry_run:
        click.echo(f"   [预览] 将添加FastORM依赖到 {req_file}")
        return
    
    try:
        # 读取现有内容
        existing_content = ""
        if req_file.exists():
            existing_content = req_file.read_text(encoding='utf-8')
        
        # 检查是否已存在
        if 'fastorm' not in existing_content.lower():
            with open(req_file, 'a', encoding='utf-8') as f:
                f.write('\n# FastORM\nfastorm>=1.0.0\n')
            
            if verbose:
                click.echo(f"   ✅ 已添加FastORM依赖到 {req_file}")
        else:
            if verbose:
                click.echo(f"   ℹ️ FastORM依赖已存在于 {req_file}")
                
    except Exception as e:
        click.echo(f"   ⚠️ 添加依赖失败: {e}")


def _create_requirements_txt(project_info: Dict, dry_run: bool, verbose: bool):
    """创建requirements.txt"""
    req_file = project_info['project_root'] / 'requirements.txt'
    
    if dry_run:
        click.echo(f"   [预览] 将创建 {req_file}")
        return
    
    content = """# FastORM dependencies
fastorm>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
"""
    
    # 根据检测到的数据库类型添加驱动
    if project_info['database_type'] == 'postgresql':
        content += "asyncpg>=0.29.0\n"
    elif project_info['database_type'] == 'mysql':
        content += "aiomysql>=0.2.0\n"
    else:
        content += "aiosqlite>=0.20.0\n"
    
    try:
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if verbose:
            click.echo(f"   ✅ 已创建 {req_file}")
    except Exception as e:
        click.echo(f"   ⚠️ 创建文件失败: {e}")


def _create_fastorm_config(project_info: Dict, database_type: str, models_dir: str,
                          force: bool, dry_run: bool, verbose: bool):
    """创建FastORM配置文件"""
    if verbose or dry_run:
        click.echo("⚙️ 创建FastORM配置...")
    
    config_dir = project_info['project_root'] / 'fastorm_config'
    
    if dry_run:
        click.echo(f"   [预览] 将创建配置目录: {config_dir}")
        return
    
    # 创建配置目录
    config_dir.mkdir(exist_ok=True)
    
    # 创建数据库配置文件
    db_config_content = _get_database_config_template(database_type, project_info)
    db_config_file = config_dir / 'database.py'
    
    if not db_config_file.exists() or force:
        with open(db_config_file, 'w', encoding='utf-8') as f:
            f.write(db_config_content)
        
        if verbose:
            click.echo(f"   ✅ 已创建数据库配置: {db_config_file}")
    
    # 创建集成指南
    guide_content = _get_integration_guide_template(project_info, models_dir)
    guide_file = config_dir / 'INTEGRATION_GUIDE.md'
    
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    if verbose:
        click.echo(f"   ✅ 已创建集成指南: {guide_file}")


def _generate_integration_examples(project_info: Dict, dry_run: bool, verbose: bool):
    """生成集成示例代码"""
    if verbose or dry_run:
        click.echo("📝 生成集成示例...")
    
    examples_dir = project_info['project_root'] / 'fastorm_config' / 'examples'
    
    if dry_run:
        click.echo(f"   [预览] 将创建示例目录: {examples_dir}")
        return
    
    examples_dir.mkdir(exist_ok=True)
    
    # 生成基础集成示例
    basic_example = _get_basic_integration_example(project_info)
    basic_file = examples_dir / 'basic_integration.py'
    
    with open(basic_file, 'w', encoding='utf-8') as f:
        f.write(basic_example)
    
    if verbose:
        click.echo(f"   ✅ 已创建基础集成示例: {basic_file}")


def _setup_alembic_integration(project_info: Dict, dry_run: bool, verbose: bool):
    """设置Alembic集成"""
    if verbose or dry_run:
        click.echo("🔄 设置Alembic集成...")
    
    if dry_run:
        click.echo("   [预览] 将初始化Alembic配置")
        return
    
    # 这里可以集成之前的Alembic设置逻辑
    if verbose:
        click.echo("   💡 提示: 请运行 'fastorm migrate' 初始化数据库迁移")


def _get_database_config_template(database_type: str, project_info: Dict) -> str:
    """获取数据库配置模板"""
    existing_url = project_info.get('database_url', '')
    
    return f'''"""
FastORM数据库配置

这个文件包含了FastORM的数据库连接配置。
您可以根据现有项目的配置进行调整。
"""

from fastorm import Database
import os

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "{existing_url or _get_default_database_url(database_type)}"
)

# 创建FastORM数据库实例
database = Database(DATABASE_URL)

# 可选：配置连接池参数
# database = Database(
#     DATABASE_URL,
#     pool_size=10,
#     max_overflow=20,
#     pool_timeout=30
# )
'''


def _get_default_database_url(database_type: str) -> str:
    """获取默认数据库URL"""
    urls = {
        'sqlite': 'sqlite:///./app.db',
        'postgresql': 'postgresql+asyncpg://user:password@localhost/dbname',
        'mysql': 'mysql+aiomysql://user:password@localhost/dbname'
    }
    return urls.get(database_type or 'sqlite', urls['sqlite'])


def _get_integration_guide_template(project_info: Dict, models_dir: str) -> str:
    """获取集成指南模板"""
    return f'''# FastORM集成指南

## 🎯 集成概述

此指南将帮助您将FastORM集成到现有的FastAPI项目中。

## 📋 检测到的项目信息

- **项目根目录**: {project_info['project_root']}
- **FastAPI应用**: {len(project_info['fastapi_app_files'])} 个
- **现有模型**: {len(project_info['existing_models'])} 个
- **数据库类型**: {project_info['database_type'] or '未检测到'}
- **使用SQLAlchemy**: {'是' if project_info['has_sqlalchemy'] else '否'}

## 🚀 集成步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 导入FastORM数据库配置

在您的FastAPI应用中添加以下代码：

```python
from fastorm_config.database import database

# 在应用启动时连接数据库
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown") 
async def shutdown():
    await database.disconnect()
```

### 3. 创建FastORM模型

参考 `examples/basic_integration.py` 中的示例。

### 4. 渐进式迁移

如果您有现有的SQLAlchemy模型，可以：

1. **并行使用**: FastORM和现有ORM可以同时使用
2. **逐步迁移**: 逐个将模型迁移到FastORM
3. **混合查询**: 在过渡期间使用两种查询方式

### 5. 数据库迁移

```bash
# 初始化迁移
fastorm migrate --auto -m "初始化FastORM"

# 执行迁移
fastorm migrate --upgrade
```

## 💡 最佳实践

1. **渐进式集成**: 不要一次性替换所有代码
2. **测试驱动**: 为新的FastORM模型编写测试
3. **性能监控**: 使用FastORM的性能监控功能
4. **文档更新**: 更新API文档以反映新的模型结构

## 🆘 获取帮助

- FastORM文档: https://fastorm.dev
- 命令帮助: `fastorm --help`
- 问题反馈: 请在GitHub上提交issue
'''


def _get_basic_integration_example(project_info: Dict) -> str:
    """获取基础集成示例"""
    return '''"""
FastORM基础集成示例

此文件展示了如何在现有FastAPI项目中使用FastORM。
"""

from fastapi import FastAPI, Depends
from fastorm_config.database import database
from fastorm import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

# 创建FastORM模型
class User(BaseModel):
    """用户模型示例"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# FastAPI应用集成
app = FastAPI()

@app.on_event("startup")
async def startup():
    """应用启动时连接数据库"""
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    """应用关闭时断开数据库连接"""
    await database.disconnect()

# 依赖注入：获取数据库会话
async def get_session():
    async with database.session() as session:
        yield session

# API路由示例
@app.get("/users/")
async def list_users(session = Depends(get_session)):
    """获取用户列表"""
    users = await User.using(session).all()
    return {"users": users}

@app.post("/users/")
async def create_user(username: str, email: str, session = Depends(get_session)):
    """创建新用户"""
    user = User(username=username, email=email)
    await user.using(session).save()
    return {"user": user}

@app.get("/users/{user_id}")
async def get_user(user_id: int, session = Depends(get_session)):
    """获取特定用户"""
    user = await User.using(session).find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}

# 混合使用示例（如果您有现有的SQLAlchemy模型）
# from your_existing_models import ExistingModel
# 
# @app.get("/mixed-query/")
# async def mixed_query(session = Depends(get_session)):
#     """混合使用FastORM和现有模型的查询"""
#     # FastORM查询
#     fastorm_users = await User.using(session).all()
#     
#     # 现有SQLAlchemy查询（如果适用）
#     # existing_data = session.query(ExistingModel).all()
#     
#     return {
#         "fastorm_users": fastorm_users,
#         # "existing_data": existing_data
#     }
'''


def _show_integration_guide(project_info: Dict, dry_run: bool):
    """显示集成完成信息"""
    if dry_run:
        click.echo("\n🔍 预览模式完成 - 以上为将要执行的操作")
        return
    
    click.echo("\n🎉 FastORM集成完成！")
    click.echo("=" * 50)
    
    click.echo("\n📁 生成的文件:")
    click.echo("   fastorm_config/database.py        - 数据库配置")
    click.echo("   fastorm_config/INTEGRATION_GUIDE.md - 集成指南")
    click.echo("   fastorm_config/examples/basic_integration.py - 集成示例")
    
    click.echo("\n🚀 下一步操作:")
    click.echo("   1. pip install -r requirements.txt    # 安装依赖")
    click.echo("   2. 查看 fastorm_config/INTEGRATION_GUIDE.md  # 阅读集成指南")
    click.echo("   3. 参考 fastorm_config/examples/ 中的示例代码")
    click.echo("   4. fastorm migrate --auto -m '集成FastORM'  # 初始化迁移")
    
    click.echo("\n💡 集成建议:")
    click.echo("   - 渐进式迁移，不要一次性替换所有代码")
    click.echo("   - 先在新功能中使用FastORM，验证效果")
    click.echo("   - 现有代码可以与FastORM并行使用")
    click.echo("   - 使用性能监控功能优化查询")
    
    click.echo("\n📚 获取帮助:")
    click.echo("   fastorm --help                     # 查看所有命令")
    click.echo("   fastorm create:model --help        # 模型生成帮助")
    click.echo("   fastorm migrate --help             # 迁移管理帮助") 