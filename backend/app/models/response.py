"""通用响应模型"""
from pydantic import BaseModel
from typing import Optional, Any


class APIResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "Smart Trip Planner"
    version: str = "1.0.0"
