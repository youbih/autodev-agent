from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    # 使用 JSON 类型存储用户最喜欢的水果列表，例如 ["苹果", "香蕉"]
    favorite_fruits = Column(JSON, nullable=False, default=list)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', favorite_fruits={self.favorite_fruits})>"