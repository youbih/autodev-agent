from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Base schema with common fields
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    
    class Config:
        from_attributes = True

# Schema for creating a new user
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="密码")

# Schema for updating user (all fields optional)
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="密码")
    is_active: Optional[bool] = Field(None, description="是否激活")
    
    class Config:
        from_attributes = True

# Schema for user in database (includes hashed password)
class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schema for API responses (excludes sensitive data)
class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True