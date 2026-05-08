"""健康检查"""
from fastapi import APIRouter
from app.models.response import HealthResponse
from app.core.config import __version__

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="Smart Trip Planner", version=__version__)


@router.get("/")
async def root():
    return {"name": "Smart Trip Planner", "version": __version__, "docs": "/docs"}
