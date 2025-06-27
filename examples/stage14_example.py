"""
FastORM Stage 14 功能示例：验证系统增强、序列化系统增强、批量操作增强

本示例展示了FastORM第十四阶段新增的核心功能：
1. 验证系统增强 - 基于Pydantic 2.11的高级验证
2. 序列化系统增强 - 多格式序列化和自定义序列化器
3. 批量操作增强 - 高性能批量数据处理
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import String, Integer, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column

# FastORM核心导入
from fastorm import BaseModel, Database, Session

# 验证系统导入
from fastorm.validation import (
    ValidationEngine, ValidationContext, ValidationConfig,
    FieldValidatorRegistry, ModelValidatorRegistry,
    validate_field, validate_model, ValidationError
)

# 序列化系统导入
from fastorm.serialization import (
    SerializationEngine, SerializationConfig,
    serialize_field, serialize_model,
    format_as_json, format_as_xml, format_as_csv,
    JSONFormatter, XMLFormatter, CSVFormatter
)

# 批量操作导入
from fastorm.batch import (
    BatchEngine, BatchConfig,
    BatchInsert, BatchUpdate, BatchDelete
)


# =============================================================================
# 1. 定义模型和验证规则
# =============================================================================

@validate_model(
    serialize_relations=True,
    max_depth=2
)
class User(BaseModel):
    """用户模型 - 展示验证和序列化功能"""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    @validate_field(
        field_type="string",
        min_length=2,
        max_length=50
    )
    @serialize_field(alias="user_name", exclude_none=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    @validate_field(
        field_type="email",
        required=True
    )
    @serialize_field(alias="email_address")
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    
    @validate_field(
        field_type="decimal",
        min_value=0,
        precision=2
    )
    @serialize_field(alias="account_balance", format_string="{:.2f}")
    balance: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    
    @serialize_field(alias="registration_date", format_string="%Y-%m-%d %H:%M:%S")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 自定义验证方法
    @classmethod
    def validate_unique_email(cls, email: str, session: Session) -> bool:
        """验证邮箱唯一性"""
        existing = session.query(cls).filter(cls.email == email).first()
        return existing is None


@validate_model(exclude_fields=["password_hash"])
class UserProfile(BaseModel):
    """用户资料模型"""
    
    __tablename__ = "user_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    @serialize_field(alias="full_name")
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    @serialize_field(alias="bio", exclude_empty=True)
    bio: Mapped[Optional[str]] = mapped_column(String(500))
    
    @serialize_field(exclude_from_serialization=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(128))


# =============================================================================
# 2. 验证系统示例
# =============================================================================

async def validation_examples():
    """验证系统功能示例"""
    
    print("=" * 60)
    print("验证系统增强示例")
    print("=" * 60)
    
    # 创建验证引擎
    config = ValidationConfig(
        strict_mode=True,
        enable_cache=True,
        async_timeout=10.0
    )
    validator = ValidationEngine(config)
    
    # 注册自定义验证器
    field_registry = FieldValidatorRegistry()
    
    # 验证用户数据
    user_data = {
        "name": "张三",
        "email": "zhang@example.com",
        "balance": "1000.50"
    }
    
    try:
        # 字段级验证
        context = ValidationContext(
            model_name="User",
            operation_type="create",
            config=config
        )
        
        # 验证姓名
        validated_name = await validator.validate_field(
            "name", user_data["name"], context
        )
        print(f"✓ 姓名验证通过: {validated_name}")
        
        # 验证邮箱
        validated_email = await validator.validate_field(
            "email", user_data["email"], context
        )
        print(f"✓ 邮箱验证通过: {validated_email}")
        
        # 验证余额
        validated_balance = await validator.validate_field(
            "balance", user_data["balance"], context
        )
        print(f"✓ 余额验证通过: {validated_balance}")
        
        # 模型级验证
        validated_model = await validator.validate_model(User, user_data, context)
        print(f"✓ 模型验证通过: {type(validated_model).__name__}")
        
    except ValidationError as e:
        print(f"✗ 验证失败: {e}")
    
    # 展示验证统计
    stats = validator.get_stats()
    print(f"\n验证统计:")
    print(f"  总验证次数: {stats['total_validations']}")
    print(f"  缓存命中率: {stats['cache_hit_rate']:.1%}")
    print(f"  平均验证时间: {stats['average_time']:.3f}秒")


# =============================================================================
# 3. 序列化系统示例
# =============================================================================

async def serialization_examples():
    """序列化系统功能示例"""
    
    print("\n" + "=" * 60)
    print("序列化系统增强示例")
    print("=" * 60)
    
    # 创建示例数据
    user = User(
        id=1,
        name="张三",
        email="zhang@example.com",
        balance=Decimal("1500.75"),
        created_at=datetime.now()
    )
    
    profile = UserProfile(
        id=1,
        user_id=1,
        full_name="张三丰",
        bio="武当山创始人",
        password_hash="hashed_password_123"
    )
    
    # 创建序列化引擎
    config = SerializationConfig(
        exclude_none=True,
        serialize_relations=True,
        max_depth=2
    )
    serializer = SerializationEngine(config)
    
    # 序列化单个对象
    print("\n1. 单个对象序列化:")
    user_dict = serializer.serialize(user)
    print(f"用户数据: {user_dict}")
    
    profile_dict = serializer.serialize(profile)
    print(f"资料数据: {profile_dict}")
    
    # 多格式输出
    print("\n2. 多格式序列化:")
    
    # JSON格式
    json_output = format_as_json(user_dict, indent=2)
    print("JSON格式:")
    print(json_output)
    
    # XML格式
    xml_output = format_as_xml(user_dict, root_name="user")
    print("\nXML格式:")
    print(xml_output)
    
    # CSV格式 (适用于列表数据)
    users_list = [user_dict, profile_dict]
    csv_output = format_as_csv(users_list)
    print("\nCSV格式:")
    print(csv_output)
    
    # 自定义序列化器示例
    print("\n3. 自定义序列化:")
    
    from fastorm.serialization import create_datetime_serializer, create_decimal_serializer
    
    # 注册自定义序列化器
    datetime_serializer = create_datetime_serializer("%Y年%m月%d日 %H:%M:%S")
    decimal_serializer = create_decimal_serializer(precision=1)
    
    serializer.register_field_serializer("created_at", datetime_serializer)
    serializer.register_field_serializer("balance", decimal_serializer)
    
    custom_serialized = serializer.serialize(user)
    print(f"自定义格式: {custom_serialized}")
    
    # 序列化统计
    stats = serializer.get_stats()
    print(f"\n序列化统计:")
    print(f"  总序列化次数: {stats['total_serializations']}")
    print(f"  缓存命中率: {stats['cache_hit_rate']:.1%}")
    print(f"  平均序列化时间: {stats['average_time']:.3f}秒")


# =============================================================================
# 4. 批量操作系统示例
# =============================================================================

async def batch_operations_examples():
    """批量操作功能示例"""
    
    print("\n" + "=" * 60)
    print("批量操作增强示例")
    print("=" * 60)
    
    # 模拟数据库会话
    session = None  # 在实际使用中，这里应该是真实的session
    
    # 创建批量操作引擎
    config = BatchConfig(
        batch_size=100,
        use_transactions=True,
        enable_monitoring=True,
        memory_limit_mb=256.0
    )
    
    # 在实际使用中创建引擎
    # batch_engine = BatchEngine(session, config)
    
    # 准备批量数据
    print("\n1. 准备批量数据:")
    
    users_data = []
    for i in range(1000):
        users_data.append({
            "name": f"用户{i:04d}",
            "email": f"user{i:04d}@example.com",
            "balance": Decimal(f"{i * 10.5:.2f}"),
            "created_at": datetime.now()
        })
    
    print(f"准备了 {len(users_data)} 条用户记录")
    
    # 模拟批量插入操作
    print("\n2. 批量插入操作:")
    print("配置信息:")
    print(f"  批量大小: {config.batch_size}")
    print(f"  使用事务: {config.use_transactions}")
    print(f"  内存限制: {config.memory_limit_mb}MB")
    print(f"  启用监控: {config.enable_monitoring}")
    
    # 在实际使用中执行批量操作
    # try:
    #     result = await batch_engine.batch_insert(User, users_data, config)
    #     
    #     print(f"\n批量插入结果:")
    #     print(f"  总记录数: {result['total_records']}")
    #     print(f"  成功处理: {result['processed_records']}")
    #     print(f"  失败记录: {result['failed_records']}")
    #     print(f"  成功率: {result['success_rate']:.1f}%")
    #     print(f"  处理时间: {result['elapsed_time']:.2f}秒")
    #     print(f"  处理速率: {result['processing_rate']:.0f}记录/秒")
    #     print(f"  内存使用: {result['memory_used_mb']:.1f}MB")
    #     
    # except Exception as e:
    #     print(f"批量操作失败: {e}")
    
    # 模拟结果展示
    print(f"\n批量插入结果 (模拟):")
    print(f"  总记录数: {len(users_data)}")
    print(f"  成功处理: {len(users_data)}")
    print(f"  失败记录: 0")
    print(f"  成功率: 100.0%")
    print(f"  处理时间: 2.35秒")
    print(f"  处理速率: 426记录/秒")
    print(f"  内存使用: 45.2MB")
    
    # 批量更新示例
    print("\n3. 批量更新操作 (模拟):")
    update_data = [
        {"id": 1, "balance": Decimal("2000.00")},
        {"id": 2, "balance": Decimal("1500.00")},
        {"id": 3, "balance": Decimal("3000.00")}
    ]
    
    print(f"准备更新 {len(update_data)} 条记录的余额")
    print("更新操作配置:")
    print("  更新字段: balance")
    print("  条件字段: id")
    
    # 在实际使用中执行批量更新
    # batch_update = BatchUpdate(User, where_fields=["id"])
    # update_result = await batch_update.execute(session, update_data)
    # print(f"更新结果: {update_result}")
    
    print("批量更新结果 (模拟): {'updated_count': 3}")
    
    # 进度监控示例
    print("\n4. 进度监控:")
    
    def progress_callback(progress_info):
        """进度回调函数"""
        print(f"进度: {progress_info['progress_percentage']:.1f}% "
              f"({progress_info['processed_records']}/{progress_info['total_records']}) "
              f"- 速率: {progress_info['processing_rate']:.0f}记录/秒")
    
    # 在实际使用中设置进度回调
    # config_with_callback = config.copy(progress_callback=progress_callback)
    
    print("进度监控已配置，将在批量操作时显示实时进度")


# =============================================================================
# 5. 综合应用示例
# =============================================================================

async def comprehensive_example():
    """综合应用示例 - 验证、序列化、批量操作的组合使用"""
    
    print("\n" + "=" * 60)
    print("综合应用示例")
    print("=" * 60)
    
    print("场景: 用户数据导入系统")
    print("1. 验证导入数据的格式和完整性")
    print("2. 批量插入验证通过的数据")
    print("3. 序列化操作结果为多种格式输出")
    
    # 模拟导入数据 (包含一些无效数据)
    import_data = [
        {"name": "张三", "email": "zhang@example.com", "balance": "1000.00"},
        {"name": "李四", "email": "li@example.com", "balance": "1500.50"},
        {"name": "", "email": "invalid-email", "balance": "-100"},  # 无效数据
        {"name": "王五", "email": "wang@example.com", "balance": "2000.75"},
        {"name": "赵六", "email": "zhao@example.com", "balance": "abc"},  # 无效余额
    ]
    
    print(f"\n导入数据: {len(import_data)} 条记录")
    
    # 步骤1: 数据验证
    print("\n步骤1: 数据验证")
    validator = ValidationEngine()
    valid_data = []
    invalid_data = []
    
    for i, record in enumerate(import_data):
        try:
            # 这里应该使用真实的验证逻辑
            # validated = await validator.validate_model(User, record, context)
            
            # 模拟验证逻辑
            if (record.get("name") and 
                "@" in record.get("email", "") and 
                record.get("balance", "").replace(".", "").isdigit()):
                valid_data.append(record)
                print(f"  ✓ 记录 {i+1}: 验证通过")
            else:
                invalid_data.append(record)
                print(f"  ✗ 记录 {i+1}: 验证失败")
                
        except Exception as e:
            invalid_data.append(record)
            print(f"  ✗ 记录 {i+1}: 验证异常 - {e}")
    
    print(f"\n验证结果: {len(valid_data)} 条有效, {len(invalid_data)} 条无效")
    
    # 步骤2: 批量插入
    print("\n步骤2: 批量插入有效数据")
    if valid_data:
        # 在实际使用中执行批量插入
        # batch_engine = BatchEngine(session)
        # result = await batch_engine.batch_insert(User, valid_data)
        
        # 模拟插入结果
        result = {
            "operation": "insert",
            "total_records": len(valid_data),
            "processed_records": len(valid_data),
            "failed_records": 0,
            "success_rate": 100.0,
            "elapsed_time": 0.85,
            "processing_rate": len(valid_data) / 0.85
        }
        
        print(f"  插入成功: {result['processed_records']} 条记录")
        print(f"  处理时间: {result['elapsed_time']}秒")
        print(f"  处理速率: {result['processing_rate']:.0f}记录/秒")
    
    # 步骤3: 序列化结果
    print("\n步骤3: 序列化操作结果")
    
    operation_summary = {
        "import_summary": {
            "total_imported": len(import_data),
            "valid_records": len(valid_data),
            "invalid_records": len(invalid_data),
            "success_rate": len(valid_data) / len(import_data) * 100,
        },
        "batch_operation": result if valid_data else None,
        "invalid_data_samples": invalid_data[:2],  # 显示前2条无效数据
        "timestamp": datetime.now().isoformat()
    }
    
    # JSON格式输出
    json_result = format_as_json(operation_summary, indent=2)
    print("\nJSON格式结果:")
    print(json_result[:300] + "..." if len(json_result) > 300 else json_result)
    
    # XML格式输出
    xml_result = format_as_xml(operation_summary, root_name="import_result")
    print("\nXML格式结果:")
    print(xml_result[:200] + "..." if len(xml_result) > 200 else xml_result)
    
    print(f"\n✓ 综合应用示例完成")
    print(f"  数据验证: {len(valid_data)}/{len(import_data)} 通过")
    print(f"  批量插入: {'成功' if valid_data else '跳过'}")
    print(f"  结果序列化: JSON、XML格式生成完成")


# =============================================================================
# 6. 主函数
# =============================================================================

async def main():
    """主函数 - 运行所有示例"""
    
    print("FastORM Stage 14 功能示例")
    print("验证系统增强 + 序列化系统增强 + 批量操作增强")
    print("=" * 80)
    
    try:
        # 运行各个功能示例
        await validation_examples()
        await serialization_examples()
        await batch_operations_examples()
        await comprehensive_example()
        
        print("\n" + "=" * 80)
        print("所有示例执行完成！")
        print("\nStage 14 新功能特点总结:")
        print("✓ 验证系统增强 - 基于Pydantic 2.11的高级验证器")
        print("✓ 序列化系统增强 - 多格式输出和自定义序列化器")
        print("✓ 批量操作增强 - 高性能批量数据处理")
        print("✓ 完整的错误处理和监控机制")
        print("✓ 异步支持和性能优化")
        
    except Exception as e:
        print(f"\n示例执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main()) 