"""行程规划 API"""
from fastapi import APIRouter, Depends
import time
import logging
from app.models.trip import TripGenerationRequest, TripGenerationResponse
from app.models.response import APIResponse
from app.services.ai_parser import AIParserService
from app.services.poi_service import TencentMapService
from app.services.route_optimizer import RouteOptimizer
from app.services.report_generator import ReportGenerator
from app.core.exceptions import TripPlannerException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["行程规划"])


def get_map_service() -> TencentMapService:
    """依赖注入：获取地图服务实例"""
    return TencentMapService()


def get_ai_parser() -> AIParserService:
    """依赖注入：获取 AI 解析服务实例"""
    return AIParserService()


@router.post("/trip/generate", response_model=TripGenerationResponse)
async def generate_trip(
    req: TripGenerationRequest,
    map_svc: TencentMapService = Depends(get_map_service),
    ai: AIParserService = Depends(get_ai_parser),
) -> TripGenerationResponse:
    """生成行程规划

    Args:
        req: 行程生成请求
        map_svc: 地图服务（依赖注入）
        ai: AI 解析服务（依赖注入）

    Returns:
        行程生成响应
    """
    start = time.time()
    try:
        # 1. AI 解析意图
        intent = await ai.parse(req.user_input)

        if req.confirm_intent:
            intent = req.confirm_intent

        # 2. POI 搜索
        pois = []
        for attr in intent.attractions:
            results = await map_svc.search_poi(attr, intent.city, "景点")
            if results:
                pois.append(results[0])

        if not pois:
            return TripGenerationResponse(success=False, error="未找到任何景点", processing_time_ms=0)

        # 3. 路径优化
        optimizer = RouteOptimizer(map_svc)
        route, segments = await optimizer.optimize(pois, mode=intent.transport_mode)

        # 4. 生成报告
        gen = ReportGenerator()
        trip_plan = gen.generate(intent, route, segments, [])

        ms = int((time.time() - start) * 1000)
        return TripGenerationResponse(
            success=True,
            trip_plan=trip_plan,
            intent=intent,
            processing_time_ms=ms,
        )

    except TripPlannerException as e:
        logger.warning(f"业务异常: {e.code} - {e.message}")
        return TripGenerationResponse(success=False, error=e.message, processing_time_ms=0)
    except Exception as e:
        logger.error(f"系统异常: {e}", exc_info=True)
        return TripGenerationResponse(success=False, error="系统内部错误，请稍后重试", processing_time_ms=0)
