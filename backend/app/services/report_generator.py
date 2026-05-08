"""行程报告生成服务"""
from typing import List, Optional
from app.models.trip import TripIntent, TripPlan, DayPlan, AttractionInDay, HotelRecommendation
from app.models.poi import POI


class ReportGenerator:
    """行程报告生成器

    将优化后的路线和 POI 数据组织为结构化的行程计划。
    """

    def generate(
        self,
        intent: TripIntent,
        route: List[POI],
        segments: List[dict],
        hotels: Optional[List[POI]] = None,
    ) -> TripPlan:
        """生成行程计划

        Args:
            intent: 旅行意图
            route: 优化后的 POI 路线
            segments: 路径段信息
            hotels: 酒店推荐列表

        Returns:
            完整的行程计划
        """
        if hotels is None:
            hotels = []

        day_plans = self._build_day_plans(intent, route, segments)
        hotel_recs = self._build_hotel_recommendations(hotels)

        return TripPlan(
            intent=intent.model_dump(),
            city=intent.city,
            days=intent.days,
            day_plans=day_plans,
            hotels=hotel_recs,
            tips=[
                "建议提前预约热门景点门票",
                "携带身份证，部分景点需实名入场",
                "关注目的地天气，合理安排行程",
            ],
        )

    def _build_day_plans(
        self, intent: TripIntent, route: List[POI], segments: List[dict]
    ) -> List[DayPlan]:
        """按天分配景点并计算时间"""
        attractions_per_day = max(1, len(route) // intent.days)
        day_plans = []

        for day in range(1, intent.days + 1):
            start_idx = (day - 1) * attractions_per_day
            end_idx = min(start_idx + attractions_per_day, len(route))
            day_attractions = route[start_idx:end_idx]

            if not day_attractions and day_plans:
                # 如果景点已分配完，不再生成空的天
                break

            attractions = []
            for i, poi in enumerate(day_attractions):
                arrival_hour = 9 + i * 2
                if arrival_hour >= 20:
                    # 晚于 20:00 不再安排景点
                    break
                attractions.append(AttractionInDay(
                    name=poi.name,
                    poi={"name": poi.name, "lat": poi.lat, "lng": poi.lng},
                    arrival_time=f"{arrival_hour:02d}:00",
                    departure_time=f"{min(arrival_hour + 2, 22):02d}:00",
                    duration_minutes=120,
                ))

            day_plans.append(DayPlan(
                day=day,
                attractions=attractions,
            ))

        return day_plans

    @staticmethod
    def _build_hotel_recommendations(hotels: List[POI]) -> List[HotelRecommendation]:
        """生成酒店推荐"""
        return [
            HotelRecommendation(
                name=h.name,
                address=h.address,
                lat=h.lat,
                lng=h.lng,
                rating=h.rating,
                district=h.district,
                reason="周边景点密集，交通便利",
            )
            for h in hotels[:3]
        ]
