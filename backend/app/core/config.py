"""全局配置管理"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """全局配置"""

    APP_NAME: str = "Smart Trip Planner"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── 腾讯地图 API（必填）───────────────────────────────
    TENCENT_MAP_API_KEY: str = ""
    TENCENT_MAP_BASE_URL: str = "https://apis.map.qq.com"

    # ── LLM Provider 配置 ────────────────────────────────
    # 支持: deepseek / openai / siliconflow
    # 三个 Provider 至少配置一个，无配置时使用规则引擎降级
    LLM_PROVIDER: str = "deepseek"  # 默认使用 DeepSeek（性价比最高）

    # DeepSeek（推荐：$0.27/M tokens）
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # OpenAI（需科学上网）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # 硅基流动（国内直达，无需科学上网）
    SILICONFLOW_API_KEY: Optional[str] = None
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_MODEL: str = "deepseek-ai/DeepSeek-V3"

    # ── 缓存配置 ────────────────────────────────────────
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 86400
    CACHE_MAX_SIZE: int = 2000

    # ── 算法参数 ────────────────────────────────────────
    MAX_ATTRACTION_PER_DAY: int = 6
    MAX_TRIP_DAYS: int = 7
    ROUTE_OPTIMIZATION_TIMEOUT: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
