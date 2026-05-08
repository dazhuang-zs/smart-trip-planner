"""腾讯地图 POI 服务"""
import httpx
from typing import List, Optional
from app.models.poi import POI, TransportMode, DistanceInfo, DistanceMatrix
from app.core.exceptions import POISearchError, APIRateLimitError
from app.core.config import get_settings
from app.core.cache import get_poi_cache, get_distance_cache, get_geocode_cache

settings = get_settings()


class TencentMapService:
    """腾讯地图 API 客户端

    注意：使用 httpx.AsyncClient 作为上下文管理器时，每次请求都会创建新连接。
    对于高并发场景，建议使用依赖注入共享 client 实例。
    """

    BASE_URL = "https://apis.map.qq.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TENCENT_MAP_API_KEY
        if not self.api_key:
            raise ValueError("请配置 TENCENT_MAP_API_KEY")
        self._poi_cache = get_poi_cache()
        self._distance_cache = get_distance_cache()
        self._geocode_cache = get_geocode_cache()

    async def search_poi(
        self,
        keyword: str,
        city: str,
        category: str = "景点",
        page_size: int = 10,
    ) -> List[POI]:
        """POI 搜索

        Args:
            keyword: 搜索关键词
            city: 城市名称
            category: POI 类别
            page_size: 每页数量

        Returns:
            POI 列表

        Raises:
            POISearchError: 搜索失败时抛出
        """
        cache_key = f"poi:{keyword}:{city}:{category}"
        cached = self._poi_cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.BASE_URL}/ws/place/v1/search"
        params = {
            "key": self.api_key,
            "keyword": keyword,
            "boundary": f"region({city},0)",
            "page_size": page_size,
            "orderby": "_distance",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            data = resp.json()

        if data.get("status") != 0:
            raise POISearchError(f"搜索失败: {data.get('message')}")

        pois = [
            POI(
                id=p.get("id", ""),
                name=p.get("title", ""),
                address=p.get("address", ""),
                lat=float(p.get("location", {}).get("lat", 0)),
                lng=float(p.get("location", {}).get("lng", 0)),
                category=category,
                city=city,
                rating=float(p.get("rating", 0)) if p.get("rating") else None,
            )
            for p in data.get("data", [])
        ]

        self._poi_cache.set(cache_key, pois)
        return pois

    async def get_distance(
        self,
        from_poi: POI,
        to_poi: POI,
        mode: TransportMode = TransportMode.DRIVING,
    ) -> Optional[DistanceInfo]:
        """计算两点间距离"""
        return await self.get_distance_by_coords(
            from_poi.lat, from_poi.lng, to_poi.lat, to_poi.lng, mode
        )

    async def get_distance_by_coords(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        mode: TransportMode = TransportMode.DRIVING,
    ) -> Optional[DistanceInfo]:
        """通过坐标计算距离"""
        cache_key = f"dist:{from_lat},{from_lng}:{to_lat},{to_lng}:{mode}"
        cached = self._distance_cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.BASE_URL}/ws/distance/v1/matrix"
        params = {
            "key": self.api_key,
            "from": f"{from_lat},{from_lng}",
            "to": f"{to_lat},{to_lng}",
            "mode": mode.value,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=10.0)
                data = resp.json()

            rows = data.get("result", {}).get("rows", [{}])[0]
            elements = rows.get("elements", [{}])[0]

            if elements.get("status") != 0:
                return None

            dist = elements.get("distance", {})
            dur = elements.get("duration", {})

            result = DistanceInfo(
                from_poi=POI(id="", name="起点", lat=from_lat, lng=from_lng, address=""),
                to_poi=POI(id="", name="终点", lat=to_lat, lng=to_lng, address=""),
                mode=mode,
                distance_meters=dist.get("value", 0),
                duration_seconds=dur.get("value", 0),
            )

            self._distance_cache.set(cache_key, result, ttl=3600)
            return result
        except Exception:
            return None

    async def geocode(self, address: str) -> dict:
        """地理编码：地址 → 坐标"""
        cache_key = f"geo:{address}"
        cached = self._geocode_cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.BASE_URL}/ws/geocoder/v1/"
        params = {"key": self.api_key, "address": address}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            data = resp.json()

        if data.get("status") != 0:
            raise POISearchError(f"地理编码失败: {data.get('message')}")

        result = data.get("result", {})
        location = result.get("location", {})
        info = {
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "address": result.get("address"),
            "province": result.get("ad_info", {}).get("province"),
            "city": result.get("ad_info", {}).get("city"),
            "district": result.get("ad_info", {}).get("district"),
        }

        self._geocode_cache.set(cache_key, info)
        return info
