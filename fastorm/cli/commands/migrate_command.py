"""
FastORM数据库迁移命令

管理数据库迁移文件的生成、执行和版本控制。
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click


@click.command()
@click.option("--message", "-m", help="迁移描述信息")
@click.option("--auto", is_flag=True, help="自动检测模型变更")
@click.option("--upgrade", is_flag=True, help="执行迁移到最新版本")
@click.option("--downgrade", help="回滚到指定版本")
@click.option("--history", is_flag=True, help="显示迁移历史")
@click.option("--current", is_flag=True, help="显示当前版本")
@click.pass_context
def migrate(
    ctx,
    message: str,
    auto: bool,
    upgrade: bool,
    downgrade: str,
    history: bool,
    current: bool,
):
    """
    🗄️ 数据库迁移管理

    生成和执行数据库迁移文件，管理数据库schema版本。

    \b
    常用操作:
        fastorm migrate --auto -m "添加用户表"    # 自动生成迁移
        fastorm migrate --upgrade                # 执行所有待执行迁移
        fastorm migrate --downgrade base         # 回滚到初始状态
        fastorm migrate --history                # 查看迁移历史
        fastorm migrate --current                # 查看当前版本

    \b
    前提条件:
        - 已安装 alembic
        - 存在 alembic.ini 配置文件
        - 数据库连接配置正确
    """
    verbose = ctx.obj.get("verbose", False)

    # 检查Alembic配置
    if not _check_alembic_setup():
        click.echo("❌ Alembic未配置，正在初始化...")
        if not _init_alembic(verbose):
            sys.exit(1)

    try:
        if history:
            _show_migration_history(verbose)
        elif current:
            _show_current_version(verbose)
        elif auto:
            _generate_auto_migration(message, verbose)
        elif upgrade:
            _upgrade_database(verbose)
        elif downgrade:
            _downgrade_database(downgrade, verbose)
        else:
            # 默认行为：生成迁移并询问是否执行
            if auto or click.confirm("🔍 是否自动检测模型变更并生成迁移？"):
                _generate_auto_migration(message, verbose)

                if click.confirm("⬆️ 是否立即执行迁移？"):
                    _upgrade_database(verbose)

    except Exception as e:
        click.echo(f"❌ 迁移操作失败: {e}", err=True)
        sys.exit(1)


def _check_alembic_setup() -> bool:
    """检查Alembic是否已配置"""
    return (
        Path("alembic.ini").exists()
        and Path("migrations").exists()
        and Path("migrations/env.py").exists()
    )


def _init_alembic(verbose: bool) -> bool:
    """初始化Alembic配置"""
    if verbose:
        click.echo("🔧 初始化Alembic配置...")

    try:
        # 初始化alembic
        subprocess.run(
            ["alembic", "init", "migrations"], capture_output=not verbose, check=True
        )

        # 创建配置文件
        _create_alembic_config()
        _create_env_py()

        if verbose:
            click.echo("  ✓ Alembic配置完成")
        return True

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Alembic初始化失败: {e}")
        return False
    except FileNotFoundError:
        click.echo("❌ 未找到alembic命令，请安装: pip install alembic")
        return False


def _create_alembic_config():
    """创建alembic.ini配置文件"""
    config_content = """# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
timezone =

# max length of characters to apply to the
# "slug" field
truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
sourceless = false

# version number format
version_num_format = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

    with open("alembic.ini", "w", encoding="utf-8") as f:
        f.write(config_content)


def _create_env_py():
    """创建migrations/env.py文件"""
    env_content = '''from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入模型
try:
    from app.models.base import AppBaseModel
    target_metadata = AppBaseModel.metadata
except ImportError:
    # 如果导入失败，使用None
    target_metadata = None

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 从环境变量获取数据库URL
database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)
else:
    # 默认SQLite配置
    config.set_main_option('sqlalchemy.url', 'sqlite:///./app.db')

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''

    env_file = Path("migrations/env.py")
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)


def _generate_auto_migration(message: str, verbose: bool):
    """生成自动迁移文件"""
    if not message:
        message = f"Auto migration {datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if verbose:
        click.echo(f"📝 生成迁移文件: {message}")

    try:
        cmd = ["alembic", "revision", "--autogenerate", "-m", message]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if verbose:
            click.echo(result.stdout)

        # 解析输出获取版本号
        for line in result.stdout.split("\n"):
            if "Generating" in line and "revision ID" in line:
                click.echo(f"✅ {line.strip()}")
                break
        else:
            click.echo("✅ 迁移文件生成完成")

    except subprocess.CalledProcessError as e:
        raise Exception(f"生成迁移失败: {e.stderr}")


def _upgrade_database(verbose: bool):
    """升级数据库到最新版本"""
    if verbose:
        click.echo("⬆️ 执行数据库迁移...")

    try:
        cmd = ["alembic", "upgrade", "head"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if verbose:
            click.echo(result.stdout)

        click.echo("✅ 数据库迁移完成")

    except subprocess.CalledProcessError as e:
        raise Exception(f"数据库迁移失败: {e.stderr}")


def _downgrade_database(target: str, verbose: bool):
    """降级数据库到指定版本"""
    if verbose:
        click.echo(f"⬇️ 回滚数据库到版本: {target}")

    try:
        cmd = ["alembic", "downgrade", target]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if verbose:
            click.echo(result.stdout)

        click.echo(f"✅ 数据库回滚到 {target} 完成")

    except subprocess.CalledProcessError as e:
        raise Exception(f"数据库回滚失败: {e.stderr}")


def _show_migration_history(verbose: bool):
    """显示迁移历史"""
    try:
        cmd = ["alembic", "history", "--verbose" if verbose else ""]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        click.echo("📜 迁移历史:")
        click.echo(result.stdout)

    except subprocess.CalledProcessError as e:
        raise Exception(f"获取迁移历史失败: {e.stderr}")


def _show_current_version(verbose: bool):
    """显示当前数据库版本"""
    try:
        cmd = ["alembic", "current", "--verbose" if verbose else ""]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        click.echo("🔍 当前数据库版本:")
        click.echo(result.stdout or "数据库尚未初始化")

    except subprocess.CalledProcessError as e:
        raise Exception(f"获取当前版本失败: {e.stderr}")
