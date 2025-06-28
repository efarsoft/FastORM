"""
FastORM 序列化功能测试

测试序列化系统的API集成功能：
- 序列化引擎
- 序列化配置
- 序列化上下文
- 字段序列化
- 关系序列化
- 异步序列化
- 缓存机制
"""

import pytest
import time
from sqlalchemy import Column, Integer, String, Float, ForeignKey

from fastorm.model.model import Model
from fastorm.serialization import (
    SerializationEngine,
    SerializationConfig,
    SerializationContext,
    SerializationError,
    FieldSerializationError,
    CircularReferenceError,
)


# =================================================================
# 测试模型定义
# =================================================================

class SerializationTestUser(Model):
    """序列化测试用户模型"""
    __tablename__ = 'serialization_test_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True)
    age = Column(Integer)
    balance = Column(Float, default=0.0)


class SerializationTestProfile(Model):
    """序列化测试档案模型"""
    __tablename__ = 'serialization_test_profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('serialization_test_users.id'))
    bio = Column(String(500))
    website = Column(String(200))


# =================================================================
# 测试用例
# =================================================================

class TestSerializationConfig:
    """序列化配置测试类"""
    
    def test_serialization_config_default(self):
        """测试序列化配置默认值"""
        config = SerializationConfig()
        
        assert config.include_none is False
        assert config.exclude_none is True
        assert config.by_alias is True
        assert config.exclude_unset is False
        assert config.serialize_relations is True
        assert config.max_depth == 3
        assert config.enable_cache is True
        assert config.cache_ttl == 300
        assert config.async_timeout == 30.0
        assert config.max_concurrent == 10
        assert config.detect_circular is True
        assert config.max_reference_depth == 10
        assert config.datetime_format == "%Y-%m-%d %H:%M:%S"
        assert config.decimal_precision == 2
    
    def test_serialization_config_copy(self):
        """测试序列化配置复制"""
        config = SerializationConfig(
            include_none=True,
            max_depth=5,
            cache_ttl=600
        )
        
        # 测试基本复制
        config_copy = config.copy()
        assert config_copy.include_none is True
        assert config_copy.max_depth == 5
        assert config_copy.cache_ttl == 600
        
        # 测试带参数的复制
        config_modified = config.copy(max_depth=10, enable_cache=False)
        assert config_modified.include_none is True  # 保持原值
        assert config_modified.max_depth == 10  # 新值
        assert config_modified.enable_cache is False  # 新值
        assert config_modified.cache_ttl == 600  # 保持原值


class TestSerializationContext:
    """序列化上下文测试类"""
    
    def test_serialization_context_creation(self):
        """测试序列化上下文创建"""
        context = SerializationContext(
            model_name="User",
            instance_id="123",
            operation_type="serialize"
        )
        
        assert context.model_name == "User"
        assert context.instance_id == "123"
        assert context.operation_type == "serialize"
        assert context.current_depth == 0
        assert len(context.reference_path) == 0
        assert len(context.serialized_objects) == 0
        assert len(context.errors) == 0
        assert len(context.warnings) == 0
    
    def test_serialization_context_error_management(self):
        """测试序列化上下文错误管理"""
        context = SerializationContext()
        
        # 添加错误
        error = SerializationError("Test error")
        context.add_error(error)
        
        assert len(context.errors) == 1
        assert context.errors[0] == error
        
        # 添加警告
        context.add_warning("Test warning")
        
        assert len(context.warnings) == 1
        assert context.warnings[0] == "Test warning"
    
    def test_serialization_context_object_tracking(self):
        """测试序列化上下文对象跟踪"""
        context = SerializationContext()
        
        # 进入对象
        can_continue = context.enter_object(123, "User")
        assert can_continue is True
        assert context.current_depth == 1
        assert len(context.reference_path) == 1
        assert context.reference_path[0] == "User"
        assert 123 in context.serialized_objects
        
        # 退出对象
        context.exit_object(123)
        assert context.current_depth == 0
        assert len(context.reference_path) == 0
        assert 123 not in context.serialized_objects
    
    def test_serialization_context_circular_reference_detection(self):
        """测试循环引用检测"""
        config = SerializationConfig(detect_circular=True)
        context = SerializationContext(config=config)
        
        # 第一次进入对象
        context.enter_object(123, "User")
        
        # 再次进入相同对象应该抛出异常
        with pytest.raises(CircularReferenceError) as exc_info:
            context.enter_object(123, "User")
        
        assert "循环引用" in str(exc_info.value)
    
    def test_serialization_context_depth_limit(self):
        """测试深度限制"""
        config = SerializationConfig(max_depth=2)
        context = SerializationContext(config=config)
        
        # 第一层
        can_continue = context.enter_object(1, "User")
        assert can_continue is True
        
        # 第二层
        can_continue = context.enter_object(2, "Profile")
        assert can_continue is True
        
        # 第三层应该超过限制
        can_continue = context.enter_object(3, "Address")
        assert can_continue is False
    
    def test_serialization_context_elapsed_time(self):
        """测试执行时间计算"""
        context = SerializationContext()
        
        # 等待一小段时间
        time.sleep(0.1)
        
        elapsed = context.get_elapsed_time()
        assert elapsed >= 0.1
        assert elapsed < 1.0


class TestSerializationEngine:
    """序列化引擎测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建序列化引擎"""
        return SerializationEngine()
    
    @pytest.fixture
    def test_user_data(self):
        """创建测试用户数据"""
        return {
            "id": 1,
            "name": "Test User",
            "email": "test@example.com",
            "age": 25,
            "balance": 100.50
        }
    
    def test_serialization_engine_creation(self, engine):
        """测试序列化引擎创建"""
        assert isinstance(engine.config, SerializationConfig)
        assert len(engine._cache) == 0
        assert len(engine._serializers) == 0
        assert len(engine._field_serializers) == 0
    
    def test_serialization_engine_register_serializer(self, engine):
        """测试注册序列化器"""
        def custom_serializer(obj, context):
            return {"custom": "serialized"}
        
        engine.register_serializer(str, custom_serializer)
        
        assert str in engine._serializers
        assert engine._serializers[str] == custom_serializer
    
    def test_serialization_engine_register_field_serializer(self, engine):
        """测试注册字段序列化器"""
        def custom_field_serializer(value, context):
            return f"custom_{value}"
        
        engine.register_field_serializer("custom_field", custom_field_serializer)
        
        assert "custom_field" in engine._field_serializers
        assert engine._field_serializers["custom_field"] == custom_field_serializer
    
    def test_serialization_engine_basic_serialization(self, engine, test_user_data):
        """测试基本序列化"""
        result = engine.serialize(test_user_data)
        
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["age"] == 25
        assert result["balance"] == 100.50
    
    def test_serialization_engine_with_config(self, engine, test_user_data):
        """测试带配置的序列化"""
        config = SerializationConfig(
            include_none=True,
            exclude_none=False
        )
        
        # 添加None值
        test_data = test_user_data.copy()
        test_data["middle_name"] = None
        
        result = engine.serialize(test_data, config=config)
        
        assert "middle_name" in result
        assert result["middle_name"] is None
    
    def test_serialization_engine_stats(self, engine, test_user_data):
        """测试序列化统计"""
        # 获取初始统计
        initial_stats = engine.get_stats()
        assert initial_stats["total_serializations"] == 0
        
        # 执行序列化
        engine.serialize(test_user_data)
        
        # 检查统计更新
        stats = engine.get_stats()
        assert stats["total_serializations"] == 1
        assert stats["average_time"] >= 0
    
    def test_serialization_engine_cache(self, engine, test_user_data):
        """测试序列化缓存"""
        config = SerializationConfig(enable_cache=True)
        
        # 第一次序列化
        result1 = engine.serialize(test_user_data, config=config)
        stats1 = engine.get_stats()
        
        # 第二次序列化（应该使用缓存）
        result2 = engine.serialize(test_user_data, config=config)
        stats2 = engine.get_stats()
        
        assert result1 == result2
        assert stats2["cache_hits"] > stats1["cache_hits"]
    
    def test_serialization_engine_clear_cache(self, engine, test_user_data):
        """测试清理缓存"""
        config = SerializationConfig(enable_cache=True)
        
        # 序列化以填充缓存
        engine.serialize(test_user_data, config=config)
        assert len(engine._cache) > 0
        
        # 清理缓存
        engine.clear_cache()
        assert len(engine._cache) == 0
        assert len(engine._cache_timestamps) == 0
    
    def test_serialization_engine_reset_stats(self, engine, test_user_data):
        """测试重置统计"""
        # 执行一些操作
        engine.serialize(test_user_data)
        
        stats = engine.get_stats()
        assert stats["total_serializations"] > 0
        
        # 重置统计
        engine.reset_stats()
        
        new_stats = engine.get_stats()
        assert new_stats["total_serializations"] == 0
        assert new_stats["cache_hits"] == 0
        assert new_stats["cache_misses"] == 0
        assert new_stats["average_time"] == 0.0


class TestAsyncSerialization:
    """异步序列化测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建序列化引擎"""
        return SerializationEngine()
    
    @pytest.mark.asyncio
    async def test_async_serialization_basic(self, engine):
        """测试基本异步序列化"""
        test_data = {
            "id": 1,
            "name": "Async User",
            "email": "async@example.com"
        }
        
        result = await engine.serialize_async(test_data)
        
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "Async User"
        assert result["email"] == "async@example.com"
    
    @pytest.mark.asyncio
    async def test_async_serialization_stats(self, engine):
        """测试异步序列化统计"""
        test_data = {"id": 1, "name": "Test"}
        
        # 执行异步序列化
        await engine.serialize_async(test_data)
        
        stats = engine.get_stats()
        assert stats["async_serializations"] == 1
        assert stats["total_serializations"] == 1


class TestModelIntegration:
    """模型集成测试类"""
    
    @pytest.mark.asyncio
    async def test_model_serialization_integration(self, test_database):
        """测试模型序列化集成"""
        # 创建测试用户
        user = SerializationTestUser(
            name="Serialization User",
            email="serialization@example.com",
            age=30,
            balance=250.75
        )
        await user.save()
        
        # 使用序列化引擎
        engine = SerializationEngine()
        
        # 序列化用户数据
        user_dict = user.to_dict()
        result = engine.serialize(user_dict)
        
        assert isinstance(result, dict)
        assert result["name"] == "Serialization User"
        assert result["email"] == "serialization@example.com"
        assert result["age"] == 30
        assert result["balance"] == 250.75
    
    @pytest.mark.asyncio
    async def test_model_to_dict_serialization(self, test_database):
        """测试模型to_dict序列化"""
        # 创建测试用户
        user = SerializationTestUser(
            name="Dict User",
            email="dict@example.com",
            age=35
        )
        await user.save()
        
        # 测试to_dict方法
        user_dict = user.to_dict()
        
        assert isinstance(user_dict, dict)
        assert "id" in user_dict
        assert user_dict["name"] == "Dict User"
        assert user_dict["email"] == "dict@example.com"
        assert user_dict["age"] == 35
        
        # 测试排除字段
        user_dict_excluded = user.to_dict(exclude=["email"])
        assert "email" not in user_dict_excluded
        assert "name" in user_dict_excluded


class TestSerializationExceptions:
    """序列化异常测试类"""
    
    def test_serialization_error_creation(self):
        """测试序列化错误创建"""
        error = SerializationError("Test serialization error")
        
        assert str(error) == "序列化错误: Test serialization error"
        assert isinstance(error, Exception)
    
    def test_field_serialization_error_creation(self):
        """测试字段序列化错误创建"""
        error = FieldSerializationError(
            field="test_field",
            value="test_value",
            message="Test field error"
        )
        
        assert error.field == "test_field"
        assert error.value == "test_value"
        assert "test_field" in str(error)
        assert "Test field error" in str(error)
    
    def test_circular_reference_error_creation(self):
        """测试循环引用错误创建"""
        error = CircularReferenceError(
            message="Circular reference detected",
            reference_path=["User", "Profile", "User"]
        )
        
        assert error.reference_path == ["User", "Profile", "User"]
        assert "Circular reference detected" in str(error)
        assert "User -> Profile -> User" in str(error)


class TestSerializationPerformance:
    """序列化性能测试类"""
    
    @pytest.fixture
    def engine(self):
        """创建序列化引擎"""
        return SerializationEngine()
    
    def test_serialization_performance_large_data(self, engine):
        """测试大数据序列化性能"""
        # 创建大量数据
        large_data = {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "age": 20 + (i % 50),
                    "balance": float(i * 10.5)
                }
                for i in range(100)
            ]
        }
        
        start_time = time.time()
        result = engine.serialize(large_data)
        end_time = time.time()
        
        # 验证结果
        assert isinstance(result, dict)
        assert "users" in result
        assert len(result["users"]) == 100
        
        # 验证性能（应该在合理时间内完成）
        elapsed_time = end_time - start_time
        assert elapsed_time < 1.0  # 应该在1秒内完成
    
    def test_serialization_cache_performance(self, engine):
        """测试缓存性能"""
        config = SerializationConfig(enable_cache=True)
        test_data = {"id": 1, "name": "Cache Test"}
        
        # 第一次序列化（缓存未命中）
        start_time = time.time()
        result1 = engine.serialize(test_data, config=config)
        first_time = time.time() - start_time
        
        # 第二次序列化（缓存命中）
        start_time = time.time()
        result2 = engine.serialize(test_data, config=config)
        second_time = time.time() - start_time
        
        # 验证结果相同
        assert result1 == result2
        
        # 缓存命中应该更快（在大多数情况下）
        # 注意：由于数据很小，差异可能不明显，所以只验证功能正确性
        stats = engine.get_stats()
        assert stats["cache_hits"] > 0 