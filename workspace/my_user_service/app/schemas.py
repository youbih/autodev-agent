# schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名")

class UserCreate(UserBase):
    """创建用户请求"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")

class UserUpdate(BaseModel):
    """更新用户请求（所有字段可选）"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="密码")
    is_active: Optional[bool] = Field(None, description="是否激活")

class UserResponse(UserBase):
    """用户响应"""
    id: int = Field(..., description="用户ID")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """用户列表响应"""
    users: List[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="用户总数")