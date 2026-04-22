# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal, engine
from app.models import Base, User
from app.schemas import UserCreate, UserUpdate, UserResponse, UserListResponse

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="My User Service",
    description="基于 FastAPI 的用户服务后端",
    version="1.0.0"
)

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 辅助函数：将 User 模型转换为 UserResponse
def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

# 辅助函数：获取用户或抛出 404 异常
def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID {user_id} 不存在"
        )
    return user

@app.get("/users", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(db: Session = Depends(get_db)):
    """获取所有用户列表"""
    users = db.query(User).all()
    user_responses = [user_to_response(user) for user in users]
    return UserListResponse(users=user_responses, total=len(users))

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已被注册"
        )

    # 创建用户（实际项目中应使用密码哈希，此处简化处理）
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=user_data.password,  # 注意：生产环境应使用哈希
        full_name=user_data.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return user_to_response(new_user)

@app.get("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """根据 ID 获取用户详情"""
    user = get_user_or_404(db, user_id)
    return user_to_response(user)

@app.put("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """更新用户信息（部分更新）"""
    user = get_user_or_404(db, user_id)

    # 检查用户名/邮箱是否与其他用户冲突
    if user_data.username is not None:
        conflict = db.query(User).filter(
            User.username == user_data.username,
            User.id != user_id
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被其他用户使用"
            )
        user.username = user_data.username

    if user_data.email is not None:
        conflict = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被其他用户使用"
            )
        user.email = user_data.email

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.password is not None:
        user.password_hash = user_data.password  # 注意：生产环境应使用哈希

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)
    return user_to_response(user)

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户"""
    user = get_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
    return None