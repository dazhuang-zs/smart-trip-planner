"""POI 查询 API"""
from fastapi import APIRouter, Query
from typing import Optional
from app.services.poi_service import TencentMapService
from app.models.response import APIResponse

router = APIRouter(prefix="/api/v1", tags=["POI查询"])


@router.get("/poi/search")
async def search_poi(
    keyword: str = Query(..., description="搜索关键词"),
    city: str = Query(..., description="城市"),
    category: str = Query("景点", description="类别"),
):
    try:
        svc = TencentMapService()
        pois = await svc.search_poi(keyword, city, category)
        return APIResponse(
            data={"keyword": keyword, "city": city, "total": len(pois),
                  "results": [{"name": p.name, "lat": p.lat, "lng": p.lng} for p in pois]}
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))
