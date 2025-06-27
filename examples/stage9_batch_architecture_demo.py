#!/usr/bin/env python3
"""
FastORM第九阶段：批量操作架构重构演示

展示新的批量操作系统架构：
1. 从独立的batch模块移动到query.batch
2. 遵循DRY原则，避免功能重复
3. 提供一致的API使用方式
4. 性能监控系统集成
"""

import asyncio
import time

# SQLAlchemy 2.0 imports
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# FastORM imports - 新架构
from fastorm import Model
from fastorm.query.batch import BatchEngine, BatchConfig, BatchError
from fastorm.performance import QueryProfiler, PerformanceMonitor


# 测试模型
class User(Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)


class Product(Model):
    __tablename__ = 'products'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)  # 价格，单位分
    category: Mapped[str] = mapped_column(String(50))


async def setup_database():
    """设置测试数据库"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///batch_demo.db", echo=False
    )
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all)
        await conn.run_sync(User.metadata.create_all)
    
    # 创建会话工厂
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    return engine, async_session


async def demo_new_batch_architecture():
    """演示新的批量操作架构"""
    print("🚀 FastORM 批量操作架构重构演示")
    print("=" * 60)
    
    # 设置数据库
    engine, async_session = await setup_database()
    
    async with async_session() as session:
        # 创建批量操作引擎 - 新架构
        batch_engine = BatchEngine(session)
        
        print("\n📦 1. 批量操作系统架构展示")
        print("-" * 40)
        print("✅ 新架构路径: fastorm.query.batch")
        print("✅ 统一API: BatchEngine, BatchConfig")
        print("✅ 遵循DRY原则: 移除重复功能")
        
        # 准备测试数据
        user_data = [
            {
                "name": f"用户{i}", 
                "email": f"user{i}@example.com", 
                "age": 20 + i % 30
            }
            for i in range(1, 1001)
        ]
        
        print("\n🔢 2. 批量插入性能测试 (1000条记录)")
        print("-" * 40)
        
        # 配置批量操作
        config = BatchConfig(
            batch_size=200,
            enable_monitoring=True,
            use_transactions=True
        )
        
        start_time = time.time()
        result = await batch_engine.batch_insert(
            model_class=User,
            data=user_data,
            config=config
        )
        end_time = time.time()
        
        print(f"✅ 插入成功: {result['successful_records']} 条记录")
        print(f"⏱️  执行时间: {end_time - start_time:.3f} 秒")
        speed = result['successful_records'] / (end_time - start_time)
        print(f"🚀 处理速度: {speed:.0f} 记录/秒")
        
        print("\n📊 3. 批量操作结果详情")
        print("-" * 40)
        for key, value in result.items():
            if key != 'errors':  # 跳过错误列表显示
                print(f"  {key}: {value}")


async def demo_api_consistency():
    """演示API一致性"""
    print("\n🔄 4. API使用方式对比")
    print("-" * 40)
    
    print("✅ 新架构导入 (推荐):")
    print("   from fastorm.query.batch import BatchEngine")
    print("   from fastorm.query.batch import BatchConfig")
    
    print("\n✅ 主包导入 (向后兼容):")
    print("   from fastorm import BatchEngine, BatchConfig")
    
    print("\n❌ 旧架构 (已移除):")
    print("   from fastorm.batch import BatchEngine  # 不再支持")


async def demo_performance_monitoring():
    """演示性能监控集成"""
    print("\n📈 5. 性能监控系统集成")
    print("-" * 40)
    
    # 启动性能监控
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    engine, async_session = await setup_database()
    
    # 使用性能分析器
    profiler = QueryProfiler()
    
    with profiler.profile("batch_operations"):
        async with async_session() as session:
            batch_engine = BatchEngine(session)
            
            # 小批量操作测试
            small_data = [
                {
                    "name": f"测试用户{i}", 
                    "email": f"test{i}@example.com", 
                    "age": 25
                }
                for i in range(10)
            ]
            
            await batch_engine.batch_insert(
                model_class=User,
                data=small_data
            )
    
    # 获取性能统计
    stats = monitor.get_current_stats()
    
    print("📊 性能统计:")
    print(f"   总查询数: {stats.total_queries}")
    print(f"   平均执行时间: {stats.avg_execution_time:.3f}s")
    print(f"   慢查询数: {stats.slow_queries}")
    
    monitor.stop_monitoring()


async def demo_error_handling():
    """演示错误处理"""
    print("\n🚨 6. 错误处理演示")
    print("-" * 40)
    
    engine, async_session = await setup_database()
    
    async with async_session() as session:
        batch_engine = BatchEngine(session)
        
        # 故意制造错误的数据
        invalid_data = [
            {"name": "正常用户", "email": "normal@example.com", "age": 25},
            # name不能为空
            {"name": None, "email": "invalid@example.com", "age": 30},
        ]
        
        config = BatchConfig(
            skip_invalid_records=True,  # 跳过无效记录
            validate_data=True
        )
        
        try:
            result = await batch_engine.batch_insert(
                model_class=User,
                data=invalid_data,
                config=config
            )
            
            print(f"✅ 成功处理: {result['successful_records']} 条")
            print(f"❌ 失败记录: {result['failed_records']} 条")
            
            if result['errors']:
                print("🔍 错误详情:")
                # 只显示前3个错误
                for error in result['errors'][:3]:  
                    print(f"   - {error}")
                    
        except BatchError as e:
            print(f"❌ 批量操作错误: {e}")


async def main():
    """主演示函数"""
    try:
        await demo_new_batch_architecture()
        await demo_api_consistency()
        await demo_performance_monitoring()
        await demo_error_handling()
        
        print("\n🎉 批量操作架构重构演示完成！")
        print("=" * 60)
        print("✅ 新架构优势:")
        print("   1. 遵循DRY原则，避免功能重复")
        print("   2. 逻辑清晰，批量操作归属于查询模块")
        print("   3. API一致性，统一的导入路径")
        print("   4. 性能监控集成，企业级功能")
        print("   5. 向后兼容，平滑迁移")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 