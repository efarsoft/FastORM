"""
FastORM开发服务器命令

启动开发服务器，提供热重载等开发功能。
"""

import os
import subprocess
import sys
from pathlib import Path

import click


@click.command()
@click.option("--host", default="127.0.0.1", help="服务器地址")
@click.option("--port", default=8000, help="服务器端口")
@click.option("--reload", is_flag=True, default=True, help="启用热重载")
@click.option("--app", default="app.main:app", help="FastAPI应用路径")
@click.option("--workers", type=int, help="工作进程数量（生产环境）")
@click.pass_context
def serve(ctx, host: str, port: int, reload: bool, app: str, workers: int):
    """
    🚀 启动开发服务器

    使用uvicorn启动FastAPI开发服务器，支持热重载。

    \b
    示例:
        fastorm serve                           # 默认配置启动
        fastorm serve --host 0.0.0.0 --port 8080  # 自定义地址端口
        fastorm serve --app myapp.main:app      # 自定义应用路径
        fastorm serve --workers 4              # 多进程模式
    """
    verbose = ctx.obj.get("verbose", False)

    # 检查应用文件是否存在
    app_file = _parse_app_file(app)
    if not _check_app_exists(app_file):
        click.echo(f"❌ 应用文件不存在: {app_file}", err=True)
        click.echo("💡 提示: 请确保在FastORM项目根目录下运行此命令")
        sys.exit(1)

    # 构建uvicorn命令
    cmd = ["uvicorn", app]
    cmd.extend(["--host", host])
    cmd.extend(["--port", str(port)])

    if reload and not workers:
        cmd.append("--reload")

    if workers:
        cmd.extend(["--workers", str(workers)])
        if reload:
            click.echo("⚠️ 多进程模式下不支持热重载，已禁用热重载")

    # 设置环境变量
    env = os.environ.copy()
    if verbose:
        env["LOG_LEVEL"] = "debug"

    # 显示启动信息
    click.echo("🚀 启动FastORM开发服务器...")
    click.echo(f"📱 应用: {app}")
    click.echo(f"🌐 地址: http://{host}:{port}")

    if reload:
        click.echo("🔄 热重载: 启用")

    if workers:
        click.echo(f"👥 工作进程: {workers}")

    click.echo("\n💡 提示:")
    click.echo("   - 按 Ctrl+C 停止服务器")
    click.echo("   - API文档: http://127.0.0.1:8000/docs")
    click.echo("   - 交互式文档: http://127.0.0.1:8000/redoc")
    click.echo("")

    try:
        # 启动服务器
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        click.echo("\n👋 服务器已停止")
    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ 服务器启动失败: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("❌ 未找到uvicorn命令", err=True)
        click.echo("💡 请安装: pip install uvicorn[standard]")
        sys.exit(1)


def _parse_app_file(app_path: str) -> str:
    """解析应用文件路径"""
    # 从 "app.main:app" 格式中提取文件路径
    if ":" in app_path:
        module_path = app_path.split(":")[0]
    else:
        module_path = app_path

    # 转换为文件路径
    return module_path.replace(".", "/") + ".py"


def _check_app_exists(app_file: str) -> bool:
    """检查应用文件是否存在"""
    return Path(app_file).exists()
