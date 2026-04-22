# schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """用户基础模型，包含基本用户信息"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名，3-50个字符")
    email: EmailStr = Field(..., description="有效的邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名，可选")
    is_active: bool = Field(default=True, description="用户状态，True为激活")

class UserCreate(UserBase):
    """创建用户请求模型，包含密码字段"""
    password: str = Field(..., min_length=6, max_length=100, description="密码，至少6个字符")

class UserUpdate(BaseModel):
    """更新用户请求模型，所有字段可选"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名，3-50个字符")
    email: Optional[EmailStr] = Field(None, description="有效的邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="密码，至少6个字符")
    is_active: Optional[bool] = Field(None, description="用户状态")

class UserInDB(UserBase):
    """数据库用户模型，包含所有数据库字段"""
    id: int = Field(..., description="用户唯一ID")
    hashed_password: str = Field(..., description="加密后的密码")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        orm_mode = True  # 允许从ORM对象转换

class UserResponse(UserBase):
    """API响应模型，不包含敏感信息"""
    id: int = Field(..., description="用户唯一ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        orm_mode = True