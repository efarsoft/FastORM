# 🚀 PyPI OIDC 发布完整指南

FastORM PyPI发布支持两种方式：API Token（首次发布）和OIDC（推荐的安全方式）

## 📋 部署步骤概览

### 阶段1：首次发布（使用API Token）
### 阶段2：配置OIDC（长期安全方案）
### 阶段3：自动化发布

---

## 🔐 阶段1：首次发布（API Token）

### 1.1 创建PyPI账户

1. 访问 https://pypi.org/account/register/
2. 注册账户并验证邮箱
3. 设置双因素认证（2FA）

### 1.2 生成API Token

1. 登录PyPI → Account settings → API tokens
2. 点击 "Add API token"
3. 设置Token名称：`FastORM-GitHub-Actions`
4. Scope选择：`Entire account`（首次发布必须）
5. 复制生成的token（只显示一次！）

### 1.3 配置GitHub Secrets

在GitHub仓库中：
1. Settings → Secrets and variables → Actions
2. 添加Repository secret：
   - Name: `PYPI_API_TOKEN`
   - Value: 粘贴刚才复制的token

### 1.4 首次发布

```bash
# 手动触发工作流
# GitHub → Actions → "🚀 Publish to PyPI" → Run workflow
# 取消勾选 "使用 OIDC 发布"
```

---

## 🔒 阶段2：配置OIDC（推荐）

### 2.1 配置PyPI可信发布者

项目成功发布后：

1. 登录PyPI → 进入`fastorm`项目页面
2. Manage → Publishing → Add a new pending publisher
3. 填写信息：
   ```
   PyPI project name: fastorm
   Owner: [您的GitHub用户名]
   Repository name: NeoAiBiz
   Workflow filename: publish.yml
   Environment name: release
   ```
4. 点击 "Add"

### 2.2 测试OIDC发布

```bash
# 手动触发工作流
# GitHub → Actions → "🚀 Publish to PyPI" → Run workflow
# 勾选 "使用 OIDC 发布"
```

### 2.3 删除API Token（可选）

OIDC配置成功后，可以删除API Token：
1. PyPI → Account settings → API tokens
2. 删除 `FastORM-GitHub-Actions` token
3. GitHub → Settings → Secrets → 删除 `PYPI_API_TOKEN`

---

## ⚡ 阶段3：自动化发布

### 3.1 Release触发发布

```bash
# 创建Git标签
git tag v0.1.1
git push origin v0.1.1

# 在GitHub上创建Release
# 这将自动触发OIDC发布
```

### 3.2 版本管理

工作流使用 `hatch` 动态读取版本：

```python
# fastorm/__init__.py
__version__ = "0.1.1"  # 更新这里

# pyproject.toml 会自动同步
[tool.hatch.version]
path = "fastorm/__init__.py"
```

---

## 🧪 测试发布

### TestPyPI测试

1. 手动触发工作流
2. 勾选 "发布到 TestPyPI"
3. 测试安装：
   ```bash
   pip install -i https://test.pypi.org/simple/ fastorm
   ```

---

## 📊 工作流特性

### 🎯 智能发布策略

| 触发方式 | 发布目标 | 认证方式 |
|---------|---------|---------|
| Release创建 | PyPI | OIDC |
| 手动触发 + OIDC勾选 | PyPI | OIDC |
| 手动触发 + 不勾选OIDC | PyPI | API Token |
| 手动触发 + TestPyPI勾选 | TestPyPI | OIDC |

### 🔍 质量检查

- ✅ 代码格式检查（ruff）
- ✅ 包构建验证
- ✅ 元数据验证
- ✅ 导入测试

### 🛡️ 安全特性

- ✅ OIDC无密钥认证
- ✅ 环境隔离
- ✅ 最小权限原则
- ✅ 自动令牌轮换

---

## 🚨 故障排除

### 常见问题

#### 1. "Invalid or non-existent authentication information"
- 检查API Token格式
- 确认用户名为 `__token__`
- 验证Token未过期

#### 2. "项目名称已存在"
- 更改 `pyproject.toml` 中的项目名称
- 或联系PyPI管理员申请名称

#### 3. OIDC认证失败
- 确认可信发布者配置正确
- 检查仓库名称、工作流文件名
- 验证环境名称匹配

#### 4. 包构建失败
- 检查 `pyproject.toml` 语法
- 确认依赖项正确
- 验证文件路径

### 调试技巧

```bash
# 本地测试构建
pip install hatch twine
hatch build
twine check dist/*

# 本地测试上传（TestPyPI）
twine upload --repository testpypi dist/*
```

---

## 📈 监控和指标

### GitHub Actions监控
- 构建时间跟踪
- 成功/失败率统计
- 包大小监控

### PyPI统计
- 下载量追踪
- 版本分布
- 用户反馈

---

## 🔗 相关链接

- [PyPI官方文档](https://pypi.org/help/)
- [OIDC配置指南](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions文档](https://docs.github.com/actions)
- [Python打包指南](https://packaging.python.org/)

---

## 📞 支持

如遇问题，请：
1. 查看GitHub Actions日志
2. 检查PyPI项目状态
3. 参考故障排除章节
4. 提交Issue寻求帮助

---

> 🎉 **恭喜！** 您现在拥有了一个现代化、安全的PyPI发布流程！ 