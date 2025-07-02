
# FastORM 生产环境配置示例

from fastorm.config import set_config

# 基本配置
set_config(
    # 数据库连接（请替换为实际的生产数据库URL）
    database_url="postgresql+asyncpg://user:password@localhost/production_db",
    
    # 生产环境设置
    debug=False,
    echo_sql=False,
    
    # 连接池配置
    pool_size=20,
    max_overflow=30,
    pool_timeout=60,
    
    # 性能优化
    query_cache_enabled=True,
    batch_size=1000,
)

# 安全配置（已自动启用）
# - SQL注入防护: ✅ 已启用
# - 安全审计: ✅ 已启用
# - 参数化查询: ✅ 已强制使用
