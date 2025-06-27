"""
🛠️ FastORM CLI - 现代化开发工具集

专为FastORM设计的命令行界面，提供项目初始化、代码生成、
数据库管理等开发者友好的功能。

Usage:
    fastorm --help              # 查看帮助
    fastorm init my-project     # 初始化新项目
    fastorm create:model User   # 生成模型代码
    fastorm migrate             # 运行数据库迁移
"""

import click
import sys

from .commands import (
    init,
    create_model,
    migrate,
    db,
    serve,
    setup,
    convert
)


# CLI版本信息
__version__ = "1.0.0"


@click.group()
@click.version_option(version=__version__, prog_name="FastORM CLI")
@click.option('--verbose', '-v', is_flag=True, help='启用详细输出')
@click.option('--quiet', '-q', is_flag=True, help='静默模式')
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool):
    """
    🚀 FastORM CLI - 现代化Python ORM开发工具
    
    FastORM = FastAPI + SQLAlchemy 2.0 + Pydantic 2.11 的完美融合
    
    \b
    常用命令:
        fastorm init <project>      创建新的FastORM项目
        fastorm create:model <name> 生成模型代码
        fastorm migrate             运行数据库迁移
        fastorm serve               启动开发服务器
    
    \b
    获取帮助:
        fastorm <command> --help    查看特定命令的帮助
    """
    # 确保上下文对象存在
    ctx.ensure_object(dict)
    
    # 设置全局配置
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    # 配置日志级别
    if verbose and not quiet:
        click.echo(f"🔧 FastORM CLI v{__version__} - 详细模式")


# 注册命令组
cli.add_command(init)
cli.add_command(create_model, name='create:model')
cli.add_command(migrate)
cli.add_command(db)
cli.add_command(serve)
cli.add_command(setup)
cli.add_command(convert)


def main():
    """CLI主入口函数"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n❌ 操作被用户中断", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ CLI执行错误: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main() 