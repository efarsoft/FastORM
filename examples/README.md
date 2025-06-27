# FastORM 示例文件

本目录包含FastORM的各种使用示例和演示程序，帮助开发者快速了解和使用FastORM的功能特性。

## 目录结构

```
examples/
├── README.md                           # 本文件 - 示例说明
├── quickstart.py                       # 快速入门示例
├── simple_demo.py                      # 简单演示
├── enhanced_demo.py                    # 增强功能演示
├── existing_project_integration_demo.py # 现有项目集成演示
├── stage_10_cli_demo.py               # CLI工具演示
├── stage_8_demo.py                    # 第八阶段功能演示
├── stage_7_demo.py                    # 第七阶段功能演示
├── pydantic_v2_demo.py                # Pydantic v2集成演示
├── events_demo.py                     # 事件系统演示
├── soft_delete_standalone.py          # 软删除功能演示
└── sqlalchemy_2_modern_demo.py       # SQLAlchemy 2现代化演示
```

## 示例分类

### 🚀 入门示例
- **`quickstart.py`** - 5分钟快速入门，展示基本的CRUD操作
- **`simple_demo.py`** - 最简单的使用示例
- **`enhanced_demo.py`** - 完整功能演示，包含高级特性

### 🛠️ 工具集成
- **`existing_project_integration_demo.py`** - 现有FastAPI项目集成FastORM
- **`stage_10_cli_demo.py`** - CLI命令行工具完整演示
- **`sqlalchemy_2_modern_demo.py`** - SQLAlchemy 2.0现代化特性

### 📊 高级功能
- **`pydantic_v2_demo.py`** - Pydantic v2深度集成
- **`events_demo.py`** - 事件驱动架构演示
- **`soft_delete_standalone.py`** - 软删除功能完整实现

### 🎯 阶段性演示
- **`stage_8_demo.py`** - 第八阶段：测试工厂系统
- **`stage_7_demo.py`** - 第七阶段：查询优化和分页

## 快速开始

### 1. 最简单的例子
```bash
python examples/quickstart.py
```

### 2. 完整功能演示
```bash
python examples/enhanced_demo.py
```

### 3. CLI工具演示
```bash
python examples/stage_10_cli_demo.py
```

## 运行要求

### 基础环境
- Python 3.8+
- FastORM (通过 `pip install -e .` 安装开发版)

### 依赖安装
```bash
# 安装FastORM开发版
pip install -e .

# 或安装完整版本
pip install "fastorm[full]"
```

### 数据库配置
大部分示例使用SQLite，无需额外配置。如需使用PostgreSQL或MySQL：

```bash
# PostgreSQL
pip install "fastorm[postgresql]"

# MySQL  
pip install "fastorm[mysql]"
```

## 示例详解

### quickstart.py - 快速入门
```python
# 展示内容：
- 数据库连接配置
- 模型定义
- 基本CRUD操作
- 查询构建器使用
- 关系管理
```

### enhanced_demo.py - 完整演示
```python
# 展示内容：
- 高级查询功能
- 批量操作
- 事务管理
- 缓存使用
- 性能优化
- 错误处理
```

### existing_project_integration_demo.py - 项目集成
```python
# 展示内容：
- 现有FastAPI项目结构检测
- FastORM集成步骤
- 新旧代码并行运行
- 渐进式迁移策略
```

### stage_10_cli_demo.py - CLI工具
```python
# 展示内容：
- 项目初始化命令
- 模型生成命令
- 数据库迁移命令
- 开发服务器启动
```

## 最佳实践示例

### 1. 项目结构
参考 `enhanced_demo.py` 了解推荐的项目组织方式。

### 2. 错误处理
查看 `pydantic_v2_demo.py` 学习完善的错误处理机制。

### 3. 性能优化
研究 `stage_7_demo.py` 了解查询优化和分页最佳实践。

### 4. 测试策略
参考 `stage_8_demo.py` 学习测试工厂的使用方法。

## 自定义示例

### 创建新示例
1. 在 `examples/` 目录创建新的Python文件
2. 使用清晰的注释解释代码功能
3. 包含完整的运行说明
4. 更新本README文件

### 示例模板
```python
"""
FastORM 示例：[功能名称]

本示例演示如何使用FastORM的[具体功能]

运行方式：
    python examples/your_example.py

依赖要求：
    - FastORM
    - [其他依赖]
"""

# 导入必要的模块
from fastorm import Database, BaseModel

# 主要演示代码
async def main():
    # 数据库初始化
    await Database.init("sqlite:///examples/demo.db")
    
    # 功能演示
    # ...
    
    # 清理
    await Database.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## 获取帮助

- 📖 **文档**: [fastorm.dev](https://fastorm.dev)
- 💬 **社区**: [Discord](https://discord.gg/fastorm)
- 🐛 **问题**: [GitHub Issues](https://github.com/fastorm/fastorm/issues)
- 💡 **讨论**: [GitHub Discussions](https://github.com/fastorm/fastorm/discussions)

## 贡献示例

我们欢迎社区贡献更多实用的示例！

1. Fork项目仓库
2. 创建示例文件
3. 添加详细说明
4. 提交Pull Request

### 示例贡献指南
- 代码清晰易懂
- 注释充分详细
- 包含运行说明
- 遵循项目规范 