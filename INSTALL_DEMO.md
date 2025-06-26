# 🚀 FastORM 安装演示

## 📦 开箱即用 - 自动依赖管理

### ✅ **问题已解决！**

现在FastORM已经包含了基础数据库支持，用户安装后可以立即使用，无需手动安装额外依赖。

## 📋 安装方式对比

### **🎯 基础安装（推荐）**
```bash
pip install fastorm
```

**自动包含的依赖：**
- ✅ SQLAlchemy 2.0.40+ (异步支持)
- ✅ Pydantic 2.11+ (类型验证)
- ✅ Pydantic Settings 2.6+ (配置管理)
- ✅ **aiosqlite 0.20+** (SQLite异步驱动) 🎉

**立即可用：**
```python
import fastorm
from fastorm import BaseModel, Database

# 无需额外安装，直接可用！
fastorm.init("sqlite+aiosqlite:///app.db")
```

### **🚀 完整安装**
```bash
# PostgreSQL支持
pip install "fastorm[postgresql]"

# MySQL支持  
pip install "fastorm[mysql]"

# FastAPI集成
pip install "fastorm[fastapi]"

# 缓存支持
pip install "fastorm[cache]"

# 全功能安装
pip install "fastorm[full]"
```

## 🆚 更新前后对比

### **❌ 更新前（用户痛点）**
```bash
pip install fastorm
# 安装后尝试使用...
python -c "import fastorm; fastorm.init('sqlite+aiosqlite:///test.db')"
# ❌ 错误：ModuleNotFoundError: No module named 'aiosqlite'

# 用户需要手动安装
pip install aiosqlite  # 😫 额外步骤
```

### **✅ 更新后（无缝体验）**
```bash
pip install fastorm
# 安装后立即可用！
python -c "
import fastorm
from fastorm import BaseModel, Database
fastorm.init('sqlite+aiosqlite:///test.db')
print('✅ FastORM 开箱即用！')
"
# ✅ 输出：FastORM 开箱即用！
```

## 🎯 设计理念

### **🔧 渐进式依赖策略**

1. **核心依赖** - 保证基础功能开箱即用
   - SQLAlchemy 2.0.40+ (核心ORM)
   - Pydantic 2.11+ (类型安全) 
   - aiosqlite (基础数据库)

2. **可选依赖** - 按需扩展功能
   - PostgreSQL/MySQL驱动
   - FastAPI集成
   - Redis缓存
   - 开发工具

### **📊 用户体验提升**

| 场景 | 更新前 | 更新后 |
|------|--------|--------|
| 快速测试 | ❌ 需要查文档安装驱动 | ✅ 一行命令立即可用 |
| 学习体验 | ❌ 安装配置复杂 | ✅ 专注业务逻辑 |
| 生产部署 | ❌ 容易遗漏依赖 | ✅ 基础功能稳定可靠 |
| 团队协作 | ❌ 环境配置不一致 | ✅ 统一开发体验 |

## 🚀 5分钟上手测试

```bash
# 1. 安装FastORM
pip install fastorm

# 2. 创建测试文件
cat > test_fastorm.py << 'EOF'
import asyncio
from fastorm import BaseModel, Database
from sqlalchemy.orm import Mapped, mapped_column

class User(BaseModel):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]

async def main():
    # 初始化 - 无需额外依赖！
    await Database.init("sqlite+aiosqlite:///demo.db")
    await Database.create_all()
    
    async with Database.session() as session:
        # 创建用户
        user = await User.create(session, name="张三", email="zhang@example.com")
        print(f"✅ 创建成功: {user.name}")
        
        # 查询用户
        users = await User.all(session)
        print(f"✅ 查询成功: {len(users)} 个用户")
    
    await Database.close()
    print("🎉 FastORM 测试完成！")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# 3. 运行测试
python test_fastorm.py
```

**预期输出：**
```
✅ 创建成功: 张三
✅ 查询成功: 1 个用户
🎉 FastORM 测试完成！
```

## 💡 最佳实践建议

### **🎯 不同场景的安装策略**

```bash
# 学习和原型开发
pip install fastorm

# Web应用开发
pip install "fastorm[fastapi,postgresql]"

# 企业级应用
pip install "fastorm[full]"

# 数据分析项目
pip install "fastorm[postgresql,cache]"
```

### **🔧 Docker部署示例**

```dockerfile
# 精简版本 - 只安装必需依赖
FROM python:3.11-slim
RUN pip install fastorm

# 完整版本 - 包含所有功能
FROM python:3.11-slim  
RUN pip install "fastorm[full]"
```

## 📈 技术细节

### **🔍 依赖分析**

```bash
# 查看当前依赖
pip show fastorm

# 输出示例：
# Requires: aiosqlite, annotated-types, pydantic, pydantic-settings, sqlalchemy, typing-extensions
```

### **⚡ 性能优化**

- ✅ 延迟导入 - 减少启动时间
- ✅ 编译缓存 - SQLAlchemy 2.0优化
- ✅ 连接池 - 数据库性能优化
- ✅ 类型安全 - 减少运行时错误

---

## 🎉 总结

现在FastORM真正做到了 **"开箱即用"**！用户只需要一个`pip install`命令，就能立即开始使用FastORM的所有核心功能，无需担心复杂的依赖配置问题。

这大大降低了新用户的学习门槛，提升了开发体验！ 🚀 