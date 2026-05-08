"""自定义异常定义"""
from fastapi import HTTPException, status


class TripPlannerException(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def to_http(self) -> HTTPException:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": self.code, "message": self.message})


class AIParseError(TripPlannerException):
    def __init__(self, message: str = "AI意图解析失败"):
        super().__init__(message, "AI_PARSE_ERROR")


class POISearchError(TripPlannerException):
    def __init__(self, message: str = "POI搜索失败"):
        super().__init__(message, "POI_SEARCH_ERROR")


class POINotFoundError(TripPlannerException):
    def __init__(self, poi_name: str):
        super().__init__(f"未找到POI: {poi_name}", "POI_NOT_FOUND")


class RouteOptimizationError(TripPlannerException):
    def __init__(self, message: str = "路径优化失败"):
        super().__init__(message, "ROUTE_ERROR")


class APIRateLimitError(TripPlannerException):
    def __init__(self, api_name: str):
        super().__init__(f"{api_name} API调用超出限制", "RATE_LIMIT")


class InvalidInputError(TripPlannerException):
    def __init__(self, message: str):
        super().__init__(message, "INVALID_INPUT")


class NetworkError(TripPlannerException):
    def __init__(self, message: str = "网络连接异常"):
        super().__init__(message, "NETWORK_ERROR")
