"""POI 数据模型"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


class TransportMode(str, Enum):
    DRIVING = "driving"
    WALKING = "walking"
    TRANSIT = "transit"
    MIXED = "mixed"


class POI(BaseModel):
    id: str
    name: str
    address: str
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    category: str = "景点"
    city: Optional[str] = None
    district: Optional[str] = None
    tel: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    price_level: Optional[int] = Field(None, ge=1, le=4)
    distance_from_center: Optional[float] = None


class POISearchResult(BaseModel):
    keyword: str
    city: str
    total: int
    pois: List[POI] = []


class DistanceInfo(BaseModel):
    from_poi: POI
    to_poi: POI
    mode: TransportMode
    distance_meters: int
    duration_seconds: int
    polyline: Optional[str] = None


class DistanceMatrix(BaseModel):
    pois: List[POI]
    mode: TransportMode
    matrix: List[List[Optional[DistanceInfo]]]
