from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional

# 基础用户模型
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

# 创建用户时的输入模型
class UserCreate(UserBase):
    password: str

# 更新用户时的输入模型
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

# 用户响应模型（API返回）
class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# 数据库用户模型（包含密码）
class UserInDB(UserResponse):
    hashed_password: str