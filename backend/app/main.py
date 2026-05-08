"""FastAPI 应用入口"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import trip, poi, health
from app.conversation import api as conversation_api
from app.core.exceptions import TripPlannerException
from app.core.config import get_settings
import logging

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="智能行程规划助手 API",
    description="AI驱动的旅行规划工具，基于腾讯地图 + QClaw，支持多轮对话",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件（修复安全配置）
origins = getattr(settings, "CORS_ORIGINS", None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TripPlannerException)
async def trip_planner_exception_handler(request: Request, exc: TripPlannerException):
    return JSONResponse(
        status_code=400,
        content={"code": exc.code, "message": exc.message},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": "SYSTEM_ERROR", "message": "系统内部错误"},
    )

# 注册路由
app.include_router(health.router)
app.include_router(trip.router)
app.include_router(poi.router)
app.include_router(conversation_api.router)


@app.get("/")
async def root():
    return {
        "name": "Smart Trip Planner",
        "version": "1.1.0",
        "docs": "/docs",
        "endpoints": {
            # 单轮模式
            "generate_trip": "POST /api/v1/trip/generate",
            "search_poi": "GET /api/v1/poi/search",
            # 多轮对话模式（新增）
            "chat": "POST /api/v1/conversation/chat",
            "history": "GET /api/v1/conversation/history/{conversation_id}",
            "delete_chat": "DELETE /api/v1/conversation/{conversation_id}",
            "health": "GET /api/v1/health",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
