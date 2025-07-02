# FastORM v0.1.0 发布说明 (开发预览版)

## 🎉 首次发布！

FastORM v0.1.0 是我们的首个开发预览版本，为FastAPI开发者提供了一个现代、类型安全的异步ORM解决方案。

## 📦 版本信息

- **版本号**: 0.1.0 (开发预览版)
- **发布日期**: 2025年1月
- **开发状态**: Alpha
- **Python支持**: 3.10+
- **主要依赖**: SQLAlchemy 2.0.9, Pydantic 2.11.3, FastAPI 0.115.12+

## ✨ 核心功能

### 🏗️ 模型系统 (完整实现)
- ✅ 基于SQLAlchemy 2.0的现代模型定义
- ✅ 类型安全的字段映射 (`Mapped[T]`)
- ✅ 完整的时间戳支持 (created_at, updated_at)
- ✅ 软删除功能
- ✅ 模型事件系统 (before_save, after_save等)
- ✅ Pydantic集成验证

### 🔍 查询构建器 (完整实现)
- ✅ 链式查询API (`where().limit().order_by()`)
- ✅ 完整的CRUD操作 (`create`, `find`, `update`, `delete`)
- ✅ 批量操作 (`create_many`, `delete_where`)
- ✅ 聚合查询 (`count`, `sum`, `avg`)
- ✅ 分页支持 (`paginate`)
- ✅ 存在性检查 (`exists`)
- ✅ 条件查询 (`where`, `where_in`, `where_between`)

### ⚙️ 配置系统 (完整实现)
- ✅ 简单直观的配置API
- ✅ 环境变量支持
- ✅ 数据库连接管理
- ✅ 调试模式配置
- ✅ 时间戳自动管理配置

### 🔗 关系系统 (基础实现)
- ✅ 一对一关系 (HasOne)
- ✅ 一对多关系 (HasMany)
- ✅ 多对多关系 (BelongsToMany)
- ✅ 反向关系 (BelongsTo)
- ✅ 关系预加载
- ✅ 关系查询支持

### 🎛️ 混入系统 (完整实现)
- ✅ 时间戳混入 (TimestampMixin)
- ✅ 软删除混入 (SoftDeleteMixin)
- ✅ 事件混入 (EventMixin)
- ✅ 作用域混入 (ScopeMixin)
- ✅ Pydantic集成混入

### 💾 数据库支持
- ✅ SQLite (开发/测试)
- ✅ PostgreSQL (推荐生产)
- ✅ MySQL/MariaDB
- ✅ 异步驱动支持
- ✅ 连接池管理

## 🧪 测试覆盖

- ✅ **基础功能测试**: 100%通过
- ✅ **综合功能测试**: 100%通过
- ✅ **生产就绪性检查**: 100%通过
- ✅ **数据库操作**: CRUD、查询、分页等全面测试
- ✅ **性能验证**: 基础性能指标正常

## 📋 API示例

### 模型定义
```python
from fastorm import Model
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer

class User(Model):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[int] = mapped_column(Integer, default=18)
```

### 基础操作
```python
# 创建用户
user = await User.create(name="张三", email="zhang@example.com", age=25)

# 查询用户
users = await User.where("age", ">", 18).limit(10).get()
user = await User.find(1)

# 更新用户
await user.update(age=26)

# 删除用户
await user.delete()

# 批量操作
await User.create_many([
    {"name": "李四", "email": "lisi@example.com"},
    {"name": "王五", "email": "wangwu@example.com"}
])
```

### 查询构建
```python
# 链式查询
users = await User.where("age", ">=", 18)\
                 .where("email", "like", "%@gmail.com")\
                 .order_by("created_at", "desc")\
                 .limit(20)\
                 .get()

# 分页
paginator = await User.query().paginate(page=1, per_page=10)
print(f"总计: {paginator.total}, 当前页: {len(paginator.items)}")

# 统计
count = await User.where("active", True).count()
exists = await User.where("email", "test@example.com").exists()
```

## 🚧 开发状态说明

### ✅ 已完成
- 核心ORM功能 (模型、查询、关系)
- 基础FastAPI集成
- 完整的CRUD操作
- 测试框架

### 🔄 开发中 (后续版本)
- CLI工具完善
- 高级缓存系统
- 性能监控仪表板
- 数据库迁移工具
- 更多数据库支持

### 📋 计划中
- 图形化管理界面
- 高级查询优化
- 插件系统
- 社区生态

## ⚠️ 使用说明

**这是一个开发预览版本，不建议用于生产环境。**

### 适用场景
- ✅ 学习和评估
- ✅ 原型开发
- ✅ 小型项目试验
- ✅ 功能测试和反馈

### 不建议场景
- ❌ 生产环境部署
- ❌ 关键业务系统
- ❌ 大规模商业项目

## 🛠️ 安装指南

```bash
# 基础安装
pip install fastorm==0.1.0

# 开发安装 (包含测试工具)
pip install fastorm[dev]==0.1.0
```

## 📚 文档资源

- **README**: [GitHub](https://github.com/efarsoft/FastORM/blob/main/README.md)
- **示例代码**: [examples目录](https://github.com/efarsoft/FastORM/tree/main/examples)
- **测试用例**: [tests目录](https://github.com/efarsoft/FastORM/tree/main/tests)
- **快速集成指南**: [QUICK_INTEGRATION_GUIDE.md](https://github.com/efarsoft/FastORM/blob/main/QUICK_INTEGRATION_GUIDE.md)

## 🐛 已知问题

1. **CLI工具**: 部分高级功能仍在开发中
2. **性能优化**: 某些复杂查询可能需要进一步优化
3. **文档完善**: API文档仍在补充中
4. **错误处理**: 部分边缘情况的错误信息有待优化

## 🤝 参与贡献

我们欢迎社区反馈和贡献！

### 反馈方式
- 🐛 [报告问题](https://github.com/efarsoft/FastORM/issues)
- 💡 [功能建议](https://github.com/efarsoft/FastORM/discussions)
- 📧 邮件联系: team@fastorm.dev

### 贡献指南
1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 🗓️ 版本规划

### v0.2.0 (计划中)
- CLI工具完善
- 数据库迁移支持
- 缓存系统增强
- 文档完善

### v0.3.0 (计划中)
- 性能监控仪表板
- 高级查询优化
- 更多测试覆盖

### v1.0.0 (生产版本)
- 完整功能验证
- 生产环境优化
- 长期支持承诺

## 🙏 致谢

感谢以下开源项目为FastORM提供的基础支持：
- SQLAlchemy - 强大的Python SQL工具包
- Pydantic - 现代数据验证库
- FastAPI - 高性能Web框架

---

**FastORM v0.1.0 - 开始你的现代ORM之旅！** 🚀 