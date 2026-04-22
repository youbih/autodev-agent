# models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# 声明基类
Base = declarative_base()

class User(Base):
    """用户数据模型"""
    __tablename__ = "users"
    
    # 主键ID，自增长
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 用户名，唯一且不能为空，用于登录和显示
    username = Column(String(50), unique=True, nullable=False, index=True)
    
    # 邮箱地址，唯一且不能为空
    email = Column(String(100), unique=True, nullable=False, index=True)
    
    # 全名，可选字段
    full_name = Column(String(100), nullable=True)
    
    # 密码哈希值，存储加密后的密码
    hashed_password = Column(String(255), nullable=False)
    
    # 用户状态，True表示激活，False表示禁用
    is_active = Column(Boolean, default=True)
    
    # 创建时间，自动设置为当前时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 更新时间，每次更新时自动设置为当前时间
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"