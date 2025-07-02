#!/usr/bin/env python3
"""
FastORM 安全扫描脚本

扫描整个项目中的SQL注入风险和其他安全问题。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastorm.security.sql_injection_checker import check_source_code_security


def scan_project_security() -> dict:
    """扫描整个项目的安全问题"""
    
    # 要扫描的目录
    scan_dirs = [
        PROJECT_ROOT / "fastorm",
        PROJECT_ROOT / "tests", 
    ]
    
    results = {
        "total_files": 0,
        "safe_files": 0,
        "risky_files": 0,
        "issues": [],
        "summary": {}
    }
    
    print("🔍 开始FastORM安全扫描...")
    print(f"📁 扫描目录: {[str(d) for d in scan_dirs]}")
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            print(f"⚠️  目录不存在: {scan_dir}")
            continue
            
        # 扫描所有Python文件
        for py_file in scan_dir.rglob("*.py"):
            results["total_files"] += 1
            
            print(f"🔍 扫描: {py_file.relative_to(PROJECT_ROOT)}")
            
            # 检查文件安全性
            security_result = check_source_code_security(str(py_file))
            
            if "error" in security_result:
                print(f"❌ 扫描失败: {security_result['error']}")
                continue
            
            if security_result["status"] == "safe":
                results["safe_files"] += 1
                print("✅ 安全")
            else:
                results["risky_files"] += 1
                print(f"⚠️  发现 {security_result['issues_found']} 个问题")
                
                # 记录问题
                for issue in security_result["issues"]:
                    issue["file"] = str(py_file.relative_to(PROJECT_ROOT))
                    results["issues"].append(issue)
    
    # 生成摘要
    results["summary"] = {
        "total_files": results["total_files"],
        "safe_files": results["safe_files"], 
        "risky_files": results["risky_files"],
        "safety_rate": (
            results["safe_files"] / results["total_files"] * 100
            if results["total_files"] > 0 else 0
        ),
        "high_severity_issues": len([
            issue for issue in results["issues"] 
            if issue.get("severity") == "high"
        ]),
        "sql_injection_risks": len([
            issue for issue in results["issues"]
            if issue.get("type") == "sql_injection_risk"
        ])
    }
    
    return results


def print_security_report(results: dict) -> None:
    """打印安全报告"""
    
    print("\n" + "="*60)
    print("🛡️  FastORM 安全扫描报告")
    print("="*60)
    
    summary = results["summary"]
    
    print(f"📊 扫描统计:")
    print(f"   总文件数: {summary['total_files']}")
    print(f"   安全文件: {summary['safe_files']}")
    print(f"   风险文件: {summary['risky_files']}") 
    print(f"   安全率: {summary['safety_rate']:.1f}%")
    
    print(f"\n🚨 风险统计:")
    print(f"   高危风险: {summary['high_severity_issues']}")
    print(f"   SQL注入风险: {summary['sql_injection_risks']}")
    
    if results["issues"]:
        print(f"\n⚠️  发现的安全问题:")
        
        for issue in results["issues"]:
            severity_icon = "🔴" if issue["severity"] == "high" else "🟡"
            print(f"   {severity_icon} {issue['file']}:{issue['line']}")
            print(f"      {issue['message']}")
            print(f"      类型: {issue['type']}")
    else:
        print(f"\n✅ 恭喜！未发现安全问题")
    
    print("\n" + "="*60)
    
    # 安全建议
    if summary['sql_injection_risks'] > 0:
        print("🔧 安全建议:")
        print("   1. 使用参数化查询代替字符串拼接")
        print("   2. 使用fastorm.security.safe_text()函数")
        print("   3. 避免在SQL中使用f-string和.format()")
        print("   4. 启用SQL安全审计功能")


def main():
    """主函数"""
    print("🛡️  FastORM P0安全修复 - 安全扫描")
    print("基于ThinkORM 4.0设计理念，确保现代如FastAPI的安全标准\n")
    
    # 执行安全扫描
    results = scan_project_security()
    
    # 打印报告
    print_security_report(results)
    
    # 返回适当的退出码
    if results["summary"]["sql_injection_risks"] > 0:
        print("\n❌ 发现SQL注入风险，请立即修复！")
        sys.exit(1)
    else:
        print("\n✅ 安全扫描通过")
        sys.exit(0)


if __name__ == "__main__":
    main() 