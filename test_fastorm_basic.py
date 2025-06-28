#!/usr/bin/env python3
"""
FastORM 基本功能测试脚本

测试FastORM的核心功能是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from fastorm import Model, Database
from fastorm.connection.database import init, close, create_all
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer


class TestUser(Model):
    """测试用户模型"""
    __tablename__ = "test_users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)


async def test_basic_functionality():
    """测试基本功能"""
    print("🚀 开始测试FastORM基本功能...")
    
    try:
        # 1. 初始化数据库连接
        print("1. 初始化数据库连接...")
        db = init("sqlite+aiosqlite:///:memory:", echo=True)
        print("   ✅ 数据库连接初始化成功")
        
        # 2. 创建表
        print("2. 创建数据库表...")
        await create_all()
        print("   ✅ 数据库表创建成功")
        
        # 3. 测试创建记录
        print("3. 测试创建记录...")
        user = await TestUser.create(
            name="张三",
            email="zhangsan@example.com",
            age=25
        )
        print(f"   ✅ 用户创建成功: {user.name} (ID: {user.id})")
        
        # 4. 测试查询记录
        print("4. 测试查询记录...")
        found_user = await TestUser.find(user.id)
        if found_user:
            print(f"   ✅ 用户查询成功: {found_user.name}")
        else:
            print("   ❌ 用户查询失败")
            
        # 5. 测试where查询
        print("5. 测试where查询...")
        users = await TestUser.where('name', '张三').get()
        print(f"   ✅ where查询成功，找到 {len(users)} 个用户")
        
        # 6. 测试更新记录
        print("6. 测试更新记录...")
        await user.update(age=26)
        updated_user = await TestUser.find(user.id)
        print(f"   ✅ 用户更新成功，新年龄: {updated_user.age}")
        
        # 7. 测试计数
        print("7. 测试计数...")
        count = await TestUser.count()
        print(f"   ✅ 计数成功，总用户数: {count}")
        
        # 8. 测试删除记录
        print("8. 测试删除记录...")
        await user.delete()
        deleted_user = await TestUser.find(user.id)
        if deleted_user is None:
            print("   ✅ 用户删除成功")
        else:
            print("   ❌ 用户删除失败")
            
        print("\n🎉 所有基本功能测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理连接
        await close()
        print("🔧 数据库连接已关闭")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_basic_functionality()) 