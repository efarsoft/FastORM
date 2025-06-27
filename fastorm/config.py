"""
FastORM 配置系统

提供灵活的配置管理，支持配置文件、环境变量和代码配置
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
import json


@dataclass
class FastORMConfig:
    """FastORM 配置类"""
    
    # =================================================================
    # 时间戳配置
    # =================================================================
    
    # 全局时间戳开关
    timestamps_enabled: bool = True
    
    # 默认时间戳字段名
    default_created_at_column: str = "created_at"
    default_updated_at_column: str = "updated_at"
    
    # =================================================================
    # 数据库配置
    # =================================================================
    
    # 默认数据库连接
    database_url: Optional[str] = None
    
    # 连接池配置
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # SQL日志
    echo_sql: bool = False
    
    # =================================================================
    # 性能配置
    # =================================================================
    
    # 查询缓存
    query_cache_enabled: bool = True
    query_cache_size: int = 1000
    
    # 批量操作
    batch_size: int = 1000
    
    # N+1查询检测
    n1_detection_enabled: bool = True
    
    # =================================================================
    # 开发配置
    # =================================================================
    
    # 调试模式
    debug: bool = False
    
    # 测试模式
    testing: bool = False
    
    # 自动创建表
    auto_create_tables: bool = False
    
    # =================================================================
    # 序列化配置
    # =================================================================
    
    # 默认序列化格式
    default_serialization_format: str = "json"
    
    # 日期时间格式
    datetime_format: str = "iso"
    
    # =================================================================
    # 验证配置
    # =================================================================
    
    # 严格验证模式
    strict_validation: bool = True
    
    # 自动验证
    auto_validation: bool = True


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _config: FastORMConfig = field(default_factory=FastORMConfig)
    
    def __new__(cls) -> 'ConfigManager':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = FastORMConfig()
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """加载配置"""
        # 1. 从环境变量加载
        self._load_from_env()
        
        # 2. 从配置文件加载
        self._load_from_file()
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        env_mappings = {
            'FASTORM_TIMESTAMPS_ENABLED': ('timestamps_enabled', bool),
            'FASTORM_DATABASE_URL': ('database_url', str),
            'FASTORM_ECHO_SQL': ('echo_sql', bool),
            'FASTORM_DEBUG': ('debug', bool),
            'FASTORM_TESTING': ('testing', bool),
            'FASTORM_POOL_SIZE': ('pool_size', int),
            'FASTORM_MAX_OVERFLOW': ('max_overflow', int),
            'FASTORM_QUERY_CACHE_ENABLED': ('query_cache_enabled', bool),
            'FASTORM_BATCH_SIZE': ('batch_size', int),
            'FASTORM_AUTO_CREATE_TABLES': ('auto_create_tables', bool),
            'FASTORM_STRICT_VALIDATION': ('strict_validation', bool),
        }
        
        for env_key, (attr_name, attr_type) in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                try:
                    if attr_type == bool:
                        value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif attr_type == int:
                        value = int(env_value)
                    else:
                        value = env_value
                    
                    setattr(self._config, attr_name, value)
                except (ValueError, TypeError):
                    pass  # 忽略无效的环境变量值
    
    def _load_from_file(self) -> None:
        """从配置文件加载配置"""
        config_paths = [
            Path.cwd() / "fastorm.json",
            Path.cwd() / "fastorm.config.json",
            Path.cwd() / ".fastorm.json",
            Path.home() / ".fastorm" / "config.json",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        self._update_config_from_dict(config_data)
                    break
                except (json.JSONDecodeError, IOError):
                    continue
    
    def _update_config_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """从字典更新配置"""
        for key, value in config_dict.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    def get_config(self) -> FastORMConfig:
        """获取当前配置"""
        return self._config
    
    def update_config(self, **kwargs: Any) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self._config, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            field.name: getattr(self._config, field.name)
            for field in self._config.__dataclass_fields__.values()
        }
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """保存配置到文件"""
        config_dict = self.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)


# =============================================================================
# 全局配置实例
# =============================================================================

# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷的配置访问函数
def get_config() -> FastORMConfig:
    """获取全局配置"""
    return config_manager.get_config()

def set_config(**kwargs: Any) -> None:
    """设置全局配置"""
    config_manager.update_config(**kwargs)

def get_setting(key: str, default: Any = None) -> Any:
    """获取配置项"""
    return config_manager.get(key, default)

def set_setting(key: str, value: Any) -> None:
    """设置配置项"""
    config_manager.set(key, value)


# =============================================================================
# 配置文件示例生成
# =============================================================================

def generate_config_file(file_path: Union[str, Path] = "fastorm.json") -> None:
    """生成示例配置文件"""
    
    example_config = {
        "// FastORM 配置文件": "支持JSON格式，// 开头的为注释",
        
        "// 时间戳配置": "",
        "timestamps_enabled": True,
        "default_created_at_column": "created_at", 
        "default_updated_at_column": "updated_at",
        
        "// 数据库配置": "",
        "database_url": "postgresql+asyncpg://user:pass@localhost/dbname",
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "echo_sql": False,
        
        "// 性能配置": "",
        "query_cache_enabled": True,
        "query_cache_size": 1000,
        "batch_size": 1000,
        "n1_detection_enabled": True,
        
        "// 开发配置": "",
        "debug": False,
        "testing": False,
        "auto_create_tables": False,
        
        "// 序列化配置": "",
        "default_serialization_format": "json",
        "datetime_format": "iso",
        
        "// 验证配置": "",
        "strict_validation": True,
        "auto_validation": True
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2, ensure_ascii=False)


# =============================================================================
# 配置装饰器
# =============================================================================

def require_config(config_key: str, error_message: str = None):
    """配置项必需装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not get_setting(config_key):
                message = error_message or f"配置项 {config_key} 未设置或为False"
                raise ValueError(message)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# 配置验证
# =============================================================================

def validate_config() -> Dict[str, str]:
    """验证配置合法性"""
    errors = {}
    config = get_config()
    
    # 验证数据库URL格式
    if config.database_url:
        if not any(config.database_url.startswith(scheme) 
                  for scheme in ['sqlite', 'postgresql', 'mysql']):
            errors['database_url'] = "不支持的数据库类型"
    
    # 验证连接池配置
    if config.pool_size <= 0:
        errors['pool_size'] = "连接池大小必须大于0"
    
    if config.max_overflow < 0:
        errors['max_overflow'] = "最大溢出连接数不能小于0"
    
    # 验证批量大小
    if config.batch_size <= 0:
        errors['batch_size'] = "批量大小必须大于0"
    
    return errors 