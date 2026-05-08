"""行程数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.poi import TransportMode


class TripIntent(BaseModel):
    city: str
    days: int = Field(..., ge=1, le=14)
    attractions: List[str]
    hotel_area: Optional[str] = None
    budget_per_night: Optional[int] = Field(None, ge=0)
    transport_mode: TransportMode = TransportMode.MIXED
    food_budget_per_day: Optional[int] = None
    extra_notes: Optional[str] = None


class AttractionInDay(BaseModel):
    name: str
    poi: Optional[dict] = None
    arrival_time: str
    departure_time: str
    duration_minutes: int


class DayPlan(BaseModel):
    day: int
    date: Optional[str] = None
    attractions: List[AttractionInDay]
    total_distance_meters: int = 0
    total_duration_minutes: int = 0


class HotelRecommendation(BaseModel):
    name: str
    address: str
    lat: float
    lng: float
    price_per_night: Optional[int] = None
    rating: Optional[float] = None
    distance_from_center: Optional[float] = None
    district: Optional[str] = None
    reason: Optional[str] = None


class TripPlan(BaseModel):
    intent: dict
    city: str
    days: int
    day_plans: List[DayPlan]
    hotels: List[HotelRecommendation] = []
    total_distance_meters: int = 0
    estimated_cost: Optional[int] = None
    tips: List[str] = []


class TripGenerationRequest(BaseModel):
    user_input: str = Field(..., min_length=5)
    start_date: Optional[str] = None
    confirm_intent: Optional[TripIntent] = None


class TripGenerationResponse(BaseModel):
    success: bool
    trip_plan: Optional[TripPlan] = None
    intent: Optional[TripIntent] = None
    error: Optional[str] = None
    processing_time_ms: int = 0
