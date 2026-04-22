# schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

# ==================== 基础模型 ====================

class UserBase(BaseModel):
    """用户基础模型，包含用户的基本信息"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名，3-50个字符",
        example="john_doe"
    )
    email: EmailStr = Field(
        ...,
        description="用户邮箱地址",
        example="john@example.com"
    )
    
    @validator('username')
    def validate_username(cls, v):
        """验证用户名格式"""
        if not v.replace('_', '').isalnum():
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

# ==================== 请求模型 ====================

class UserCreate(UserBase):
    """创建用户请求模型"""
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="用户密码，至少8个字符",
        example="SecurePass123!"
    )
    
    @validator('password')
    def validate_password(cls, v):
        """验证密码强度"""
        if v.isnumeric():
            raise ValueError('密码不能全是数字')
        if v.isalpha():
            raise ValueError('密码不能全是字母')
        return v

class UserUpdate(BaseModel):
    """更新用户请求模型（所有字段可选）"""
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="用户名，3-50个字符",
        example="john_doe_updated"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="用户邮箱地址",
        example="john.updated@example.com"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=100,
        description="用户密码，至少8个字符",
        example="NewSecurePass123!"
    )
    is_active: Optional[bool] = Field(
        None,
        description="用户状态：True启用，False禁用",
        example=True
    )

# ==================== 响应模型 ====================

class UserResponse(UserBase):
    """用户响应模型（不包含敏感信息）"""
    id: int = Field(..., description="用户ID", example=1)
    is_active: bool = Field(..., description="用户状态", example=True)
    created_at: datetime = Field(..., description="创建时间", example="2024-01-01T00:00:00Z")
    updated_at: datetime = Field(..., description="更新时间", example="2024-01-01T00:00:00Z")
    
    class Config:
        """Pydantic 配置"""
        orm_mode = True  # 允许从 ORM 对象转换
        schema_extra = {
            "example": {
                "id": 1,
                "username": "john_doe",
                "email": "john@example.com",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: list[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="总用户数", example=100)
    page: int = Field(..., description="当前页码", example=1)
    size: int = Field(..., description="每页数量", example=20)

# ==================== 认证模型 ====================

class UserLogin(BaseModel):
    """用户登录请求模型"""
    username: str = Field(..., description="用户名", example="john_doe")
    password: str = Field(..., description="密码", example="SecurePass123!")