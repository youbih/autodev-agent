import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app import models

# 创建内存数据库用于测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 覆盖依赖
@pytest.fixture(scope="function")
def override_get_db():
    # 创建表
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(override_get_db):
    def _get_db_override():
        try:
            yield override_get_db
        finally:
            pass
    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# 测试用例
class TestUserAPI:
    def test_create_user_success(self, client):
        """测试成功创建用户"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "secret123",
            "is_active": True
        }
        response = client.post("/users", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] == True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "hashed_password" not in data  # 密码不应返回

    def test_create_user_duplicate_username(self, client):
        """测试创建重复用户名的用户"""
        user_data = {
            "username": "duplicate",
            "email": "first@example.com",
            "password": "pass1"
        }
        response = client.post("/users", json=user_data)
        assert response.status_code == 201
        
        # 尝试创建相同用户名的用户
        user_data2 = {
            "username": "duplicate",
            "email": "second@example.com",
            "password": "pass2"
        }
        response2 = client.post("/users", json=user_data2)
        assert response2.status_code == 400
        assert response2.json()["detail"] == "用户名已存在"

    def test_create_user_duplicate_email(self, client):
        """测试创建重复邮箱的用户"""
        user_data = {
            "username": "user1",
            "email": "same@example.com",
            "password": "pass1"
        }
        response = client.post("/users", json=user_data)
        assert response.status_code == 201
        
        # 尝试创建相同邮箱的用户
        user_data2 = {
            "username": "user2",
            "email": "same@example.com",
            "password": "pass2"
        }
        response2 = client.post("/users", json=user_data2)
        assert response2.status_code == 400
        assert response2.json()["detail"] == "邮箱已存在"

    def test_get_users_empty(self, client):
        """测试获取空用户列表"""
        response = client.get("/users")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_users_with_data(self, client):
        """测试获取用户列表"""
        # 创建两个用户
        user1 = {"username": "user1", "email": "user1@example.com", "password": "pass1"}
        user2 = {"username": "user2", "email": "user2@example.com", "password": "pass2"}
        
        client.post("/users", json=user1)
        client.post("/users", json=user2)
        
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["username"] == "user1"
        assert data[1]["username"] == "user2"

    def test_get_users_pagination(self, client):
        """测试用户列表分页"""
        # 创建3个用户
        for i in range(3):
            client.post("/users", json={
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "password": "pass"
            })
        
        # 测试skip和limit
        response = client.get("/users?skip=1&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "user1"

    def test_get_user_by_id_success(self, client):
        """测试根据ID获取用户成功"""
        # 创建用户
        create_response = client.post("/users", json={
            "username": "test",
            "email": "test@example.com",
            "password": "pass"
        })
        user_id = create_response.json()["id"]
        
        # 获取用户
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == "test"

    def test_get_user_by_id_not_found(self, client):
        """测试获取不存在的用户"""
        response = client.get("/users/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "用户不存在"

    def test_update_user_success(self, client):
        """测试成功更新用户"""
        # 创建用户
        create_response = client.post("/users", json={
            "username": "oldname",
            "email": "old@example.com",
            "password": "oldpass",
            "full_name": "Old Name"
        })
        user_id = create_response.json()["id"]
        
        # 更新用户
        update_data = {
            "username": "newname",
            "email": "new@example.com",
            "full_name": "New Name",
            "password": "newpass"
        }
        response = client.put(f"/users/{user_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newname"
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "New Name"
        
        # 验证更新后的用户
        get_response = client.get(f"/users/{user_id}")
        assert get_response.json()["username"] == "newname"

    def test_update_user_partial(self, client):
        """测试部分更新用户"""
        # 创建用户
        create_response = client.post("/users", json={
            "username": "partial",
            "email": "partial@example.com",
            "password": "pass",
            "full_name": "Original Name"
        })
        user_id = create_response.json()["id"]
        
        # 只更新full_name
        update_data = {"full_name": "Updated Name"}
        response = client.put(f"/users/{user_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "partial"  # 保持不变
        assert data["full_name"] == "Updated Name"  # 已更新

    def test_update_user_duplicate_username(self, client):
        """测试更新用户时用户名冲突"""
        # 创建两个用户
        client.post("/users", json={"username": "user1", "email": "user1@example.com", "password": "pass"})
        create_response = client.post("/users", json={"username": "user2", "email": "user2@example.com", "password": "pass"})
        user2_id = create_response.json()["id"]
        
        # 尝试将user2的用户名改为user1
        update_data = {"username": "user1"}
        response = client.put(f"/users/{user2_id}", json=update_data)
        assert response.status_code == 400
        assert response.json()["detail"] == "用户名已存在"

    def test_update_user_duplicate_email(self, client):
        """测试更新用户时邮箱冲突"""
        # 创建两个用户
        client.post("/users", json={"username": "user1", "email": "email1@example.com", "password": "pass"})
        create_response = client.post("/users", json={"username": "user2", "email": "email2@example.com", "password": "pass"})
        user2_id = create_response.json()["id"]
        
        # 尝试将user2的邮箱改为email1@example.com
        update_data = {"email": "email1@example.com"}
        response = client.put(f"/users/{user2_id}", json=update_data)
        assert response.status_code == 400
        assert response.json()["detail"] == "邮箱已存在"

    def test_update_user_not_found(self, client):
        """测试更新不存在的用户"""
        update_data = {"username": "newname"}
        response = client.put("/users/999", json=update_data)
        assert response.status_code == 404
        assert response.json()["detail"] == "用户不存在"

    def test_delete_user_success(self, client):
        """测试成功删除用户"""
        # 创建用户
        create_response = client.post("/users", json={
            "username": "todelete",
            "email": "delete@example.com",
            "password": "pass"
        })
        user_id = create_response.json()["id"]
        
        # 删除用户
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 204
        
        # 验证用户已删除
        get_response = client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    def test_delete_user_not_found(self, client):
        """测试删除不存在的用户"""
        response = client.delete("/users/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "用户不存在"

    def test_user_password_hashing(self, client, override_get_db):
        """测试密码哈希处理"""
        # 创建用户
        response = client.post("/users", json={
            "username": "hashuser",
            "email": "hash@example.com",
            "password": "mysecret"
        })
        assert response.status_code == 201
        
        # 直接从数据库检查哈希密码
        db_user = override_get_db.query(models.User).filter(models.User.username == "hashuser").first()
        assert db_user is not None
        assert db_user.hashed_password == "mysecret_hashed"  # 根据main.py中的简化哈希逻辑

    def test_update_user_password_hashing(self, client, override_get_db):
        """测试更新用户时的密码哈希处理"""
        # 创建用户
        create_response = client.post("/users", json={
            "username": "updatepass",
            "email": "updatepass@example.com",
            "password": "oldpass"
        })
        user_id = create_response.json()["id"]
        
        # 更新密码
        update_data = {"password": "newpass"}
        response = client.put(f"/users/{user_id}", json=update_data)
        assert response.status_code == 200
        
        # 直接从数据库检查哈希密码
        db_user = override_get_db.query(models.User).filter(models.User.id == user_id).first()
        assert db_user.hashed_password == "newpass_hashed"
