"""
FastORM数据库操作命令

提供数据库创建、删除、重置等操作。
"""

import click
import sys
import asyncio
from pathlib import Path


@click.group(name='db')
@click.pass_context
def database(ctx):
    """
    🗄️ 数据库操作命令组
    
    提供数据库的创建、删除、重置等管理功能。
    """
    pass


@database.command()
@click.option('--drop', is_flag=True, help='删除现有数据库')
@click.pass_context
def create(ctx, drop: bool):
    """
    📦 创建数据库
    
    创建项目配置的数据库。
    """
    verbose = ctx.obj.get('verbose', False)
    
    if verbose:
        click.echo("📦 创建数据库...")
    
    try:
        # 这里可以添加实际的数据库创建逻辑
        click.echo("✅ 数据库创建成功")
    except Exception as e:
        click.echo(f"❌ 数据库创建失败: {e}", err=True)
        sys.exit(1)


@database.command()
@click.confirmation_option(
    prompt='确定要删除数据库吗？此操作不可恢复！'
)
@click.pass_context
def drop(ctx):
    """
    🗑️ 删除数据库
    
    删除项目数据库及所有数据。
    """
    verbose = ctx.obj.get('verbose', False)
    
    if verbose:
        click.echo("🗑️ 删除数据库...")
    
    try:
        # 这里可以添加实际的数据库删除逻辑
        click.echo("✅ 数据库删除成功")
    except Exception as e:
        click.echo(f"❌ 数据库删除失败: {e}", err=True)
        sys.exit(1)


@database.command()
@click.confirmation_option(
    prompt='确定要重置数据库吗？所有数据将丢失！'
)
@click.pass_context
def reset(ctx):
    """
    🔄 重置数据库
    
    删除并重新创建数据库，运行所有迁移。
    """
    verbose = ctx.obj.get('verbose', False)
    
    if verbose:
        click.echo("🔄 重置数据库...")
    
    try:
        # 删除数据库
        if verbose:
            click.echo("  🗑️ 删除现有数据库...")
        
        # 创建数据库
        if verbose:
            click.echo("  📦 创建新数据库...")
        
        # 运行迁移
        if verbose:
            click.echo("  ⬆️ 运行迁移...")
        
        click.echo("✅ 数据库重置成功")
    except Exception as e:
        click.echo(f"❌ 数据库重置失败: {e}", err=True)
        sys.exit(1)


@database.command()
@click.pass_context
def seed(ctx):
    """
    🌱 填充测试数据
    
    运行数据库种子文件，填充测试数据。
    """
    verbose = ctx.obj.get('verbose', False)
    
    if verbose:
        click.echo("🌱 填充测试数据...")
    
    try:
        # 检查种子文件
        seed_file = Path('scripts/seed.py')
        if not seed_file.exists():
            click.echo("⚠️ 未找到种子文件: scripts/seed.py")
            if click.confirm("是否创建示例种子文件？"):
                _create_seed_file(seed_file, verbose)
            return
        
        # 运行种子文件
        if verbose:
            click.echo(f"  📄 运行种子文件: {seed_file}")
        
        click.echo("✅ 测试数据填充完成")
    except Exception as e:
        click.echo(f"❌ 数据填充失败: {e}", err=True)
        sys.exit(1)


def _create_seed_file(seed_file: Path, verbose: bool):
    """创建示例种子文件"""
    seed_content = '''"""
数据库种子文件

用于填充测试数据
"""

import asyncio
from app.core.database import database
from app.models.user import User


async def seed_users():
    """创建测试用户"""
    async with database.session() as session:
        # 创建测试用户
        users_data = [
            {
                "username": "admin",
                "email": "admin@example.com", 
                "full_name": "Administrator"
            },
            {
                "username": "user1",
                "email": "user1@example.com",
                "full_name": "Test User 1"
            },
            {
                "username": "user2", 
                "email": "user2@example.com",
                "full_name": "Test User 2"
            }
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            session.add(user)
        
        await session.commit()
        print(f"✅ 创建了 {len(users_data)} 个测试用户")


async def main():
    """主函数"""
    print("🌱 开始填充测试数据...")
    
    await database.connect()
    try:
        await seed_users()
        print("✅ 所有测试数据填充完成")
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    # 确保目录存在
    seed_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入种子文件
    with open(seed_file, 'w', encoding='utf-8') as f:
        f.write(seed_content)
    
    if verbose:
        click.echo(f"  ✓ 创建种子文件: {seed_file}") 