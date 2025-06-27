"""
FastORM 配置系统和时间戳功能演示

演示如何：
1. 使用配置系统控制全局时间戳
2. 使用默认启用的时间戳功能（timestamps=True）
3. 自定义时间戳字段名
4. 通过配置文件和环境变量控制
"""

import asyncio
import os
from datetime import datetime
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

# 导入FastORM组件
from fastorm import (
    Model, 
    init,
    get_config,
    set_config,
    get_setting,
    set_setting,
    generate_config_file,
    validate_config
)


# =============================================================================
# 模型定义 - 展示默认启用的时间戳功能
# =============================================================================

class User(Model):
    """用户模型 - 时间戳默认启用（timestamps=True）"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    
    # 时间戳已默认启用，无需设置 timestamps = True


class Post(Model):
    """文章模型 - 自定义时间戳字段名"""
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    
    # 时间戳默认启用，但自定义字段名
    created_at_column = "created_time"
    updated_at_column = "updated_time"


class Product(Model):
    """产品模型 - 显式关闭时间戳"""
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float]
    
    # 显式关闭时间戳功能
    timestamps = False


# =============================================================================
# 配置系统演示
# =============================================================================

async def demo_config_system():
    """演示配置系统功能"""
    
    print("=" * 60)
    print("FastORM 配置系统演示")
    print("=" * 60)
    
    # 1. 查看当前配置
    print("\n1. 当前配置状态:")
    config = get_config()
    print(f"  - 全局时间戳启用: {config.timestamps_enabled}")
    print(f"  - 默认created_at字段: {config.default_created_at_column}")
    print(f"  - 默认updated_at字段: {config.default_updated_at_column}")
    print(f"  - 调试模式: {config.debug}")
    print(f"  - 查询缓存: {config.query_cache_enabled}")
    
    # 2. 修改配置
    print("\n2. 修改配置:")
    set_setting('debug', True)
    set_setting('query_cache_size', 2000)
    print(f"  - 调试模式设置为: {get_setting('debug')}")
    print(f"  - 查询缓存大小设置为: {get_setting('query_cache_size')}")
    
    # 3. 批量配置更新
    print("\n3. 批量配置更新:")
    set_config(
        pool_size=10,
        max_overflow=20,
        batch_size=2000
    )
    updated_config = get_config()
    print(f"  - 连接池大小: {updated_config.pool_size}")
    print(f"  - 最大溢出: {updated_config.max_overflow}")
    print(f"  - 批量大小: {updated_config.batch_size}")
    
    # 4. 配置验证
    print("\n4. 配置验证:")
    errors = validate_config()
    if errors:
        print("  配置错误:")
        for key, error in errors.items():
            print(f"    - {key}: {error}")
    else:
        print("  ✅ 配置验证通过")


async def demo_timestamps_default_enabled():
    """演示默认启用的时间戳功能"""
    
    print("\n" + "=" * 60)
    print("时间戳功能演示 - 默认启用")
    print("=" * 60)
    
    # 1. 检查全局时间戳状态
    print(f"\n1. 全局时间戳状态: {get_setting('timestamps_enabled')}")
    
    # 2. User模型 - 默认启用时间戳
    print("\n2. User模型（时间戳默认启用）:")
    user = await User.create(name="张三", email="zhang@example.com")
    print(f"  - 用户ID: {user.id}")
    print(f"  - 创建时间: {user.get_created_at()}")
    print(f"  - 更新时间: {user.get_updated_at()}")
    
    # 3. 更新用户
    print("\n3. 更新用户:")
    await asyncio.sleep(1)  # 确保时间差异
    await user.update(name="张三丰")
    print(f"  - 更新后用户名: {user.name}")
    print(f"  - 创建时间: {user.get_created_at()}")
    print(f"  - 更新时间: {user.get_updated_at()}")
    
    # 4. Post模型 - 自定义字段名
    print("\n4. Post模型（自定义时间戳字段名）:")
    post = await Post.create(
        title="FastORM配置系统", 
        content="演示配置系统的强大功能"
    )
    print(f"  - 文章ID: {post.id}")
    print(f"  - 创建时间字段: {post.created_at_column}")
    print(f"  - 更新时间字段: {post.updated_at_column}")
    print(f"  - 创建时间: {getattr(post, post.created_at_column)}")
    print(f"  - 更新时间: {getattr(post, post.updated_at_column)}")
    
    # 5. Product模型 - 关闭时间戳
    print("\n5. Product模型（关闭时间戳）:")
    product = await Product.create(name="MacBook Pro", price=15999.0)
    print(f"  - 产品ID: {product.id}")
    print(f"  - 时间戳启用状态: {product.is_timestamps_enabled()}")
    print(f"  - 创建时间: {product.get_created_at()}")  # 应该返回None


async def demo_global_timestamp_control():
    """演示全局时间戳控制"""
    
    print("\n" + "=" * 60)
    print("全局时间戳控制演示")
    print("=" * 60)
    
    # 1. 通过配置系统关闭全局时间戳
    print("\n1. 通过配置系统关闭全局时间戳:")
    set_setting('timestamps_enabled', False)
    print(f"  - 全局时间戳状态: {get_setting('timestamps_enabled')}")
    
    # 2. 创建用户（应该没有时间戳）
    print("\n2. 创建用户（全局关闭时间戳）:")
    user2 = await User.create(name="李四", email="li@example.com")
    print(f"  - 用户ID: {user2.id}")
    print(f"  - 时间戳启用状态: {user2.is_timestamps_enabled()}")
    print(f"  - 创建时间: {user2.get_created_at()}")  # 应该返回None
    
    # 3. 重新启用全局时间戳
    print("\n3. 重新启用全局时间戳:")
    set_setting('timestamps_enabled', True)
    print(f"  - 全局时间戳状态: {get_setting('timestamps_enabled')}")
    
    # 4. 创建用户（应该有时间戳）
    print("\n4. 创建用户（重新启用时间戳）:")
    user3 = await User.create(name="王五", email="wang@example.com")
    print(f"  - 用户ID: {user3.id}")
    print(f"  - 时间戳启用状态: {user3.is_timestamps_enabled()}")
    print(f"  - 创建时间: {user3.get_created_at()}")
    print(f"  - 更新时间: {user3.get_updated_at()}")


async def demo_config_file():
    """演示配置文件功能"""
    
    print("\n" + "=" * 60)
    print("配置文件演示")
    print("=" * 60)
    
    # 1. 生成配置文件
    print("\n1. 生成示例配置文件:")
    config_file = "fastorm_demo.json"
    generate_config_file(config_file)
    print(f"  - 配置文件已生成: {config_file}")
    
    # 2. 显示配置文件内容
    print("\n2. 配置文件内容（前几行）:")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:15]  # 只显示前15行
            for i, line in enumerate(lines, 1):
                print(f"  {i:2}: {line.rstrip()}")
        print("  ...")
    except Exception as e:
        print(f"  读取配置文件失败: {e}")
    
    # 3. 清理示例文件
    try:
        os.remove(config_file)
        print(f"\n3. 示例配置文件已清理: {config_file}")
    except Exception:
        pass


async def demo_environment_variables():
    """演示环境变量配置"""
    
    print("\n" + "=" * 60)
    print("环境变量配置演示")
    print("=" * 60)
    
    # 1. 设置环境变量
    print("\n1. 设置环境变量:")
    os.environ['FASTORM_TIMESTAMPS_ENABLED'] = 'true'
    os.environ['FASTORM_DEBUG'] = 'false'
    os.environ['FASTORM_POOL_SIZE'] = '8'
    print("  - FASTORM_TIMESTAMPS_ENABLED=true")
    print("  - FASTORM_DEBUG=false")
    print("  - FASTORM_POOL_SIZE=8")
    
    # 2. 重新加载配置（在实际应用中需要重启）
    print("\n2. 环境变量配置说明:")
    print("  - 环境变量在应用启动时加载")
    print("  - 支持的环境变量前缀: FASTORM_")
    print("  - 布尔值: true/false, 1/0, yes/no, on/off")
    print("  - 数字值: 直接使用数字")
    print("  - 字符串值: 直接使用字符串")
    
    # 3. 清理环境变量
    for key in ['FASTORM_TIMESTAMPS_ENABLED', 'FASTORM_DEBUG', 'FASTORM_POOL_SIZE']:
        if key in os.environ:
            del os.environ[key]


async def main():
    """主演示函数"""
    
    print("FastORM 配置系统和时间戳功能演示")
    print("基于 SQLAlchemy 2.0 + Pydantic 2.11")
    
    # 初始化数据库（使用SQLite内存数据库）
    await init("sqlite+aiosqlite:///:memory:")
    
    # 创建表
    from fastorm.model.model import DeclarativeBase
    from fastorm.connection.database import Database
    
    async with Database.get_engine().begin() as conn:
        await conn.run_sync(DeclarativeBase.metadata.create_all)
    
    # 运行演示
    await demo_config_system()
    await demo_timestamps_default_enabled()
    await demo_global_timestamp_control()
    await demo_config_file()
    await demo_environment_variables()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n主要特性总结:")
    print("✅ 时间戳默认启用 (timestamps=True)")
    print("✅ 配置系统控制全局时间戳")
    print("✅ 支持配置文件和环境变量")
    print("✅ 自定义时间戳字段名")
    print("✅ 灵活的配置管理")
    print("✅ 配置验证功能")


if __name__ == "__main__":
    asyncio.run(main()) 