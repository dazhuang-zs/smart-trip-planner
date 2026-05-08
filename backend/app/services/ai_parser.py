"""AI 意图解析服务"""
from typing import Optional
import json
import logging
from app.models.trip import TripIntent
from app.core.exceptions import AIParseError
from app.core.config import get_settings
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class AIParserService:
    """AI 意图解析

    通过大模型解析用户的自然语言旅行需求，提取结构化的行程意图。
    当 LLM API 不可用时，降级为简单规则解析。
    """

    SYSTEM_PROMPT = """你是一个旅行规划助手。

用户会输入旅行需求，请提取以下信息并以JSON格式返回：
- city: 城市名（必填）
- days: 天数（必填，数字）
- attractions: 景点列表（必填，数组）
- hotel_area: 住宿区域偏好（可选）
- budget_per_night: 每晚预算（可选，数字，单位元）
- transport_mode: 交通偏好（可选：driving/walking/transit/mixed）

只返回JSON，不要其他内容。"""

    def __init__(self):
        self.llm = LLMProvider()

    async def parse(self, user_input: str) -> TripIntent:
        """解析用户输入

        Args:
            user_input: 用户的自然语言旅行需求

        Returns:
            结构化的行程意图

        Raises:
            AIParseError: 解析失败时抛出
        """
        try:
            return await self._llm_parse(user_input)
        except AIParseError:
            # LLM 不可用，降级为规则解析
            logger.warning("[AIParser] LLM 不可用，降级为规则解析")
            return self._simple_parse(user_input)

    async def _llm_parse(self, user_input: str) -> TripIntent:
        """通过 LLM 解析意图"""
        try:
            response = await self.llm.chat(
                prompt=user_input,
                system=self.SYSTEM_PROMPT,
                temperature=0.3,
            )
            json_str = self._extract_json(response)
            info = json.loads(json_str)
            return TripIntent(**info)
        except AIParseError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"[AIParser] JSON 解析失败: {e}")
            raise AIParseError("AI返回格式异常，请重试")
        except Exception as e:
            logger.error(f"[AIParser] 未知错误: {e}", exc_info=True)
            raise AIParseError("意图解析失败")

    @staticmethod
    def _extract_json(content: str) -> str:
        """从 LLM 响应中提取 JSON 字符串"""
        json_str = content.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        return json_str.strip()

    @staticmethod
    def _simple_parse(user_input: str) -> TripIntent:
        """简单规则解析（无API时用）"""
        import re

        # 提取城市（简化版）
        cities = [
            "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆",
            "西安", "南京", "苏州", "武汉", "厦门", "青岛", "大连",
            "天津", "郑州", "长沙", "昆明", "哈尔滨", "长春",
        ]
        city = None
        for c in cities:
            if c in user_input:
                city = c
                break

        # 提取天数
        day_match = re.search(r"(\d+)天", user_input)
        days = int(day_match.group(1)) if day_match else 3

        # 提取景点（去掉城市名和数字）
        attractions: list[str] = []
        parts = user_input.replace(city or "", "").split("，")
        for p in parts:
            p = p.strip()
            if p and len(p) >= 2 and not re.search(r"\d", p[:2]):
                attractions.append(p[:20])

        return TripIntent(
            city=city or "北京",
            days=days,
            attractions=attractions or ["故宫", "天安门"],
        )
