from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from app import models, schemas
from app.database import SessionLocal, engine

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="my_user_service", description="基于 FastAPI 的后端服务")

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to my_user_service"}

@app.get("/users", response_model=List[schemas.User], tags=["Users"])
def read_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的最大记录数"),
    db: Session = Depends(get_db)
):
    """获取用户列表（分页支持）"""
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.post("/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """创建新用户"""
    # 检查用户名是否已存在
    db_user_by_username = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 检查邮箱是否已存在
    db_user_by_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 创建用户（这里简化密码处理，实际应该使用哈希）
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=f"hashed_{user.password}",  # 实际应该使用 bcrypt 等库
        is_active=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=schemas.User, tags=["Users"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    """获取指定用户"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}", response_model=schemas.User, tags=["Users"])
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    """更新用户信息"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 更新字段（只更新提供的字段）
    update_data = user_update.dict(exclude_unset=True)
    
    # 如果更新了密码，需要哈希处理
    if "password" in update_data:
        update_data["hashed_password"] = f"hashed_{update_data.pop('password')}"
    
    # 检查用户名唯一性（如果提供了用户名）
    if "username" in update_data and update_data["username"] != db_user.username:
        existing_user = db.query(models.User).filter(
            models.User.username == update_data["username"],
            models.User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # 检查邮箱唯一性（如果提供了邮箱）
    if "email" in update_data and update_data["email"] != db_user.email:
        existing_user = db.query(models.User).filter(
            models.User.email == update_data["email"],
            models.User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # 更新字段
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    # 更新更新时间
    db_user.updated_at = datetime.datetime.now()
    
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """删除用户（软删除）"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 软删除：将 is_active 设置为 False
    db_user.is_active = False
    db_user.updated_at = datetime.datetime.now()
    
    db.commit()
    return None