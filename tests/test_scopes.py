"""
FastORM 作用域功能测试

测试查询作用域系统的各种功能：
1. 普通作用域定义和使用
2. 全局作用域自动应用
3. 作用域链式调用
4. 作用域参数传递
5. 全局作用域移除
6. 作用域注册和获取
"""

import pytest
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean
from fastorm import Model
from fastorm.mixins.scopes import scope, global_scope


class ScopeTestUser(Model):
    """作用域测试用户模型"""
    __tablename__ = "scope_test_users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    
    @scope
    def active(self, query):
        """活跃用户作用域"""
        return query.where('status', 'active')
    
    @scope
    def verified(self, query):
        """已验证用户作用域"""
        return query.where('is_verified', True)
    
    @scope
    def by_role(self, query, role: str):
        """按角色筛选作用域"""
        return query.where('role', role)
    
    @scope
    def by_department(self, query, department: str):
        """按部门筛选作用域"""
        return query.where('department', department)
    
    @scope
    def name_contains(self, query, keyword: str):
        """名称包含关键词作用域"""
        return query.where('name', 'like', f'%{keyword}%')
    
    @global_scope('default_ordering')
    def apply_default_ordering(self, query):
        """全局作用域：默认按名称排序"""
        return query.order_by('name', 'asc')


class GlobalScopeTestUser(Model):
    """全局作用域测试用户模型"""
    __tablename__ = "global_scope_test_users"
    
    timestamps = True
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    
    @global_scope('hide_inactive')
    def hide_inactive_users(self, query):
        """全局作用域：隐藏非活跃用户"""
        return query.where('status', 'active')
    
    @global_scope('hide_hidden')
    def hide_hidden_users(self, query):
        """全局作用域：隐藏标记为隐藏的用户"""
        return query.where('is_hidden', False)
    
    @global_scope('default_ordering')
    def apply_default_ordering(self, query):
        """全局作用域：默认按名称排序"""
        return query.order_by('name', 'asc')
    
    @scope
    def by_status(self, query, status: str):
        """按状态筛选作用域"""
        return query.where('status', status)


class TestScopes:
    """作用域功能测试类"""

    @pytest.mark.asyncio
    async def test_scope_registration(self, test_database):
        """测试作用域注册功能"""
        # 检查普通作用域是否正确注册
        scopes = ScopeTestUser.get_registered_scopes()
        expected_scopes = ['active', 'verified', 'by_role', 'by_department', 'name_contains']
        
        for scope_name in expected_scopes:
            assert scope_name in scopes, f"作用域 {scope_name} 未注册"
        
        # 检查全局作用域是否正确注册
        global_scopes = ScopeTestUser.get_registered_global_scopes()
        assert 'default_ordering' in global_scopes, "全局作用域 default_ordering 未注册"

    @pytest.mark.asyncio
    async def test_basic_scope_usage(self, test_database):
        """测试基本作用域使用"""
        # 创建测试数据
        await ScopeTestUser.create(name="张三", email="zhang@test.com", status="active")
        await ScopeTestUser.create(name="李四", email="li@test.com", status="inactive")
        await ScopeTestUser.create(name="王五", email="wang@test.com", status="active")
        
        # 测试单个作用域
        active_users = await ScopeTestUser.query().active().get()
        assert len(active_users) == 2, "active作用域应该返回2个用户"
        
        # 验证返回的都是活跃用户
        for user in active_users:
            assert user.status == "active", "作用域过滤失效"

    @pytest.mark.asyncio
    async def test_scope_with_parameters(self, test_database):
        """测试带参数的作用域"""
        # 创建不同角色的用户
        await ScopeTestUser.create(name="管理员", email="admin@test.com", role="admin")
        await ScopeTestUser.create(name="用户1", email="user1@test.com", role="user")
        await ScopeTestUser.create(name="用户2", email="user2@test.com", role="user")
        await ScopeTestUser.create(name="编辑", email="editor@test.com", role="editor")
        
        # 测试按角色筛选
        admin_users = await ScopeTestUser.query().by_role("admin").get()
        assert len(admin_users) == 1, "应该只有1个管理员"
        assert admin_users[0].role == "admin"
        
        user_users = await ScopeTestUser.query().by_role("user").get()
        assert len(user_users) == 2, "应该有2个普通用户"

    @pytest.mark.asyncio
    async def test_chained_scopes(self, test_database):
        """测试链式作用域调用"""
        # 创建测试数据
        await ScopeTestUser.create(
            name="张三", email="zhang@test.com", 
            status="active", role="admin", is_verified=True
        )
        await ScopeTestUser.create(
            name="李四", email="li@test.com", 
            status="active", role="user", is_verified=False
        )
        await ScopeTestUser.create(
            name="王五", email="wang@test.com", 
            status="inactive", role="admin", is_verified=True
        )
        
        # 链式调用多个作用域
        verified_active_admins = await ScopeTestUser.query().active().verified().by_role("admin").get()
        
        assert len(verified_active_admins) == 1, "应该只有1个已验证的活跃管理员"
        user = verified_active_admins[0]
        assert user.name == "张三"
        assert user.status == "active"
        assert user.role == "admin"
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_scope_with_like_query(self, test_database):
        """测试包含LIKE查询的作用域"""
        # 创建测试数据
        await ScopeTestUser.create(name="张三丰", email="zhang@test.com")
        await ScopeTestUser.create(name="张无忌", email="zhang2@test.com")
        await ScopeTestUser.create(name="李四", email="li@test.com")
        await ScopeTestUser.create(name="王五", email="wang@test.com")
        
        # 测试名称包含关键词的作用域
        zhang_users = await ScopeTestUser.query().name_contains("张").get()
        assert len(zhang_users) == 2, "应该找到2个姓张的用户"
        
        for user in zhang_users:
            assert "张" in user.name, "作用域过滤失效"

    @pytest.mark.asyncio
    async def test_global_scope_auto_application(self, test_database):
        """测试全局作用域自动应用"""
        # 创建测试数据（注意：全局作用域会自动排序）
        await GlobalScopeTestUser.create(name="Charlie", status="active")
        await GlobalScopeTestUser.create(name="Alice", status="active")
        await GlobalScopeTestUser.create(name="Bob", status="inactive")  # 会被全局作用域过滤
        await GlobalScopeTestUser.create(name="David", status="active", is_hidden=True)  # 会被全局作用域过滤
        
        # 普通查询应该自动应用全局作用域
        users = await GlobalScopeTestUser.all()
        
        # 应该只返回活跃且未隐藏的用户，且按名称排序
        assert len(users) == 2, "全局作用域应该过滤掉非活跃和隐藏用户"
        
        # 验证都是活跃且未隐藏的用户
        for user in users:
            assert user.status == "active", "全局作用域过滤失效"
            assert user.is_hidden is False, "全局作用域过滤失效"
        
        # 验证排序（应该按名称升序）
        assert users[0].name == "Alice", "全局作用域排序失效"
        assert users[1].name == "Charlie", "全局作用域排序失效"

    @pytest.mark.asyncio
    async def test_without_global_scope(self, test_database):
        """测试移除全局作用域"""
        # 创建测试数据
        await GlobalScopeTestUser.create(name="Active User", status="active")
        await GlobalScopeTestUser.create(name="Inactive User", status="inactive")
        await GlobalScopeTestUser.create(name="Hidden User", status="active", is_hidden=True)
        
        # 移除单个全局作用域
        users_with_inactive = await GlobalScopeTestUser.query().without_global_scope('hide_inactive').get()
        # 应该包含非活跃用户，但仍然排除隐藏用户
        active_and_inactive = [u for u in users_with_inactive if not u.is_hidden]
        assert len(active_and_inactive) >= 2, "移除hide_inactive作用域后应该包含非活跃用户"
        
        # 移除所有全局作用域
        all_users = await GlobalScopeTestUser.query().without_global_scopes().get()
        assert len(all_users) == 3, "移除所有全局作用域后应该返回所有用户"

    @pytest.mark.asyncio
    async def test_without_multiple_global_scopes(self, test_database):
        """测试移除多个指定的全局作用域"""
        # 创建测试数据
        await GlobalScopeTestUser.create(name="Active User", status="active")
        await GlobalScopeTestUser.create(name="Inactive User", status="inactive")
        await GlobalScopeTestUser.create(name="Hidden User", status="active", is_hidden=True)
        
        # 移除指定的多个全局作用域
        users = await GlobalScopeTestUser.query().without_global_scopes(['hide_inactive', 'hide_hidden']).get()
        assert len(users) == 3, "移除指定的全局作用域后应该返回所有用户"

    @pytest.mark.asyncio
    async def test_scope_with_query_builder_methods(self, test_database):
        """测试作用域与查询构建器方法的结合"""
        # 创建测试数据
        for i in range(10):
            await ScopeTestUser.create(
                name=f"用户{i:02d}", 
                email=f"user{i}@test.com",
                status="active" if i % 2 == 0 else "inactive",
                role="admin" if i < 3 else "user"
            )
        
        # 结合作用域和查询构建器方法
        result = await ScopeTestUser.query().active().by_role("admin").limit(2).get()
        
        # 应该返回最多2个活跃的管理员
        assert len(result) <= 2, "limit方法应该限制结果数量"
        for user in result:
            assert user.status == "active", "作用域过滤失效"
            assert user.role == "admin", "作用域过滤失效"

    @pytest.mark.asyncio
    async def test_scope_with_count_and_exists(self, test_database):
        """测试作用域与count、exists方法的结合"""
        # 创建测试数据
        await ScopeTestUser.create(name="活跃用户", email="active@test.com", status="active")
        await ScopeTestUser.create(name="非活跃用户", email="inactive@test.com", status="inactive")
        
        # 测试count方法
        active_count = await ScopeTestUser.query().active().count()
        assert active_count == 1, "作用域count方法失效"
        
        # 测试exists方法
        has_active = await ScopeTestUser.query().active().exists()
        assert has_active is True, "作用域exists方法失效"
        
        has_verified = await ScopeTestUser.query().verified().exists()
        assert has_verified is False, "作用域exists方法失效"

    @pytest.mark.asyncio
    async def test_scope_error_handling(self, test_database):
        """测试作用域错误处理"""
        # 测试调用不存在的作用域
        with pytest.raises(AttributeError):
            await ScopeTestUser.query().nonexistent_scope().get()

    @pytest.mark.asyncio
    async def test_complex_scope_combinations(self, test_database):
        """测试复杂的作用域组合"""
        # 创建复杂的测试数据
        test_users = [
            {"name": "张三", "status": "active", "role": "admin", "is_verified": True, "department": "IT"},
            {"name": "李四", "status": "active", "role": "user", "is_verified": False, "department": "HR"},
            {"name": "王五", "status": "inactive", "role": "admin", "is_verified": True, "department": "IT"},
            {"name": "赵六", "status": "active", "role": "editor", "is_verified": True, "department": "Marketing"},
            {"name": "钱七", "status": "active", "role": "admin", "is_verified": False, "department": "Finance"},
        ]
        
        for user_data in test_users:
            await ScopeTestUser.create(email=f"{user_data['name']}@test.com", **user_data)
        
        # 复杂查询：活跃的、已验证的IT部门用户
        it_verified_active = await (ScopeTestUser.query()
                                   .active()
                                   .verified()
                                   .by_department("IT")
                                   .get())
        
        assert len(it_verified_active) == 1, "复杂作用域组合失效"
        user = it_verified_active[0]
        assert user.name == "张三"
        assert user.status == "active"
        assert user.is_verified is True
        assert user.department == "IT" 