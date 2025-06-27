"""
FastORM 集成读写分离功能测试

测试集成到FastORM核心架构中的读写分离功能。
"""

import pytest

from fastorm.connection.database import Database, ReadWriteConfig


class TestIntegratedReadWriteSplit:
    """集成读写分离功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        # 清理数据库状态
        Database._engines.clear()
        Database._session_factories.clear()
        Database._is_read_write_mode = False
        Database._current_connection_type = None
        Database._config = None
    
    def test_read_write_config_creation(self):
        """测试读写分离配置创建"""
        # 测试默认配置（读写分离默认关闭）
        config_default = ReadWriteConfig()
        assert config_default.enable_read_write_split is False
        
        # 测试显式启用读写分离
        config = ReadWriteConfig(
            enable_read_write_split=True,
            read_preference="prefer_secondary",
            write_concern="primary_only"
        )
        
        assert config.enable_read_write_split is True
        assert config.read_preference == "prefer_secondary"
        assert config.write_concern == "primary_only"
    
    def test_single_database_mode(self):
        """测试单数据库模式"""
        Database.init("sqlite+aiosqlite:///test.db")
        
        info = Database.get_connection_info()
        assert info["mode"] == "single"
        assert "default" in info["engines"]
        assert info["read_write_split_enabled"] is False
    
    def test_read_write_split_mode(self):
        """测试读写分离模式"""
        config = ReadWriteConfig(enable_read_write_split=True)
        
        Database.init({
            "write": "sqlite+aiosqlite:///master.db",
            "read": "sqlite+aiosqlite:///slave.db"
        }, read_write_config=config)
        
        info = Database.get_connection_info()
        assert info["mode"] == "read_write_split"
        assert "write" in info["engines"]
        assert "read" in info["engines"]
        assert info["read_write_split_enabled"] is True
    
    def test_connection_type_determination(self):
        """测试连接类型判断"""
        config = ReadWriteConfig(enable_read_write_split=True)
        
        Database.init({
            "write": "sqlite+aiosqlite:///master.db",
            "read": "sqlite+aiosqlite:///slave.db"
        }, read_write_config=config)
        
        # 测试写操作路由
        write_key = Database._determine_connection_type("write")
        assert write_key == "write"
        
        # 测试读操作路由
        read_key = Database._determine_connection_type("read")
        assert read_key == "read"
        
        # 测试事务操作路由
        tx_key = Database._determine_connection_type("transaction")
        assert tx_key == "write"
    
    def test_engine_and_factory_retrieval(self):
        """测试引擎和会话工厂获取"""
        config = ReadWriteConfig(enable_read_write_split=True)
        
        Database.init({
            "write": "sqlite+aiosqlite:///master.db",
            "read": "sqlite+aiosqlite:///slave.db"
        }, read_write_config=config)
        
        # 测试获取写库引擎
        write_engine = Database.get_engine("write")
        assert write_engine is not None
        
        # 测试获取读库引擎
        read_engine = Database.get_engine("read")
        assert read_engine is not None
        
        # 测试获取写库会话工厂
        write_factory = Database.get_session_factory("write")
        assert write_factory is not None
        
        # 测试获取读库会话工厂
        read_factory = Database.get_session_factory("read")
        assert read_factory is not None
    
    def test_fallback_to_write_when_no_read_db(self):
        """测试没有读库时回退到写库"""
        config = ReadWriteConfig(enable_read_write_split=True)
        
        # 只配置写库，没有读库
        Database.init({
            "write": "sqlite+aiosqlite:///master.db"
        }, read_write_config=config)
        
        # 读操作应该回退到写库
        read_key = Database._determine_connection_type("read")
        assert read_key == "write"
    
    def test_disabled_read_write_split(self):
        """测试禁用读写分离时的行为"""
        config = ReadWriteConfig(enable_read_write_split=False)
        
        Database.init({
            "write": "sqlite+aiosqlite:///master.db",
            "read": "sqlite+aiosqlite:///slave.db"
        }, read_write_config=config)
        
        # 即使有读库，读操作也应该使用写库
        read_key = Database._determine_connection_type("read")
        assert read_key == "write"
    
    @pytest.mark.asyncio
    async def test_session_context_managers(self):
        """测试会话上下文管理器"""
        config = ReadWriteConfig(enable_read_write_split=True)
        
        Database.init({
            "write": "sqlite+aiosqlite:///master.db",
            "read": "sqlite+aiosqlite:///slave.db"
        }, read_write_config=config)
        
        # 测试普通会话
        async with Database.session() as session:
            assert session is not None
        
        # 测试读会话
        async with Database.read_session() as session:
            assert session is not None
        
        # 测试写会话
        async with Database.write_session() as session:
            assert session is not None
        
        # 测试事务会话
        async with Database.transaction() as session:
            assert session is not None
        
        await Database.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 