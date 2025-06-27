"""
FastORM 配置系统测试

测试配置管理、环境变量、配置文件和全局时间戳控制
"""

import os
import tempfile
import json
from pathlib import Path

import pytest

from fastorm.config import (
    FastORMConfig,
    ConfigManager,
    get_config,
    set_config,
    get_setting,
    set_setting,
    generate_config_file,
    validate_config,
)


class TestFastORMConfig:
    """FastORM配置类测试"""

    def test_default_config_values(self):
        """测试默认配置值"""
        config = FastORMConfig()
        
        # 时间戳配置
        assert config.timestamps_enabled is True
        assert config.default_created_at_column == "created_at"
        assert config.default_updated_at_column == "updated_at"
        
        # 数据库配置
        assert config.database_url is None
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.echo_sql is False
        
        # 性能配置
        assert config.query_cache_enabled is True
        assert config.batch_size == 1000
        
        # 开发配置
        assert config.debug is False
        assert config.testing is False


class TestConfigManager:
    """配置管理器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置配置管理器（创建新实例）
        ConfigManager._instance = None

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        assert manager1 is manager2

    def test_get_set_config(self):
        """测试配置获取和设置"""
        manager = ConfigManager()
        
        # 获取默认配置
        config = manager.get_config()
        assert isinstance(config, FastORMConfig)
        assert config.timestamps_enabled is True
        
        # 更新配置
        manager.update_config(timestamps_enabled=False, debug=True)
        
        updated_config = manager.get_config()
        assert updated_config.timestamps_enabled is False
        assert updated_config.debug is True

    def test_get_set_individual_settings(self):
        """测试单个配置项的获取和设置"""
        manager = ConfigManager()
        
        # 测试获取
        assert manager.get('timestamps_enabled') is True
        assert manager.get('nonexistent_key', 'default') == 'default'
        
        # 测试设置
        manager.set('debug', True)
        assert manager.get('debug') is True
        
        # 测试设置不存在的键（应该被忽略）
        manager.set('nonexistent_key', 'value')
        assert manager.get('nonexistent_key') is None

    def test_to_dict(self):
        """测试配置转换为字典"""
        manager = ConfigManager()
        config_dict = manager.to_dict()
        
        assert isinstance(config_dict, dict)
        assert 'timestamps_enabled' in config_dict
        assert 'database_url' in config_dict
        assert config_dict['timestamps_enabled'] is True

    def test_load_from_env(self):
        """测试从环境变量加载配置"""
        # 设置环境变量
        env_vars = {
            'FASTORM_TIMESTAMPS_ENABLED': 'false',
            'FASTORM_DEBUG': 'true',
            'FASTORM_POOL_SIZE': '10',
            'FASTORM_DATABASE_URL': 'sqlite:///test.db',
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            # 创建新的配置管理器实例
            ConfigManager._instance = None
            manager = ConfigManager()
            config = manager.get_config()
            
            assert config.timestamps_enabled is False
            assert config.debug is True
            assert config.pool_size == 10
            assert config.database_url == 'sqlite:///test.db'
            
        finally:
            # 清理环境变量
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]

    def test_load_from_config_file(self):
        """测试从配置文件加载配置"""
        config_data = {
            "timestamps_enabled": False,
            "debug": True,
            "pool_size": 8,
            "query_cache_size": 2000,
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            # 模拟配置文件在当前目录
            original_cwd = os.getcwd()
            temp_dir = os.path.dirname(config_file)
            os.chdir(temp_dir)
            
            # 重命名为fastorm.json
            fastorm_config = os.path.join(temp_dir, 'fastorm.json')
            os.rename(config_file, fastorm_config)
            
            # 创建新的配置管理器实例
            ConfigManager._instance = None
            manager = ConfigManager()
            config = manager.get_config()
            
            assert config.timestamps_enabled is False
            assert config.debug is True
            assert config.pool_size == 8
            assert config.query_cache_size == 2000
            
        finally:
            os.chdir(original_cwd)
            try:
                os.unlink(fastorm_config)
            except FileNotFoundError:
                pass

    def test_save_to_file(self):
        """测试保存配置到文件"""
        manager = ConfigManager()
        manager.update_config(debug=True, pool_size=15)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            manager.save_to_file(config_file)
            
            # 验证文件内容
            with open(config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
            
            assert saved_config['debug'] is True
            assert saved_config['pool_size'] == 15
            assert saved_config['timestamps_enabled'] is True
            
        finally:
            try:
                os.unlink(config_file)
            except FileNotFoundError:
                pass


class TestGlobalConfigFunctions:
    """全局配置函数测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        ConfigManager._instance = None

    def test_get_config(self):
        """测试全局get_config函数"""
        config = get_config()
        assert isinstance(config, FastORMConfig)
        assert config.timestamps_enabled is True

    def test_set_config(self):
        """测试全局set_config函数"""
        set_config(debug=True, pool_size=20)
        
        config = get_config()
        assert config.debug is True
        assert config.pool_size == 20

    def test_get_set_setting(self):
        """测试全局配置项函数"""
        # 测试获取
        assert get_setting('timestamps_enabled') is True
        assert get_setting('nonexistent', 'default') == 'default'
        
        # 测试设置
        set_setting('debug', True)
        assert get_setting('debug') is True


class TestConfigFileGeneration:
    """配置文件生成测试"""

    def test_generate_config_file(self):
        """测试生成配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            generate_config_file(config_file)
            
            # 验证文件存在
            assert os.path.exists(config_file)
            
            # 验证文件内容
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'timestamps_enabled' in content
                assert 'database_url' in content
                assert 'FastORM 配置文件' in content
            
        finally:
            try:
                os.unlink(config_file)
            except FileNotFoundError:
                pass


class TestConfigValidation:
    """配置验证测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        ConfigManager._instance = None

    def test_valid_config(self):
        """测试有效配置"""
        set_config(
            database_url="postgresql://user:pass@localhost/db",
            pool_size=5,
            max_overflow=10,
            batch_size=1000
        )
        
        errors = validate_config()
        assert len(errors) == 0

    def test_invalid_config(self):
        """测试无效配置"""
        set_config(
            database_url="invalid://url",
            pool_size=0,
            max_overflow=-1,
            batch_size=-100
        )
        
        errors = validate_config()
        assert len(errors) > 0
        assert 'database_url' in errors
        assert 'pool_size' in errors
        assert 'max_overflow' in errors
        assert 'batch_size' in errors


class TestTimestampGlobalControl:
    """全局时间戳控制测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        ConfigManager._instance = None

    def test_global_timestamp_control_via_config(self):
        """测试通过配置系统控制全局时间戳"""
        from fastorm import Model
        
        # 默认应该启用
        assert get_setting('timestamps_enabled') is True
        assert Model._get_global_timestamps_enabled() is True
        
        # 通过配置系统关闭
        set_setting('timestamps_enabled', False)
        assert get_setting('timestamps_enabled') is False
        assert Model._get_global_timestamps_enabled() is False
        
        # 重新启用
        set_setting('timestamps_enabled', True)
        assert get_setting('timestamps_enabled') is True
        assert Model._get_global_timestamps_enabled() is True

    def test_model_set_global_timestamps_updates_config(self):
        """测试Model.set_global_timestamps更新配置系统"""
        from fastorm import Model
        
        # 通过Model方法关闭
        Model.set_global_timestamps(False)
        assert get_setting('timestamps_enabled') is False
        
        # 通过Model方法启用
        Model.set_global_timestamps(True)
        assert get_setting('timestamps_enabled') is True 