# FastORM 文档

本目录包含FastORM项目的完整文档，包括使用指南、API参考、性能报告和变更记录。

## 📁 目录结构

```
docs/
├── README.md                    # 本文件 - 文档导航
├── CHANGELOG.md                 # 版本变更记录
├── ROADMAP.md                   # 项目路线图
├── changelogs/                  # 详细变更日志
├── guides/                      # 使用指南
│   ├── INSTALL_DEMO.md         # 安装演示指南
│   ├── SQLAlchemy_2_Integration_Summary.md # SQLAlchemy 2集成指南
│   └── soft_delete_results.md   # 软删除功能指南
├── api/                         # API参考文档
├── performance/                 # 性能相关文档
│   ├── performance_detailed.txt # 详细性能报告
│   └── performance_summary.json # 性能数据摘要
```

## 📖 文档分类

### 🚀 快速开始
- **[主README](../README.md)** - 项目概览和快速入门
- **[安装指南](guides/INSTALL_DEMO.md)** - 详细的安装和配置说明

### 📋 项目管理
- **[变更记录](CHANGELOG.md)** - 版本历史和功能更新
- **[项目路线图](ROADMAP.md)** - 未来发展计划和功能规划

### 🛠️ 使用指南 (guides/)
- **[SQLAlchemy 2集成](guides/SQLAlchemy_2_Integration_Summary.md)** - SQLAlchemy 2.0集成详解
- **[软删除功能](guides/soft_delete_results.md)** - 软删除功能使用指南

### 📊 性能文档 (performance/)
- **[性能详细报告](performance/performance_detailed.txt)** - 完整的性能测试结果
- **[性能数据摘要](performance/performance_summary.json)** - 性能指标JSON格式

### 🔧 API参考 (api/)
*正在建设中...*

## 🎯 文档使用指南

### 新用户推荐阅读顺序
1. **[主README](../README.md)** - 了解FastORM是什么
2. **[安装指南](guides/INSTALL_DEMO.md)** - 安装和初始配置
3. **[示例代码](../examples/)** - 通过示例学习使用
4. **[SQLAlchemy集成](guides/SQLAlchemy_2_Integration_Summary.md)** - 深入了解技术细节

### 现有用户升级指南
1. **[变更记录](CHANGELOG.md)** - 查看最新版本变化
2. **[性能报告](performance/)** - 了解性能改进
3. **[路线图](ROADMAP.md)** - 了解未来功能

### 开发者参考
1. **[API文档](api/)** - 详细的API参考
2. **[性能数据](performance/)** - 性能基准和优化指标
3. **[示例代码](../examples/)** - 实际使用案例

## 📝 文档维护

### 更新频率
- **CHANGELOG.md** - 每个版本发布时更新
- **ROADMAP.md** - 季度更新
- **性能报告** - 每次重大性能改进后更新
- **使用指南** - 功能新增或重大变更时更新

### 文档贡献
我们欢迎社区贡献文档！

#### 贡献类型
- 📝 修正错误和改进现有文档
- ➕ 添加新的使用指南和教程
- 🌐 翻译文档到其他语言
- 💡 提供更好的示例和用例

#### 贡献流程
1. **Fork** 项目仓库
2. **创建** 文档分支
3. **编写** 或修改文档
4. **提交** Pull Request
5. **审核** 和合并

### 文档规范

#### Markdown格式
- 使用标准Markdown语法
- 代码块指定语言高亮
- 链接使用相对路径
- 图片存放在docs/images/目录

#### 文档结构
```markdown
# 标题

简短的描述

## 目录 (可选)

## 主要内容

### 子章节

## 示例代码

```python
# 代码示例
```

## 参考链接
```

#### 命名规范
- 文件名使用snake_case
- 目录名使用kebab-case
- 图片名包含功能描述

## 🔗 相关资源

### 在线资源
- 📖 **官方网站**: [fastorm.dev](https://fastorm.dev)
- 💬 **社区讨论**: [Discord](https://discord.gg/fastorm)
- 🎥 **视频教程**: [YouTube频道](https://youtube.com/fastorm)

### 代码仓库
- 🐛 **问题报告**: [GitHub Issues](https://github.com/fastorm/fastorm/issues)
- 💡 **功能建议**: [GitHub Discussions](https://github.com/fastorm/fastorm/discussions)
- 🔀 **代码贡献**: [Pull Requests](https://github.com/fastorm/fastorm/pulls)

### 社交媒体
- 🐦 **Twitter**: [@FastORM](https://twitter.com/fastorm)
- 📱 **微信群**: 扫描README中的二维码

## 📞 获取帮助

### 常见问题
1. **安装问题** - 查看[安装指南](guides/INSTALL_DEMO.md)
2. **使用问题** - 查看[示例代码](../examples/)
3. **性能问题** - 查看[性能报告](performance/)
4. **集成问题** - 查看[集成指南](guides/SQLAlchemy_2_Integration_Summary.md)

### 联系方式
- 📧 **邮件**: docs@fastorm.dev
- 💬 **即时聊天**: [Discord社区](https://discord.gg/fastorm)
- 🐛 **Bug报告**: [GitHub Issues](https://github.com/fastorm/fastorm/issues)

---

*本文档最后更新: 2024年1月* 