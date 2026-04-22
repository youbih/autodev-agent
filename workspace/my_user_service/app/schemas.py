from pydantic import BaseModel, Field
from typing import List, Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱地址")
    favorite_fruits: List[str] = Field(default_factory=list, description="最喜欢的水果列表")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱地址")
    favorite_fruits: Optional[List[str]] = Field(None, description="最喜欢的水果列表")

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    favorite_fruits: List[str]

    class Config:
        orm_mode = True