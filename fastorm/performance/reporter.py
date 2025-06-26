"""
性能报告生成器

生成详细的性能分析报告，包括统计数据、图表和建议
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict
import logging

from .monitor import PerformanceMonitor, PerformanceStats
from .profiler import QueryInfo, ProfileSession
from .detector import N1QueryAlert, QueryPattern

logger = logging.getLogger(__name__)


class PerformanceReporter:
    """性能报告生成器"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """生成摘要报告"""
        stats = self.monitor.get_current_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_status": {
                "enabled": self.monitor.is_enabled,
                "profiling": self.monitor.is_profiling_enabled,
                "n1_detection": self.monitor.is_n1_detection_enabled
            },
            "query_statistics": {
                "total_queries": stats.total_queries,
                "slow_queries": stats.slow_queries,
                "failed_queries": stats.failed_queries,
                "avg_execution_time": round(stats.avg_execution_time, 4),
                "total_execution_time": round(stats.total_execution_time, 2)
            },
            "n1_alerts": {
                "total_alerts": stats.n1_alerts,
                "critical_alerts": len([
                    alert for alert in stats.latest_alerts 
                    if alert.is_critical
                ])
            },
            "top_queries": [
                {
                    "sql_template": pattern.sql_template[:100] + "...",
                    "table": pattern.table_name,
                    "count": pattern.count
                }
                for pattern in stats.most_frequent_queries[:5]
            ]
        }
    
    def generate_detailed_report(self) -> Dict[str, Any]:
        """生成详细报告"""
        summary = self.generate_summary_report()
        slow_queries = self.monitor.get_slow_queries(10)
        failed_queries = self.monitor.get_failed_queries(10)
        n1_alerts = self.monitor.get_n1_alerts()
        
        report = {
            **summary,
            "slow_queries": [
                {
                    "sql": query.sql[:200] + "...",
                    "duration": round(query.duration or 0, 4),
                    "timestamp": query.start_time.isoformat(),
                    "session_id": query.session_id
                }
                for query in slow_queries
            ],
            "failed_queries": [
                {
                    "sql": query.sql[:200] + "...",
                    "error": query.error,
                    "timestamp": query.start_time.isoformat(),
                    "session_id": query.session_id
                }
                for query in failed_queries
            ],
            "n1_alerts": [
                {
                    "description": alert.description,
                    "severity": alert.severity,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "suggestions": alert.suggestions,
                    "query_count": alert.pattern.count,
                    "table": alert.pattern.table_name
                }
                for alert in n1_alerts[:10]
            ]
        }
        
        return report
    
    def generate_json_report(self, detailed: bool = False) -> str:
        """生成JSON格式报告"""
        if detailed:
            report = self.generate_detailed_report()
        else:
            report = self.generate_summary_report()
        
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def generate_text_report(self, detailed: bool = False) -> str:
        """生成文本格式报告"""
        if detailed:
            data = self.generate_detailed_report()
        else:
            data = self.generate_summary_report()
        
        lines = []
        lines.append("=" * 60)
        lines.append("FastORM Performance Report")
        lines.append("=" * 60)
        lines.append(f"Generated at: {data['timestamp']}")
        lines.append("")
        
        # 监控状态
        status = data['monitoring_status']
        lines.append("Monitoring Status:")
        lines.append(f"  Overall: {'Enabled' if status['enabled'] else 'Disabled'}")
        lines.append(f"  Profiling: {'Enabled' if status['profiling'] else 'Disabled'}")
        lines.append(f"  N+1 Detection: {'Enabled' if status['n1_detection'] else 'Disabled'}")
        lines.append("")
        
        # 查询统计
        stats = data['query_statistics']
        lines.append("Query Statistics:")
        lines.append(f"  Total Queries: {stats['total_queries']}")
        lines.append(f"  Slow Queries: {stats['slow_queries']}")
        lines.append(f"  Failed Queries: {stats['failed_queries']}")
        lines.append(f"  Average Execution Time: {stats['avg_execution_time']}s")
        lines.append(f"  Total Execution Time: {stats['total_execution_time']}s")
        lines.append("")
        
        # N+1警告
        n1_stats = data['n1_alerts']
        lines.append("N+1 Query Alerts:")
        lines.append(f"  Total Alerts: {n1_stats['total_alerts']}")
        lines.append(f"  Critical Alerts: {n1_stats['critical_alerts']}")
        lines.append("")
        
        # 热门查询
        if data['top_queries']:
            lines.append("Top Frequent Queries:")
            for i, query in enumerate(data['top_queries'], 1):
                lines.append(f"  {i}. Table: {query['table']} (Count: {query['count']})")
                lines.append(f"     SQL: {query['sql_template']}")
            lines.append("")
        
        # 详细信息（如果需要）
        if detailed:
            # 慢查询
            if data.get('slow_queries'):
                lines.append("Slow Queries:")
                for i, query in enumerate(data['slow_queries'], 1):
                    lines.append(f"  {i}. Duration: {query['duration']}s")
                    lines.append(f"     SQL: {query['sql']}")
                    lines.append(f"     Time: {query['timestamp']}")
                lines.append("")
            
            # 失败查询
            if data.get('failed_queries'):
                lines.append("Failed Queries:")
                for i, query in enumerate(data['failed_queries'], 1):
                    lines.append(f"  {i}. Error: {query['error']}")
                    lines.append(f"     SQL: {query['sql']}")
                    lines.append(f"     Time: {query['timestamp']}")
                lines.append("")
            
            # N+1警告详情
            if data.get('n1_alerts'):
                lines.append("N+1 Alert Details:")
                for i, alert in enumerate(data['n1_alerts'], 1):
                    lines.append(f"  {i}. {alert['description']}")
                    lines.append(f"     Severity: {alert['severity']}")
                    lines.append(f"     Table: {alert['table']}")
                    lines.append(f"     Query Count: {alert['query_count']}")
                    if alert['suggestions']:
                        lines.append("     Suggestions:")
                        for suggestion in alert['suggestions']:
                            lines.append(f"       - {suggestion}")
                lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def save_report(self, filename: str, format: str = "json", 
                   detailed: bool = False) -> None:
        """保存报告到文件"""
        if format.lower() == "json":
            content = self.generate_json_report(detailed)
        elif format.lower() == "txt":
            content = self.generate_text_report(detailed)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Performance report saved to {filename}")
    
    def print_summary(self) -> None:
        """打印摘要报告到控制台"""
        print(self.generate_text_report(detailed=False))
    
    def print_detailed(self) -> None:
        """打印详细报告到控制台"""
        print(self.generate_text_report(detailed=True))


# 全局报告生成器
from .monitor import GlobalMonitor
_global_reporter = PerformanceReporter(GlobalMonitor)


def generate_report(detailed: bool = False, format: str = "json") -> str:
    """生成性能报告"""
    if format.lower() == "json":
        return _global_reporter.generate_json_report(detailed)
    elif format.lower() == "txt":
        return _global_reporter.generate_text_report(detailed)
    else:
        raise ValueError(f"Unsupported format: {format}")


def save_report(filename: str, format: str = "json", detailed: bool = False) -> None:
    """保存性能报告到文件"""
    _global_reporter.save_report(filename, format, detailed)


def print_performance_summary() -> None:
    """打印性能摘要"""
    _global_reporter.print_summary()


def print_performance_report() -> None:
    """打印详细性能报告"""
    _global_reporter.print_detailed() 