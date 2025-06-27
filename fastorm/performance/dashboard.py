"""
性能监控仪表板

提供实时性能监控界面和数据可视化功能：
- 实时指标展示
- 历史趋势分析
- 警告和建议
- 交互式控制台
"""

import json
import logging
import time
from datetime import datetime
from datetime import timedelta
from typing import Any

from .metrics import MetricsCollector
from .metrics import global_metrics_collector
from .monitor import PerformanceMonitor
from .reporter import PerformanceReporter

logger = logging.getLogger(__name__)


class PerformanceDashboard:
    """性能监控仪表板"""

    def __init__(
        self,
        monitor: PerformanceMonitor | None = None,
        metrics_collector: MetricsCollector | None = None,
    ):
        """
        初始化仪表板

        Args:
            monitor: 性能监控器
            metrics_collector: 指标收集器
        """
        self.monitor = monitor or PerformanceMonitor()
        self.metrics_collector = metrics_collector or global_metrics_collector
        self.reporter = PerformanceReporter(self.monitor)
        self._refresh_interval = 5  # 刷新间隔（秒）
        self._running = False

    def start_dashboard(self, refresh_interval: int = 5) -> None:
        """启动仪表板"""
        self._refresh_interval = refresh_interval
        self._running = True

        # 启动监控组件
        if not self.monitor.is_enabled:
            self.monitor.start_monitoring()

        if not self.metrics_collector._collecting:
            self.metrics_collector.start_collection()

        print("🚀 FastORM 性能监控仪表板启动")
        print("=" * 80)
        print("按 Ctrl+C 退出仪表板")
        print("=" * 80)

        try:
            while self._running:
                self._refresh_display()
                time.sleep(self._refresh_interval)
        except KeyboardInterrupt:
            print("\n\n👋 正在关闭仪表板...")
            self.stop_dashboard()

    def stop_dashboard(self) -> None:
        """停止仪表板"""
        self._running = False
        print("✅ 仪表板已关闭")

    def _refresh_display(self) -> None:
        """刷新显示内容"""
        # 清屏（仅在终端环境中有效）
        try:
            import os

            os.system("cls" if os.name == "nt" else "clear")
        except:
            print("\n" * 50)  # 简单的清屏替代方案

        # 显示头部信息
        self._display_header()

        # 显示各种指标
        self._display_query_stats()
        self._display_system_metrics()
        self._display_alerts()
        self._display_top_queries()

        # 显示底部信息
        self._display_footer()

    def _display_header(self) -> None:
        """显示头部信息"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("🔥 FastORM 性能监控仪表板")
        print("=" * 80)
        print(f"📅 当前时间: {now}")
        print(f"🔄 刷新间隔: {self._refresh_interval}秒")
        print(f"📊 监控状态: {'✅ 运行中' if self.monitor.is_enabled else '❌ 已停止'}")
        print("=" * 80)

    def _display_query_stats(self) -> None:
        """显示查询统计"""
        stats = self.monitor.get_current_stats()

        print("📊 查询统计")
        print("-" * 40)
        print(f"📈 总查询数: {stats.total_queries:,}")
        print(f"🐌 慢查询数: {stats.slow_queries:,}")
        print(f"❌ 失败查询: {stats.failed_queries:,}")
        print(f"⏱️  平均执行时间: {stats.avg_execution_time:.3f}s")
        print(f"⏱️  总执行时间: {stats.total_execution_time:.2f}s")

        # 查询成功率
        if stats.total_queries > 0:
            success_rate = (
                stats.total_queries - stats.failed_queries
            ) / stats.total_queries
            print(f"✅ 成功率: {success_rate:.2%}")

        print()

    def _display_system_metrics(self) -> None:
        """显示系统指标"""
        metrics_summary = self.metrics_collector.get_current_metrics_summary()

        print("💻 系统指标")
        print("-" * 40)

        # 内存指标
        if metrics_summary.get("memory"):
            memory = metrics_summary["memory"]
            print(
                f"🧠 内存使用: {memory['usage_percent']:.1f}% ({memory['used_mb']:.0f}MB)"
            )
            if memory["swap_usage_percent"] > 0:
                print(f"💾 交换区: {memory['swap_usage_percent']:.1f}%")

        # CPU指标
        if metrics_summary.get("system"):
            system = metrics_summary["system"]
            print(f"⚡ CPU使用: {system['cpu_percent']:.1f}% ({system['cpu_count']}核)")

            if system.get("load_average"):
                load_avg = system["load_average"]
                print(
                    f"📈 负载: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
                )

        # 缓存指标
        if metrics_summary.get("cache"):
            cache = metrics_summary["cache"]
            print(f"🗄️  缓存命中率: {cache['hit_ratio']:.2%}")
            print(f"📦 缓存大小: {cache['cache_size']:,}")

        # 连接池指标
        if metrics_summary.get("connection_pool"):
            pool = metrics_summary["connection_pool"]
            print(f"🔗 连接池: {pool['checked_out']}/{pool['pool_size']} (使用中/总数)")
            if pool["overflow"] > 0:
                print(f"⚠️  溢出连接: {pool['overflow']}")

        print()

    def _display_alerts(self) -> None:
        """显示警告信息"""
        # N+1查询警告
        n1_alerts = self.monitor.get_n1_alerts()
        recent_alerts = [
            alert
            for alert in n1_alerts
            if datetime.now() - alert.triggered_at < timedelta(minutes=30)
        ]

        # 系统健康报告
        health_report = self.metrics_collector.generate_health_report()

        print("🚨 警告和提醒")
        print("-" * 40)

        # 显示系统健康状态
        status_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "🔴"}
        status = health_report["health_status"]
        print(f"{status_emoji.get(status, '❓')} 系统状态: {status.upper()}")

        # 显示警告
        all_warnings = health_report.get("warnings", [])
        if recent_alerts:
            all_warnings.extend(
                [f"N+1查询: {alert.description}" for alert in recent_alerts[:3]]
            )

        if all_warnings:
            print("警告列表:")
            for warning in all_warnings[:5]:  # 只显示前5个
                print(f"  ⚠️  {warning}")
        else:
            print("🎉 无警告")

        print()

    def _display_top_queries(self) -> None:
        """显示热门查询"""
        stats = self.monitor.get_current_stats()

        print("🔝 热门查询")
        print("-" * 40)

        if stats.most_frequent_queries:
            for i, pattern in enumerate(stats.most_frequent_queries[:5], 1):
                # 截断SQL显示
                sql_preview = pattern.sql_template[:60]
                if len(pattern.sql_template) > 60:
                    sql_preview += "..."

                print(f"{i}. 表: {pattern.table_name} (执行 {pattern.count} 次)")
                print(f"   SQL: {sql_preview}")
        else:
            print("暂无查询数据")

        print()

    def _display_footer(self) -> None:
        """显示底部信息"""
        print("=" * 80)
        print("💡 提示: 按 Ctrl+C 退出监控")
        print("🔄 自动刷新中...")

    def generate_live_report(self) -> dict[str, Any]:
        """生成实时报告"""
        query_stats = self.monitor.get_current_stats()
        metrics_summary = self.metrics_collector.get_current_metrics_summary()
        health_report = self.metrics_collector.generate_health_report()
        n1_alerts = self.monitor.get_n1_alerts()

        return {
            "timestamp": datetime.now().isoformat(),
            "query_statistics": {
                "total_queries": query_stats.total_queries,
                "slow_queries": query_stats.slow_queries,
                "failed_queries": query_stats.failed_queries,
                "avg_execution_time": query_stats.avg_execution_time,
                "total_execution_time": query_stats.total_execution_time,
            },
            "system_metrics": metrics_summary,
            "health_status": health_report["health_status"],
            "warnings": health_report.get("warnings", []),
            "n1_alerts_count": len(
                [
                    alert
                    for alert in n1_alerts
                    if datetime.now() - alert.triggered_at < timedelta(minutes=30)
                ]
            ),
            "top_queries": [
                {
                    "table": pattern.table_name,
                    "count": pattern.count,
                    "sql_preview": pattern.sql_template[:100],
                }
                for pattern in query_stats.most_frequent_queries[:5]
            ],
        }

    def export_dashboard_data(self, filename: str) -> None:
        """导出仪表板数据"""
        data = self.generate_live_report()

        # 添加历史数据
        data["historical_data"] = {
            "memory_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "usage_percent": m.memory_percent,
                    "used_mb": m.used_memory,
                }
                for m in self.metrics_collector.get_memory_metrics(60)
            ],
            "system_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "cpu_percent": m.cpu_percent,
                    "load_average": m.load_average,
                }
                for m in self.metrics_collector.get_system_metrics(60)
            ],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ 仪表板数据已导出到: {filename}")


class ConsoleCommands:
    """控制台命令处理"""

    def __init__(self, dashboard: PerformanceDashboard):
        self.dashboard = dashboard
        self.commands = {
            "help": self._help,
            "status": self._status,
            "report": self._report,
            "clear": self._clear,
            "export": self._export,
            "alerts": self._alerts,
            "queries": self._queries,
            "metrics": self._metrics,
            "quit": self._quit,
        }

    def process_command(self, command: str) -> bool:
        """
        处理控制台命令

        Returns:
            bool: False表示退出命令
        """
        parts = command.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd in self.commands:
            return self.commands[cmd](args)
        else:
            print(f"❌ 未知命令: {cmd}，输入 'help' 查看帮助")
            return True

    def _help(self, args: list[str]) -> bool:
        """显示帮助"""
        print("\n📖 可用命令:")
        print("  help     - 显示此帮助信息")
        print("  status   - 显示监控状态")
        print("  report   - 生成性能报告")
        print("  clear    - 清空监控数据")
        print("  export   - 导出数据到文件")
        print("  alerts   - 显示警告列表")
        print("  queries  - 显示查询统计")
        print("  metrics  - 显示系统指标")
        print("  quit     - 退出仪表板")
        return True

    def _status(self, args: list[str]) -> bool:
        """显示状态"""
        monitor_status = "运行中" if self.dashboard.monitor.is_enabled else "已停止"
        collector_status = (
            "运行中" if self.dashboard.metrics_collector._collecting else "已停止"
        )

        print("\n📊 监控状态:")
        print(f"  性能监控器: {monitor_status}")
        print(f"  指标收集器: {collector_status}")
        return True

    def _report(self, args: list[str]) -> bool:
        """生成报告"""
        detailed = "detailed" in args
        report = self.dashboard.reporter.generate_text_report(detailed=detailed)
        print(f"\n{report}")
        return True

    def _clear(self, args: list[str]) -> bool:
        """清空数据"""
        self.dashboard.monitor.clear_monitoring_data()
        self.dashboard.metrics_collector.clear_metrics()
        print("\n✅ 监控数据已清空")
        return True

    def _export(self, args: list[str]) -> bool:
        """导出数据"""
        filename = args[0] if args else f"dashboard_data_{int(time.time())}.json"
        self.dashboard.export_dashboard_data(filename)
        return True

    def _alerts(self, args: list[str]) -> bool:
        """显示警告"""
        health_report = self.dashboard.metrics_collector.generate_health_report()
        n1_alerts = self.dashboard.monitor.get_n1_alerts()

        print(f"\n🚨 系统健康状态: {health_report['health_status']}")

        warnings = health_report.get("warnings", [])
        if warnings:
            print("系统警告:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")

        if n1_alerts:
            print(f"\nN+1查询警告 ({len(n1_alerts)} 个):")
            for alert in n1_alerts[:5]:
                print(f"  🚨 {alert.description}")

        if not warnings and not n1_alerts:
            print("🎉 无警告")

        return True

    def _queries(self, args: list[str]) -> bool:
        """显示查询统计"""
        stats = self.dashboard.monitor.get_current_stats()

        print("\n📊 查询统计:")
        print(f"  总查询数: {stats.total_queries:,}")
        print(f"  慢查询数: {stats.slow_queries:,}")
        print(f"  失败查询: {stats.failed_queries:,}")
        print(f"  平均时间: {stats.avg_execution_time:.3f}s")

        if stats.most_frequent_queries:
            print("\n🔝 热门查询:")
            for i, pattern in enumerate(stats.most_frequent_queries[:3], 1):
                print(f"  {i}. {pattern.table_name} ({pattern.count} 次)")

        return True

    def _metrics(self, args: list[str]) -> bool:
        """显示系统指标"""
        summary = self.dashboard.metrics_collector.get_current_metrics_summary()

        print("\n💻 系统指标:")

        if summary.get("memory"):
            memory = summary["memory"]
            print(f"  内存: {memory['usage_percent']:.1f}% ({memory['used_mb']:.0f}MB)")

        if summary.get("system"):
            system = summary["system"]
            print(f"  CPU: {system['cpu_percent']:.1f}%")

        if summary.get("cache"):
            cache = summary["cache"]
            print(f"  缓存命中率: {cache['hit_ratio']:.2%}")

        return True

    def _quit(self, args: list[str]) -> bool:
        """退出"""
        return False


def start_interactive_dashboard(monitor: PerformanceMonitor | None = None) -> None:
    """启动交互式仪表板"""
    dashboard = PerformanceDashboard(monitor)
    commands = ConsoleCommands(dashboard)

    print("🚀 FastORM 交互式性能监控仪表板")
    print("输入 'help' 查看可用命令，输入 'quit' 退出")
    print("=" * 60)

    # 启动监控
    dashboard.monitor.start_monitoring()
    dashboard.metrics_collector.start_collection()

    try:
        while True:
            try:
                command = input("\n💻 fastorm> ").strip()
                if not command:
                    continue

                if not commands.process_command(command):
                    break
            except KeyboardInterrupt:
                print("\n\n👋 正在退出...")
                break
            except EOFError:
                print("\n\n👋 正在退出...")
                break
    finally:
        dashboard.stop_dashboard()


def start_realtime_dashboard(
    monitor: PerformanceMonitor | None = None, refresh_interval: int = 5
) -> None:
    """启动实时仪表板"""
    dashboard = PerformanceDashboard(monitor)
    dashboard.start_dashboard(refresh_interval)
