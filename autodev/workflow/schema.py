from typing import List, Optional
from pydantic import BaseModel, Field

class ProjectSpec(BaseModel):
    project_name: str = Field(..., description="项目的名称，必须是合法的目录名")
    description: str = Field(..., description="项目的简要描述")
    architecture: str = Field("fastapi", description="项目的架构类型，例如 'fastapi' 或 'script'")
    
    # FastAPI 项目特有字段
    framework: Optional[str] = Field(None, description="后端框架")
    database: Optional[str] = Field(None, description="数据库类型，例如 'SQLite + SQLAlchemy'")
    endpoints: Optional[List[str]] = Field(default_factory=list, description="FastAPI 项目的 API 路由列表")
    
    # Script 项目特有字段
    requirements: Optional[str] = Field(None, description="Script 项目的具体需求描述")
    
    # 控制字段
    max_retries: int = Field(3, description="QA 失败时的最大重试次数")
    human_review_enabled: bool = Field(True, description="是否启用人机协同审查")

    model_config = {
        "extra": "allow" # 允许用户在 YAML 里写一些额外字段，不会报错
    }