"""
FastORM Pydantic V2 集成演示

展示第六阶段：模型验证与序列化系统功能
- 自动Pydantic Schema生成
- 双向转换：SQLAlchemy ↔ Pydantic
- 数据验证
- JSON序列化
- 字段隐藏机制
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from fastorm import Model, init


class UserStatus(Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Model):
    """用户模型 - 展示Pydantic V2集成功能"""
    
    __tablename__ = "users"
    
    # 定义隐藏字段（序列化时不显示）
    __hidden_fields__ = ["password_hash", "secret_token"]
    
    # 字段定义
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal('0.00'))
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus), 
        default=UserStatus.ACTIVE
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


async def demonstrate_schema_generation():
    """演示自动Schema生成"""
    print("\n" + "="*60)
    print("🎯 演示 1: 自动Pydantic Schema生成")
    print("="*60)
    
    # 获取完整Schema
    full_schema = User.get_pydantic_schema()
    print(f"✅ 完整Schema类名: {full_schema.__name__}")
    
    # 获取创建Schema（排除自动字段）
    create_schema = User.get_pydantic_schema(for_create=True)
    print(f"✅ 创建Schema类名: {create_schema.__name__}")
    
    # 获取部分字段Schema
    partial_schema = User.get_pydantic_schema(
        include_fields=["name", "email", "age"]
    )
    print(f"✅ 部分字段Schema类名: {partial_schema.__name__}")
    
    # 显示JSON Schema
    json_schema = User.get_pydantic_json_schema()
    print(f"✅ JSON Schema字段数量: {len(json_schema.get('properties', {}))}")
    print("📋 Schema字段:", list(json_schema.get('properties', {}).keys()))


async def demonstrate_validation():
    """演示数据验证功能"""
    print("\n" + "="*60)
    print("🔍 演示 2: 数据验证功能")
    print("="*60)
    
    # 创建用户实例
    user_data = {
        "name": "张三",
        "email": "zhangsan@example.com",
        "password_hash": "hashed_password_123",
        "secret_token": "secret_token_456",
        "age": 25,
        "balance": Decimal('1000.50'),
        "bio": "软件开发工程师",
        "status": UserStatus.ACTIVE,
        "last_login": datetime.now()
    }
    
    # 从字典创建（带验证）
    user = User.create_from_dict(user_data, validate=True)
    print(f"✅ 从字典创建用户: {user.name}")
    
    # 验证当前实例
    is_valid = user.validate_with_pydantic(raise_error=False)
    print(f"✅ 数据验证结果: {is_valid}")
    
    # 获取验证错误（如果有）
    errors = user.get_validation_errors()
    print(f"✅ 验证错误: {errors or '无错误'}")


async def demonstrate_serialization():
    """演示序列化功能"""
    print("\n" + "="*60)
    print("📤 演示 3: 序列化功能")
    print("="*60)
    
    # 创建测试用户
    user = User(
        name="李四",
        email="lisi@example.com", 
        password_hash="secret_hash",
        secret_token="secret_token",
        age=30,
        balance=Decimal('2500.75'),
        bio="产品经理",
        status=UserStatus.ACTIVE
    )
    
    # 完整序列化（隐藏敏感字段）
    user_dict = user.to_pydantic_dict()
    print("✅ 完整序列化（隐藏敏感字段）:")
    for key, value in user_dict.items():
        print(f"   {key}: {value}")
    
    # 部分字段序列化
    partial_dict = user.to_pydantic_dict(include_fields=["name", "email", "age"])
    print(f"\n✅ 部分字段序列化: {partial_dict}")
    
    # JSON序列化
    user_json = user.to_json(indent=2)
    print("\n✅ JSON序列化:")
    print(user_json)
    
    # 转换为Pydantic模型
    pydantic_user = user.to_pydantic()
    print(f"\n✅ Pydantic模型: {type(pydantic_user).__name__}")


async def demonstrate_conversion():
    """演示双向转换功能"""
    print("\n" + "="*60)
    print("🔄 演示 4: 双向转换功能")
    print("="*60)
    
    # JSON字符串
    json_data = """
    {
        "name": "王五",
        "email": "wangwu@example.com",
        "age": 28,
        "balance": 1500.25,
        "bio": "UI设计师",
        "status": "active"
    }
    """
    
    # 从JSON创建（创建模式）
    user_from_json = User.from_json(json_data, validate=True, for_create=True)
    print(f"✅ 从JSON创建用户: {user_from_json.name}")
    
    # 转换为Pydantic并再转回
    pydantic_obj = user_from_json.to_pydantic()
    user_from_pydantic = User.from_pydantic(pydantic_obj)
    print(f"✅ Pydantic转换循环: {user_from_pydantic.name}")
    
    # 更新操作
    update_data = {
        "name": "王五-更新",
        "age": 29
    }
    # 更新操作应该使用普通Schema，而不是创建Schema
    update_schema = User.get_pydantic_schema()
    # 直接从字典创建Pydantic对象，只包含更新的字段
    from pydantic import BaseModel
    
    class UpdateModel(BaseModel):
        name: Optional[str] = None
        age: Optional[int] = None
    
    update_obj = UpdateModel.model_validate(update_data)
    user_from_json.update_from_pydantic(update_obj)
    print(f"✅ 更新后用户: {user_from_json.name}, 年龄: {user_from_json.age}")


async def demonstrate_field_filtering():
    """演示字段过滤功能"""
    print("\n" + "="*60)
    print("🔒 演示 5: 字段过滤功能")
    print("="*60)
    
    # 创建包含敏感信息的用户
    sensitive_user = User(
        name="敏感用户",
        email="sensitive@example.com",
        password_hash="super_secret_hash",
        secret_token="top_secret_token",
        age=35,
        bio="管理员用户",
        balance=Decimal('5000.00'),  # 添加balance默认值
        status=UserStatus.ACTIVE     # 添加status默认值
    )
    
    # 默认序列化（隐藏敏感字段）
    safe_dict = sensitive_user.to_pydantic_dict()
    print("✅ 安全序列化（自动隐藏敏感字段）:")
    print(f"   包含字段: {list(safe_dict.keys())}")
    print(f"   是否包含密码: {'password_hash' in safe_dict}")
    print(f"   是否包含令牌: {'secret_token' in safe_dict}")
    
    # 排除额外字段
    public_dict = sensitive_user.to_pydantic_dict(
        exclude_fields=["bio", "age"]
    )
    print(f"\n✅ 公开信息: {list(public_dict.keys())}")
    
    # 仅包含特定字段
    basic_dict = sensitive_user.to_pydantic_dict(
        include_fields=["name", "email"]
    )
    print(f"✅ 基础信息: {basic_dict}")


async def main():
    """主演示函数"""
    print("🚀 FastORM 第六阶段：Pydantic V2 深度集成演示")
    print("📅 版本: SQLAlchemy 2.0.41 + Pydantic 2.11.5")
    
    # 设置FastORM
    init("sqlite+aiosqlite:///pydantic_v2_demo.db")
    
    # 演示各种功能
    await demonstrate_schema_generation()
    await demonstrate_validation()
    await demonstrate_serialization()
    await demonstrate_conversion()
    await demonstrate_field_filtering()
    
    print("\n" + "="*60)
    print("🎉 Pydantic V2 集成演示完成！")
    print("="*60)
    print("\n💡 主要特性:")
    print("  ✅ 自动Pydantic Schema生成")
    print("  ✅ 双向数据转换和验证")
    print("  ✅ 智能字段过滤和隐藏")
    print("  ✅ JSON序列化支持")
    print("  ✅ 创建/更新模式支持")
    print("  ✅ 完美的类型安全")


if __name__ == "__main__":
    asyncio.run(main()) 