import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastorm import Model, create_crud_router
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey


# ========== 声明测试模型 ==========
class User(Model):
    __tablename__ = "integration_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)


class Post(Model):
    __tablename__ = "integration_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("integration_users.id"), nullable=False
    )


# ========== 创建FastAPI应用并集成自动API ==========
app = FastAPI()
app.include_router(create_crud_router(User))
app.include_router(create_crud_router(Post))

client = TestClient(app)


# ========== 全流程集成测试 ========== 
@pytest.mark.asyncio
async def test_full_integration(test_database):
    # 1. 创建用户
    resp = client.post(
        "/integration_users/",
        json={"name": "张三", "email": "zhangsan@example.com", "age": 18},
    )
    assert resp.status_code == 200
    user = resp.json()
    assert user["name"] == "张三"
    user_id = user["id"]

    # 2. 创建文章
    resp = client.post(
        "/integration_posts/",
        json={"title": "测试文章", "content": "内容", "user_id": user_id},
    )
    assert resp.status_code == 200
    post = resp.json()
    assert post["title"] == "测试文章"
    post_id = post["id"]

    # 3. 查询用户列表，带where/order_by/with_rel
    resp = client.get(
        "/integration_users/?where=name:张三&order_by=id:desc&with_rel=posts"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["name"] == "张三"

    # 4. 更新用户
    resp = client.put(
        f"/integration_users/{user_id}",
        json={"name": "李四", "email": "zhangsan@example.com", "age": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "李四"

    # 5. 类型安全与参数校验
    resp = client.post(
        "/integration_users/",
        json={"name": 123, "email": "not-an-email", "age": "abc"},
    )
    assert resp.status_code == 422 or resp.status_code == 400

    # 6. 批量创建
    resp = client.post(
        "/integration_users/batch",
        json=[
            {"name": "A", "email": "a@example.com"},
            {"name": "B", "email": "b@example.com"},
        ],
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # 7. 软删除与恢复
    resp = client.delete(f"/integration_users/{user_id}/soft")
    assert resp.status_code == 200
    resp = client.post(f"/integration_users/{user_id}/restore")
    assert resp.status_code == 200

    # 8. 批量删除
    ids = [user_id] + [
        u["id"]
        for u in client.get("/integration_users/").json()["items"]
        if u["name"] in ["A", "B"]
    ]
    resp = client.delete("/integration_users/batch", json=ids)
    assert resp.status_code == 200

    # 9. 序列化与关系预加载
    resp = client.get(f"/integration_posts/{post_id}")
    assert resp.status_code == 200
    post = resp.json()
    assert post["user_id"] == user_id

    # 10. 性能监控（仅示例，实际可加耗时断言）
    # 可在API或QueryBuilder挂载性能监控钩子，略

    # 11. SQL注入与非法参数
    resp = client.get("/integration_users/?where=notafield:1")
    assert resp.status_code == 400 