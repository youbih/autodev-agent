# models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# 声明基类
Base = declarative_base()

class User(Base):
    """
    用户数据模型
    对应数据库中的 users 表
    """
    __tablename__ = "users"
    
    # 主键ID，自增长
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 用户名，唯一且不能为空，用于登录和显示
    username = Column(String(50), unique=True, index=True, nullable=False)
    
    # 邮箱地址，唯一且不能为空，用于用户联系和找回密码
    email = Column(String(100), unique=True, index=True, nullable=False)
    
    # 密码哈希值，存储加密后的密码，不能为空
    # 实际存储的是经过 bcrypt 或类似算法加密的哈希值
    password_hash = Column(String(255), nullable=False)
    
    # 用户状态：True 表示启用，False 表示禁用
    # 默认新用户为启用状态
    is_active = Column(Boolean, default=True)
    
    # 创建时间，自动设置为记录创建的时间
    created_at = Column(DateTime, server_default=func.now())
    
    # 更新时间，每次更新记录时自动更新为当前时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        """对象的字符串表示，便于调试"""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"