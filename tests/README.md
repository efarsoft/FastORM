# FastORM 测试文件

本目录包含FastORM项目的所有测试文件和测试相关资源。

## 目录结构

```
tests/
├── README.md              # 本文件 - 测试说明
├── database/             # 测试数据库文件
│   ├── bug_fixes_test.db
│   ├── enhanced_demo.db
│   ├── events_demo.db
│   ├── modern_demo.db
│   ├── relations_test.db
│   ├── simple_state_test.db
│   ├── soft_delete_standalone.db
│   ├── test.db
│   └── test_soft_delete.db
├── examples/             # 示例测试文件
│   ├── bug_fixes_test.py
│   ├── relations_test.py
│   ├── simple_stage_7_test.py
│   └── simple_stage_8_test.py
└── performance/          # 性能测试文件
    └── stage_9_performance_demo.py
```

## 测试类型说明

### 数据库测试 (database/)
存放各种测试场景使用的SQLite数据库文件：
- `bug_fixes_test.db` - Bug修复验证测试数据库
- `enhanced_demo.db` - 增强功能演示数据库
- `events_demo.db` - 事件系统测试数据库
- `modern_demo.db` - 现代化功能测试数据库
- `relations_test.db` - 关系管理测试数据库
- `simple_state_test.db` - 简单状态测试数据库
- `soft_delete_standalone.db` - 软删除功能测试数据库

### 示例测试 (examples/)
包含各个阶段开发的测试文件：
- `bug_fixes_test.py` - Bug修复测试用例
- `relations_test.py` - 数据库关系测试
- `simple_stage_7_test.py` - 第七阶段简单测试
- `simple_stage_8_test.py` - 第八阶段简单测试

### 性能测试 (performance/)
包含性能相关的测试和演示：
- `stage_9_performance_demo.py` - 第九阶段性能监控演示

## 运行测试

### 运行所有测试
```bash
# 从项目根目录运行
pytest tests/

# 详细输出
pytest tests/ -v

# 覆盖率报告
pytest tests/ --cov=fastorm
```

### 运行特定测试
```bash
# 运行示例测试
pytest tests/examples/

# 运行性能测试
pytest tests/performance/

# 运行特定文件
pytest tests/examples/relations_test.py
```

### 测试环境要求
- Python 3.8+
- pytest
- SQLAlchemy 2.0+
- FastAPI
- 其他依赖见 pyproject.toml

## 添加新测试

1. **单元测试**: 直接在 `tests/` 根目录创建
2. **集成测试**: 放在 `tests/examples/` 目录
3. **性能测试**: 放在 `tests/performance/` 目录
4. **测试数据库**: 放在 `tests/database/` 目录

### 测试文件命名规范
- 测试文件以 `test_` 开头或以 `_test.py` 结尾
- 测试类以 `Test` 开头
- 测试方法以 `test_` 开头

### 示例测试结构
```python
import pytest
from fastorm import Database, BaseModel

class TestUserModel:
    @pytest.fixture
    async def db_setup(self):
        await Database.init("sqlite:///tests/database/test.db")
        yield
        await Database.close()
    
    async def test_create_user(self, db_setup):
        user = await User.create(name="测试用户")
        assert user.name == "测试用户"
```

## 测试最佳实践

1. **隔离性**: 每个测试应该独立运行
2. **清理**: 测试后清理数据，避免影响其他测试
3. **覆盖率**: 确保核心功能有足够的测试覆盖
4. **性能**: 定期运行性能测试，监控回归
5. **文档**: 复杂测试添加说明注释 