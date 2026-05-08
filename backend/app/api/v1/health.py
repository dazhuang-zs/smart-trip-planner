"""健康检查"""
from fastapi import APIRouter
from app.models.response import HealthResponse

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="Smart Trip Planner", version="1.0.0")


@router.get("/")
async def root():
    return {"name": "Smart Trip Planner", "version": "1.0.0", "docs": "/docs"}
