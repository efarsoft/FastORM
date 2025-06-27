# FastORM 性能监控系统完整指南

## 概述

FastORM提供了一套完整的性能监控系统，用于实时监控数据库查询性能、系统资源使用情况以及自动检测常见的性能问题。本系统基于现代Python技术栈，完全兼容SQLAlchemy 2.0和异步操作。

## 🏗️ 系统架构

### 核心组件

```
性能监控系统
├── 🔍 查询性能分析器 (QueryProfiler)
├── 📊 性能监控器 (PerformanceMonitor)  
├── 🚨 N+1查询检测器 (N1Detector)
├── 📋 性能报告生成器 (PerformanceReporter)
├── 📈 指标收集器 (MetricsCollector)
└── 🖥️ 监控仪表板 (PerformanceDashboard)
```

### 功能特性

- ✅ **查询性能分析** - 详细的SQL执行统计和时间分析
- ✅ **N+1查询检测** - 自动发现并警告N+1查询模式
- ✅ **系统资源监控** - CPU、内存、磁盘、网络使用情况
- ✅ **连接池监控** - 数据库连接池状态和性能
- ✅ **缓存性能监控** - 缓存命中率和内存使用
- ✅ **健康状况检查** - 自动健康评估和警告
- ✅ **实时监控仪表板** - 可视化性能监控界面
- ✅ **多格式报告** - JSON、文本格式的性能报告

## 🚀 快速开始

### 基础监控

```python
from fastorm.performance import start_monitoring, stop_monitoring, get_performance_stats

# 启动监控
start_monitoring()

# 执行你的数据库操作
# ...

# 获取性能统计
stats = get_performance_stats()
print(f"总查询数: {stats.total_queries}")
print(f"慢查询数: {stats.slow_queries}")
print(f"平均执行时间: {stats.avg_execution_time:.3f}s")

# 停止监控
stop_monitoring()
```

### 完整监控（包含系统指标）

```python
from fastorm.performance import (
    start_monitoring, start_metrics_collection,
    get_current_metrics, get_health_report
)

# 启动完整监控
start_monitoring()
start_metrics_collection(interval=60)  # 每60秒收集一次指标

# 获取系统指标
metrics = get_current_metrics()
print(f"内存使用: {metrics['memory']['usage_percent']}%")
print(f"CPU使用: {metrics['system']['cpu_percent']}%")

# 获取健康报告
health = get_health_report()
print(f"系统状态: {health['health_status']}")
```

### 启动监控仪表板

```python
from fastorm.performance import start_interactive_dashboard

# 启动交互式仪表板
start_interactive_dashboard()
```

## 📊 详细功能说明

### 1. 查询性能分析器 (QueryProfiler)

用于分析单个会话或操作的查询性能。

```python
from fastorm.performance import QueryProfiler

profiler = QueryProfiler(
    slow_query_threshold=0.1,  # 慢查询阈值（秒）
    enable_stack_trace=True    # 启用堆栈跟踪
)

# 使用上下文管理器
with profiler.profile("user_operations") as session_profile:
    # 执行数据库操作
    async with async_session() as session:
        result = await session.execute(text("SELECT * FROM users"))
        users = result.fetchall()

# 查看分析结果
print(f"总查询数: {session_profile.total_queries}")
print(f"慢查询数: {session_profile.slow_queries}")
print(f"平均查询时间: {session_profile.avg_query_time:.3f}s")

# 查看具体查询详情
for query in session_profile.queries:
    print(f"SQL: {query.sql}")
    print(f"执行时间: {query.duration:.3f}s")
    print(f"是否慢查询: {query.is_slow}")
```

### 2. N+1查询检测器 (N1Detector)

自动检测N+1查询模式并提供优化建议。

```python
from fastorm.performance import N1Detector

detector = N1Detector(
    time_window=60,  # 时间窗口（秒）
    threshold=5      # 触发阈值
)

# 分析查询
detector.analyze_query("SELECT * FROM users")
for user_id in range(1, 10):
    detector.analyze_query(f"SELECT * FROM posts WHERE user_id = {user_id}")

# 检查警告
alerts = detector.get_alerts()
for alert in alerts:
    print(f"警告: {alert.description}")
    print("优化建议:")
    for suggestion in alert.suggestions:
        print(f"  - {suggestion}")
```

### 3. 系统指标收集器 (MetricsCollector)

收集系统级性能指标。

```python
from fastorm.performance import (
    start_metrics_collection, get_current_metrics,
    record_connection_pool_metrics, record_cache_performance
)

# 启动指标收集
start_metrics_collection(interval=30)

# 记录连接池指标
record_connection_pool_metrics(
    pool_size=20,
    checked_out=5,
    checked_in=15
)

# 记录缓存性能
record_cache_performance(
    total_requests=1000,
    cache_hits=850,
    cache_size=500
)

# 获取当前指标
metrics = get_current_metrics()
```

### 4. 监控仪表板 (PerformanceDashboard)

提供实时监控界面。

#### 实时仪表板

```python
from fastorm.performance import start_realtime_dashboard

# 启动实时仪表板（自动刷新）
start_realtime_dashboard(refresh_interval=5)
```

#### 交互式仪表板

```python
from fastorm.performance import start_interactive_dashboard

# 启动交互式仪表板（支持命令）
start_interactive_dashboard()

# 可用命令:
# help     - 显示帮助
# status   - 显示监控状态
# report   - 生成性能报告
# clear    - 清空监控数据
# export   - 导出数据到文件
# alerts   - 显示警告列表
# queries  - 显示查询统计
# metrics  - 显示系统指标
# quit     - 退出仪表板
```

### 5. 性能报告生成器 (PerformanceReporter)

生成详细的性能分析报告。

```python
from fastorm.performance import PerformanceMonitor, PerformanceReporter

monitor = PerformanceMonitor()
monitor.start_monitoring()

reporter = PerformanceReporter(monitor)

# 生成摘要报告
summary = reporter.generate_summary_report()

# 生成详细报告
detailed = reporter.generate_detailed_report()

# 生成文本格式报告
text_report = reporter.generate_text_report(detailed=True)
print(text_report)

# 保存报告到文件
reporter.save_report("performance_report.json", format="json", detailed=True)
reporter.save_report("performance_report.txt", format="text", detailed=True)
```

## 🎯 使用场景

### 开发环境

```python
# 启用完整监控和调试功能
from fastorm.performance import (
    start_monitoring, start_metrics_collection, start_interactive_dashboard
)

start_monitoring()
start_metrics_collection(interval=30)

# 可选：启动交互式仪表板进行实时监控
# start_interactive_dashboard()
```

### 生产环境

```python
# 轻量级监控模式
from fastorm.performance import start_monitoring, get_performance_stats

start_monitoring()

# 定期检查性能统计
import asyncio

async def periodic_health_check():
    while True:
        stats = get_performance_stats()
        if stats.slow_queries > 10:
            logger.warning(f"检测到 {stats.slow_queries} 个慢查询")
        
        await asyncio.sleep(300)  # 每5分钟检查一次

# 启动后台健康检查
asyncio.create_task(periodic_health_check())
```

### 性能调优

```python
from fastorm.performance import QueryProfiler, N1Detector

# 性能分析
profiler = QueryProfiler(slow_query_threshold=0.05)
detector = N1Detector(threshold=3)

with profiler.profile("optimization_test") as session_profile:
    # 执行需要优化的操作
    await your_database_operations()

# 分析结果
print(f"慢查询数: {session_profile.slow_queries}")
alerts = detector.get_alerts()
for alert in alerts:
    print(f"优化建议: {alert.suggestions}")
```

## ⚠️ 注意事项

### 性能影响

- 监控系统本身会产生少量性能开销
- 建议在生产环境中使用较长的指标收集间隔
- 可根据需要选择性启用监控功能

### 内存使用

- 系统会保留一定量的历史数据用于分析
- 默认保留24小时的指标数据
- 可通过清理函数手动清空数据

```python
from fastorm.performance import clear_monitoring_data
clear_monitoring_data()
```

### 依赖要求

```bash
pip install psutil  # 用于系统资源监控
```

## 📈 最佳实践

### 1. 分层监控策略

```python
# 基础层：总是启用
start_monitoring()

# 指标层：生产环境使用较长间隔
start_metrics_collection(interval=300)  # 5分钟

# 调试层：仅开发环境
if DEBUG:
    start_interactive_dashboard()
```

### 2. 告警集成

```python
from fastorm.performance import get_health_report, get_n1_alerts

def check_performance_health():
    health = get_health_report()
    alerts = get_n1_alerts()
    
    if health['health_status'] == 'critical':
        send_alert(f"系统状态严重: {health['warnings']}")
    
    if len(alerts) > 5:
        send_alert(f"检测到 {len(alerts)} 个N+1查询问题")
```

### 3. 定期报告

```python
import schedule
from fastorm.performance import PerformanceReporter

def generate_daily_report():
    reporter = PerformanceReporter()
    report = reporter.generate_text_report(detailed=True)
    
    # 发送邮件或保存文件
    save_report_to_file(report)

# 每天生成报告
schedule.every().day.at("23:59").do(generate_daily_report)
```

## 🔧 高级配置

### 自定义慢查询阈值

```python
from fastorm.performance import QueryProfiler

profiler = QueryProfiler(
    slow_query_threshold=0.1,      # 100ms
    enable_stack_trace=True,       # 启用堆栈跟踪
    max_query_history=1000,        # 最大查询历史
    session_timeout=3600           # 会话超时（秒）
)
```

### 自定义N+1检测参数

```python
from fastorm.performance import N1Detector

detector = N1Detector(
    time_window=120,    # 时间窗口2分钟
    threshold=8,        # 阈值8次
)
```

### 自定义指标收集

```python
from fastorm.performance import MetricsCollector

collector = MetricsCollector(collection_interval=30)
collector.start_collection()

# 自定义指标记录
collector.record_connection_metrics(custom_pool_metrics)
collector.record_cache_metrics(custom_cache_metrics)
```

## 📚 API参考

### 核心函数

- `start_monitoring()` - 启动基础性能监控
- `stop_monitoring()` - 停止基础性能监控
- `get_performance_stats()` - 获取性能统计
- `start_metrics_collection(interval)` - 启动指标收集
- `get_current_metrics()` - 获取当前系统指标
- `get_health_report()` - 获取健康报告
- `start_interactive_dashboard()` - 启动交互式仪表板
- `start_realtime_dashboard(refresh_interval)` - 启动实时仪表板

### 类和对象

详细的类API文档请参考各个模块的docstring。

## 🎉 总结

FastORM的性能监控系统提供了一套完整的解决方案，从基础的查询分析到高级的系统监控，从开发调试到生产运维，都能提供强有力的支持。通过合理配置和使用，可以帮助开发者：

- 🔍 快速定位性能瓶颈
- 🚨 及时发现N+1查询等问题
- 📊 了解系统资源使用情况
- 🏥 监控应用健康状态
- 📈 制定性能优化策略

建议在项目中逐步引入这些功能，从基础监控开始，根据需要逐渐添加更多高级功能。 