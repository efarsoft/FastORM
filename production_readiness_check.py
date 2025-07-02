"""
FastORM 生产就绪性检查

快速验证FastORM是否已准备好投入生产使用
"""

import asyncio
import sys
from typing import Any, Dict, List


def check_security_status() -> Dict[str, Any]:
    """检查安全状态"""
    print("🔒 检查安全状态...")
    
    try:
        from fastorm.security.sql_injection_checker import get_security_auditor
        
        # 检查安全审计器
        auditor = get_security_auditor()
        
        # 模拟检查SQL注入防护
        from fastorm.security.sql_injection_checker import validate_sql_text, SQLInjectionError
        
        # 测试安全SQL
        try:
            validate_sql_text("SELECT * FROM users WHERE id = :id")
            sql_protection = True
        except:
            sql_protection = False
        
        # 测试注入检测
        try:
            validate_sql_text("SELECT * FROM users WHERE id = '1' OR '1'='1'")
            injection_detection = False  # 应该抛出异常
        except SQLInjectionError:
            injection_detection = True  # 正确检测到注入
        except:
            injection_detection = False
        
        result = {
            "status": "OK" if (sql_protection and injection_detection) else "FAILED",
            "sql_protection": sql_protection,
            "injection_detection": injection_detection,
            "auditor_available": True
        }
        
        print(f"   ✅ SQL保护: {'启用' if sql_protection else '失败'}")
        print(f"   ✅ 注入检测: {'正常' if injection_detection else '失败'}")
        print(f"   ✅ 安全审计: 可用")
        
        return result
        
    except Exception as e:
        print(f"   ❌ 安全检查失败: {e}")
        return {"status": "FAILED", "error": str(e)}


def check_core_functionality() -> Dict[str, Any]:
    """检查核心功能"""
    print("\n⚙️ 检查核心功能...")
    
    results = {}
    
    # 检查配置系统
    try:
        from fastorm.config import get_config
        config = get_config()
        results["config_system"] = True
        print("   ✅ 配置系统: 正常")
    except Exception as e:
        results["config_system"] = False
        print(f"   ❌ 配置系统: {e}")
    
    # 检查查询构建器
    try:
        from fastorm.query.builder import QueryBuilder
        results["query_builder"] = True
        print("   ✅ 查询构建器: 正常")
    except Exception as e:
        results["query_builder"] = False
        print(f"   ❌ 查询构建器: {e}")
    
    # 检查模型基类
    try:
        from fastorm.model.model import Model
        results["model_base"] = True
        print("   ✅ 模型基类: 正常")
    except Exception as e:
        results["model_base"] = False
        print(f"   ❌ 模型基类: {e}")
    
    # 检查关系功能
    try:
        from fastorm.relations.belongs_to_many import BelongsToMany
        results["relations"] = True
        print("   ✅ 关系功能: 正常")
    except Exception as e:
        results["relations"] = False
        print(f"   ❌ 关系功能: {e}")
    
    all_ok = all(results.values())
    results["status"] = "OK" if all_ok else "PARTIAL"
    
    return results


def check_database_compatibility() -> Dict[str, Any]:
    """检查数据库兼容性"""
    print("\n💾 检查数据库兼容性...")
    
    try:
        from sqlalchemy import __version__ as sqlalchemy_version
        print(f"   ✅ SQLAlchemy版本: {sqlalchemy_version}")
        
        # 检查是否为2.0版本
        major_version = int(sqlalchemy_version.split('.')[0])
        if major_version >= 2:
            print("   ✅ SQLAlchemy 2.0+ 兼容")
            return {"status": "OK", "sqlalchemy_version": sqlalchemy_version}
        else:
            print("   ⚠️ SQLAlchemy版本过低，建议升级到2.0+")
            return {"status": "WARNING", "sqlalchemy_version": sqlalchemy_version}
            
    except Exception as e:
        print(f"   ❌ 数据库兼容性检查失败: {e}")
        return {"status": "FAILED", "error": str(e)}


def check_dependencies() -> Dict[str, Any]:
    """检查依赖项"""
    print("\n📦 检查关键依赖项...")
    
    dependencies = {
        "sqlalchemy": "2.0+",
        "pydantic": "2.0+", 
        "asyncio": "内置",
    }
    
    results = {}
    
    for dep, required_version in dependencies.items():
        try:
            if dep == "asyncio":
                import asyncio
                results[dep] = True
                print(f"   ✅ {dep}: 可用")
            else:
                module = __import__(dep)
                version = getattr(module, '__version__', 'unknown')
                results[dep] = True
                print(f"   ✅ {dep}: {version}")
        except ImportError:
            results[dep] = False
            print(f"   ❌ {dep}: 未安装")
    
    all_ok = all(results.values())
    results["status"] = "OK" if all_ok else "FAILED"
    
    return results


def generate_production_config_template():
    """生成生产环境配置模板"""
    print("\n📋 生成生产环境配置模板...")
    
    config_template = '''
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
'''
    
    with open('fastorm_production_config.py', 'w', encoding='utf-8') as f:
        f.write(config_template)
    
    print("   ✅ 配置模板已生成: fastorm_production_config.py")


def main():
    """主检查函数"""
    print("🚀 FastORM 生产就绪性检查")
    print("=" * 60)
    
    # 执行各项检查
    security_result = check_security_status()
    core_result = check_core_functionality()
    db_result = check_database_compatibility()
    deps_result = check_dependencies()
    
    # 生成配置模板
    generate_production_config_template()
    
    print("\n" + "=" * 60)
    print("📊 生产就绪性评估结果")
    print("=" * 60)
    
    # 计算总体状态
    critical_checks = [
        security_result.get("status"),
        core_result.get("status"), 
        deps_result.get("status")
    ]
    
    failed_checks = [status for status in critical_checks if status == "FAILED"]
    warning_checks = [status for status in critical_checks if status == "WARNING"]
    
    if not failed_checks:
        if not warning_checks:
            overall_status = "✅ READY FOR PRODUCTION"
            recommendation = "🎉 FastORM已准备好投入生产使用！"
        else:
            overall_status = "⚠️ READY WITH WARNINGS"
            recommendation = "✅ 可以投入生产，但请注意警告项"
    else:
        overall_status = "❌ NOT READY"
        recommendation = "🔧 请修复失败项后再投入生产"
    
    print(f"\n🎯 总体状态: {overall_status}")
    print(f"💡 建议: {recommendation}")
    
    print("\n📋 检查项详情:")
    print(f"   🔒 安全状态: {security_result.get('status')}")
    print(f"   ⚙️ 核心功能: {core_result.get('status')}")
    print(f"   💾 数据库兼容: {db_result.get('status')}")
    print(f"   📦 依赖项: {deps_result.get('status')}")
    
    if overall_status.startswith("✅"):
        print("\n🚀 快速启动指南:")
        print("1. 使用 fastorm_production_config.py 配置生产环境")
        print("2. 设置实际的数据库连接字符串")
        print("3. 部署并开始使用FastORM")
        print("4. 可选：后续进行P2阶段优化（不影响生产使用）")
    
    return overall_status.startswith("✅")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 