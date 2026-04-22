# My User Service

## 项目简介

My User Service 是一个基于 FastAPI 构建的后端用户管理服务。它采用分层架构（API -> Service -> Repository -> Model），使用 SQLite 作为数据库，并通过 SQLAlchemy ORM 进行数据操作。该服务提供了完整的用户 CRUD（创建、读取、更新、删除）功能，包含数据验证、密码安全处理以及分页查询等特性。

## 核心架构图

```mermaid
graph TD
    subgraph "客户端层"
        Client[HTTP Client]
    end

    subgraph "API 层 (FastAPI)"
        Router[FastAPI Router]
        Endpoint_GET_USERS[/users GET]
        Endpoint_POST_USERS[/users POST]
        Endpoint_GET_USER[/users/{id} GET]
        Endpoint_PUT_USER[/users/{id} PUT]
        Endpoint_DELETE_USER[/users/{id} DELETE]
    end

    subgraph "业务逻辑层"
        Service[User Service]
    end

    subgraph "数据访问层"
        Repo[User Repository]
    end

    subgraph "数据模型层"
        Schema_Pydantic[Pydantic Schemas]
        Model_SQLAlchemy[SQLAlchemy Model]
    end

    subgraph "持久化层"
        DB[(SQLite Database)]
    end

    Client --> Router
    Router --> Endpoint_GET_USERS
    Router --> Endpoint_POST_USERS
    Router --> Endpoint_GET_USER
    Router --> Endpoint_PUT_USER
    Router --> Endpoint_DELETE_USER

    Endpoint_GET_USERS --> Service
    Endpoint_POST_USERS --> Service
    Endpoint_GET_USER --> Service
    Endpoint_PUT_USER --> Service
    Endpoint_DELETE_USER --> Service

    Service --> Repo
    Repo --> Model_SQLAlchemy
    Model_SQLAlchemy --> DB

    Schema_Pydantic -.-> Endpoint_GET_USERS
    Schema_Pydantic -.-> Endpoint_POST_USERS
    Schema_Pydantic -.-> Endpoint_GET_USER
    Schema_Pydantic -.-> Endpoint_PUT_USER
    Schema_Pydantic -.-> Endpoint_DELETE_USER
```

## 环境依赖

本项目需要 Python 3.8 或更高版本。建议使用虚拟环境来管理依赖。

### 1. 创建并激活虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# 在 Windows 上:
venv\Scripts\activate
# 在 macOS/Linux 上:
source venv/bin/activate
```

### 2. 安装项目依赖

```bash
pip install fastapi uvicorn sqlalchemy pydantic[email]
```

## 快速启动

1.  确保你已激活虚拟环境并安装了所有依赖。
2.  在项目根目录下，运行以下命令启动开发服务器：

```bash
uvicorn app.main:app --reload
```

`--reload` 参数使得代码修改后服务器会自动重启，仅用于开发环境。

3.  服务器启动后，默认运行在 `http://127.0.0.1:8000`。
4.  你可以通过访问 `http://127.0.0.1:8000/docs` 来使用自动生成的交互式 API 文档（Swagger UI）。

## 接口说明

服务提供以下 RESTful API 端点：

### 1. 获取用户列表

*   **端点**: `GET /users`
*   **描述**: 检索用户列表，支持分页。
*   **查询参数**:
    *   `skip` (可选, 默认=0): 跳过的记录数，用于分页。
    *   `limit` (可选, 默认=20): 返回的最大记录数，用于分页。
*   **成功响应**: `200 OK`，返回 `UserListResponse` 对象。

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users?skip=0&limit=10' \
  -H 'accept: application/json'
```

### 2. 创建新用户

*   **端点**: `POST /users`
*   **描述**: 创建一个新的用户。
*   **请求体**: `UserCreate` 对象。
*   **成功响应**: `201 Created`，返回创建的 `UserResponse` 对象。

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/users' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "jane_doe",
  "email": "jane@example.com",
  "password": "MyPass123!"
}'
```

### 3. 获取指定用户

*   **端点**: `GET /users/{user_id}`
*   **描述**: 通过用户 ID 获取单个用户的详细信息。
*   **路径参数**:
    *   `user_id` (整数): 用户的唯一标识符。
*   **成功响应**: `200 OK`，返回 `UserResponse` 对象。

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/users/1' \
  -H 'accept: application/json'
```

### 4. 更新指定用户

*   **端点**: `PUT /users/{user_id}`
*   **描述**: 更新指定用户的全部或部分信息。
*   **路径参数**:
    *   `user_id` (整数): 用户的唯一标识符。
*   **请求体**: `UserUpdate` 对象（所有字段可选）。
*   **成功响应**: `200 OK`，返回更新后的 `UserResponse` 对象。

```bash
curl -X 'PUT' \
  'http://127.0.0.1:8000/users/1' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "jane.new@example.com",
  "is_active": false
}'
```

### 5. 删除指定用户

*   **端点**: `DELETE /users/{user_id}`
*   **描述**: 通过用户 ID 删除一个用户。
*   **路径参数**:
    *   `user_id` (整数): 用户的唯一标识符。
*   **成功响应**: `204 No Content`，无返回体。

```bash
curl -X 'DELETE' \
  'http://127.0.0.1:8000/users/1' \
  -H 'accept: application/json'
```