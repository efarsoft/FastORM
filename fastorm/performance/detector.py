"""
N+1查询检测器

自动检测N+1查询模式，帮助开发者发现性能问题
"""

import logging
import re
import threading
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta

logger = logging.getLogger(__name__)


@dataclass
class QueryPattern:
    """查询模式"""

    sql_template: str  # SQL模板（参数替换为占位符）
    table_name: str  # 主表名
    count: int = 0  # 出现次数
    examples: list[str] = field(default_factory=list)  # 实际SQL示例
    timestamps: list[datetime] = field(default_factory=list)  # 执行时间


@dataclass
class N1QueryAlert:
    """N+1查询警告"""

    pattern: QueryPattern
    triggered_at: datetime
    description: str
    suggestions: list[str] = field(default_factory=list)
    severity: str = "WARNING"  # WARNING, ERROR, CRITICAL

    @property
    def is_critical(self) -> bool:
        """是否为严重问题"""
        return self.severity == "CRITICAL" or self.pattern.count > 100


class N1Detector:
    """N+1查询检测器"""

    def __init__(self, time_window: int = 60, threshold: int = 10):
        """
        初始化N+1检测器

        Args:
            time_window: 时间窗口（秒），在此时间内的查询会被分析
            threshold: 触发阈值，相似查询超过此数量时发出警告
        """
        self.time_window = time_window
        self.threshold = threshold
        self.patterns: dict[str, QueryPattern] = {}
        self.alerts: list[N1QueryAlert] = []
        self._lock = threading.Lock()
        self._enabled = True

    def normalize_sql(self, sql: str) -> tuple[str, str]:
        """
        标准化SQL语句，提取模式

        Returns:
            (sql_template, table_name)
        """
        # 移除注释和多余空格
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        sql = re.sub(r"--.*", "", sql)
        sql = " ".join(sql.split())

        # 替换参数为占位符
        # 处理不同类型的参数
        sql_template = re.sub(r"\b\d+\b", "?", sql)  # 数字
        sql_template = re.sub(r"'[^']*'", "?", sql_template)  # 字符串
        sql_template = re.sub(r"%\([^)]+\)s", "?", sql_template)  # 命名参数
        sql_template = re.sub(r"\?", "?", sql_template)  # 其他占位符

        # 提取表名
        table_match = re.search(
            r'\bFROM\s+([`"]?)(\w+)\1|\bUPDATE\s+([`"]?)(\w+)\3|\bINTO\s+([`"]?)(\w+)\5',
            sql.upper(),
        )
        table_name = "unknown"
        if table_match:
            # 获取第一个非空的表名匹配组
            for i in range(2, len(table_match.groups()) + 1, 2):
                if table_match.group(i):
                    table_name = table_match.group(i).lower()
                    break

        return sql_template.upper(), table_name

    def analyze_query(self, sql: str, execution_time: datetime | None = None) -> None:
        """分析查询是否为N+1模式"""
        if not self._enabled:
            return

        if execution_time is None:
            execution_time = datetime.now()

        # 标准化SQL
        sql_template, table_name = self.normalize_sql(sql)

        with self._lock:
            # 获取或创建模式
            if sql_template not in self.patterns:
                self.patterns[sql_template] = QueryPattern(
                    sql_template=sql_template, table_name=table_name
                )

            pattern = self.patterns[sql_template]

            # 清理过期的时间戳
            cutoff_time = execution_time - timedelta(seconds=self.time_window)
            pattern.timestamps = [ts for ts in pattern.timestamps if ts > cutoff_time]

            # 添加新的执行记录
            pattern.count = len(pattern.timestamps) + 1
            pattern.timestamps.append(execution_time)

            # 保存SQL示例（最多保留5个）
            if len(pattern.examples) < 5:
                pattern.examples.append(sql)

            # 检查是否达到N+1警告阈值
            if pattern.count >= self.threshold:
                self._trigger_alert(pattern, execution_time)

    def _trigger_alert(self, pattern: QueryPattern, triggered_at: datetime) -> None:
        """触发N+1查询警告"""
        # 检查是否最近已经发出过相同警告（避免重复）
        recent_alerts = [
            alert
            for alert in self.alerts[-10:]  # 检查最近10个警告
            if (
                alert.pattern.sql_template == pattern.sql_template
                and triggered_at - alert.triggered_at < timedelta(minutes=5)
            )
        ]

        if recent_alerts:
            return  # 避免重复警告

        # 生成警告描述和建议
        description = (
            f"检测到疑似N+1查询: 表 '{pattern.table_name}' "
            f"在 {self.time_window} 秒内执行了 {pattern.count} 次相似查询"
        )

        suggestions = self._generate_suggestions(pattern)

        # 确定严重程度
        severity = "WARNING"
        if pattern.count > 50:
            severity = "ERROR"
        if pattern.count > 100:
            severity = "CRITICAL"

        alert = N1QueryAlert(
            pattern=pattern,
            triggered_at=triggered_at,
            description=description,
            suggestions=suggestions,
            severity=severity,
        )

        self.alerts.append(alert)

        # 记录日志
        logger.warning(f"N+1 Query Detected: {description}")

        # 限制警告数量（保留最近1000个）
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

    def _generate_suggestions(self, pattern: QueryPattern) -> list[str]:
        """生成优化建议"""
        suggestions = []

        # 基于SQL模式生成建议
        sql = pattern.sql_template.upper()

        if "SELECT" in sql and "WHERE" in sql:
            suggestions.append("考虑使用 eager loading (with_关系名) 预加载关联数据")
            suggestions.append("检查是否可以用 JOIN 查询替代多次单独查询")

        if "IN (" in sql:
            suggestions.append("考虑批量查询：将多个 IN 查询合并为一个")

        if pattern.count > 50:
            suggestions.append("严重性能问题：考虑添加适当的数据库索引")
            suggestions.append("考虑使用缓存减少数据库访问")

        return suggestions

    def get_alerts(self, severity: str | None = None) -> list[N1QueryAlert]:
        """获取警告列表"""
        alerts = self.alerts.copy()

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)

    def get_patterns(self, min_count: int = 1) -> list[QueryPattern]:
        """获取查询模式列表"""
        with self._lock:
            patterns = [
                pattern
                for pattern in self.patterns.values()
                if pattern.count >= min_count
            ]

        return sorted(patterns, key=lambda x: x.count, reverse=True)

    def clear_alerts(self) -> None:
        """清空警告列表"""
        with self._lock:
            self.alerts.clear()

    def clear_patterns(self) -> None:
        """清空模式统计"""
        with self._lock:
            self.patterns.clear()

    def enable(self) -> None:
        """启用N+1检测"""
        self._enabled = True

    def disable(self) -> None:
        """禁用N+1检测"""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """检查是否已启用"""
        return self._enabled


# 全局N+1检测器实例
_global_detector = N1Detector()


def detect_n1_queries(sql: str, execution_time: datetime | None = None) -> None:
    """便捷的N+1查询检测函数"""
    _global_detector.analyze_query(sql, execution_time)


def get_n1_alerts(severity: str | None = None) -> list[N1QueryAlert]:
    """获取N+1查询警告"""
    return _global_detector.get_alerts(severity)


def get_query_patterns(min_count: int = 1) -> list[QueryPattern]:
    """获取查询模式统计"""
    return _global_detector.get_patterns(min_count)


def get_global_detector() -> N1Detector:
    """获取全局N+1检测器"""
    return _global_detector


def enable_n1_detection() -> None:
    """启用N+1检测"""
    _global_detector.enable()


def disable_n1_detection() -> None:
    """禁用N+1检测"""
    _global_detector.disable()
