"""行程规划对话 Agent"""
import json
import logging
from typing import List, Optional, Dict, Any
from app.conversation.store import store
from app.conversation.message import ToolResult
from app.services.poi_service import TencentMapService
from app.services.route_optimizer import RouteOptimizer
from app.services.report_generator import ReportGenerator
from app.services.llm_provider import LLMProvider
from app.models.poi import TransportMode
from app.core.config import get_settings
from app.core.exceptions import AIParseError

logger = logging.getLogger(__name__)
settings = get_settings()

# ============ 工具定义 ============

TOOLS = {
    "search_poi": {
        "name": "search_poi",
        "description": "搜索景点、酒店、餐厅等POI地点",
        "parameters": {
            "keyword": "搜索关键词（如故宫、长城）",
            "city": "城市名（如北京）",
            "category": "POI类别：景点/酒店/餐厅",
        },
    },
    "get_distance": {
        "name": "get_distance",
        "description": "计算两个地点之间的距离和通行时间",
        "parameters": {
            "from_lat": "起点纬度",
            "from_lng": "起点经度",
            "to_lat": "终点纬度",
            "to_lng": "终点经度",
            "mode": "交通方式：driving/walking/transit",
        },
    },
    "confirm_attractions": {
        "name": "confirm_attractions",
        "description": "确认景点列表，准备开始规划路线",
        "parameters": {
            "poi_ids": "要确认的POI ID列表",
        },
    },
    "generate_route": {
        "name": "generate_route",
        "description": "生成完整行程路线（在景点确认后调用）",
        "parameters": {},
    },
}

# ============ Agent 系统提示词 ============

SYSTEM_PROMPT = """你是智能行程规划助手，叫小程。

## 工作流程
你通过调用工具来帮助用户规划旅行。用户可能会：
1. 提出旅行需求
2. 追问、修改、调整行程
3. 询问景点信息

## 对话状态
对话开始时，用户只提供部分信息（城市、天数、景点偏好）。
你需要通过多轮对话逐步完善信息。

## 可用工具
1. search_poi: 搜索景点/酒店/餐厅，返回POI列表
2. get_distance: 计算两地间的距离
3. confirm_attractions: 用户确认景点后，锁定景点列表
4. generate_route: 景点确认后，生成完整行程路线

## 回复风格
- 亲切自然，像朋友聊天
- 不要一次性说太多，让用户逐步确认
- 每轮对话后，给出1-2个建议操作
- 发现信息不足时，主动询问

## 状态机
- initialized: 等待用户输入目的地
- gathering_requirements: 收集信息（城市/天数/景点/住宿）
- searching: 搜索中
- confirming: 等待用户确认景点
- planning: 生成路线中
- completed: 行程已完成

## 输出格式
每次回复必须包含JSON格式：
{
  "message": "你对用户说的话",
  "state": "当前状态",
  "suggestions": ["建议用户下一步操作1", "建议2"],
  "tool_calls": []  // 如需调用工具，填工具名和参数
}
"""


class TripAgent:
    """行程规划对话 Agent

    支持多轮对话，根据用户输入决定：
    1. 调用什么工具
    2. 更新什么状态
    3. 给用户什么回复

    LLM 层通过 LLMProvider 统一调用，支持 DeepSeek / OpenAI / 硅基流动。
    无 LLM 时降级为规则引擎。
    """

    def __init__(self):
        self.map_service = TencentMapService()
        self.optimizer = RouteOptimizer(self.map_service)
        self.report_gen = ReportGenerator()
        self.llm = LLMProvider()

    async def chat(self, message: str, conversation_id: Optional[str] = None) -> dict:
        # 1. 创建或获取对话
        if conversation_id:
            conv = store.get(conversation_id)
            if not conv:
                conversation_id = None

        if not conversation_id:
            result = store.create()
            conversation_id = result["id"]

        # 2. 保存用户消息
        store.add_message(conversation_id, "user", message)

        # 3. 读取对话历史和状态
        state = store.get_state(conversation_id)
        history = store.get_conversation_summary(conversation_id)

        # 4. 调用 AI 决定下一步（优先LLM，降级规则引擎）
        try:
            response = await self._llm_decide(message, state, history)
        except AIParseError:
            logger.warning("[TripAgent] LLM 不可用，降级为规则引擎")
            response = self._rule_based_decide(message, state)

        # 5. 执行工具调用
        tool_results = []
        if response.get("tool_calls"):
            for tc in response["tool_calls"]:
                result = await self._execute_tool(tc["name"], tc.get("arguments", {}))
                tool_results.append(result)

                if tc["name"] == "search_poi" and result["success"]:
                    await self._update_after_search(conversation_id, result, state)

                if tc["name"] == "confirm_attractions" and result["success"]:
                    store.update(conversation_id, state="planning")
                    state["state"] = "planning"

                if tc["name"] == "generate_route" and result["success"]:
                    store.update(conversation_id, state="completed")
                    state["state"] = "completed"

        # 6. 保存助手回复
        reply = response["message"]
        store.add_message(conversation_id, "assistant", reply)

        return {
            "conversation_id": conversation_id,
            "message": reply,
            "state": response.get("state", state.get("state", "initialized")),
            "tool_calls": tool_results,
            "suggestions": response.get("suggestions", []),
        }

    async def _llm_decide(self, message: str, state: dict, history: str) -> dict:
        """通过 LLM 决定下一步操作"""
        current_state = state.get("state", "initialized")
        attractions = state.get("attractions", [])

        prompt = f"""当前状态: {current_state}
对话历史:
{history}

用户最新消息: {message}

已知信息:
- 城市: {state.get('city', '未知')}
- 天数: {state.get('days', '未知')}
- 景点: {attractions}
- 住宿偏好: {state.get('hotel_area', '未指定')}
- 预算: {state.get('budget_per_night', '未指定')}元/晚

请决定下一步操作，输出JSON格式：
{{
  "message": "你对用户说的话（简短亲切）",
  "state": "下一步状态",
  "suggestions": ["建议1", "建议2"],
  "tool_calls": [
    {{"name": "工具名", "arguments": {{"参数": "值"}}}}
  ]
}}

如果没有足够信息（如不知道城市），先用自然语言询问用户。
如果景点已确认且用户要求生成路线，调用generate_route。
"""
        try:
            response = await self.llm.chat(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                temperature=0.7,
            )
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            return json.loads(json_str)
        except AIParseError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"[_llm_decide] JSON解析失败: {e}")
            raise AIParseError("Agent LLM 返回格式异常")
        except Exception as e:
            logger.error(f"[_llm_decide] 未知错误: {e}", exc_info=True)
            raise AIParseError(f"Agent LLM 调用失败: {e}")

    def _rule_based_decide(self, message: str, state: dict) -> dict:
        """基于规则的决策引擎（无API时使用）"""
        import re

        msg = message
        current_state = state.get("state", "initialized")
        attractions = state.get("attractions", [])

        cities = [
            "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆",
            "西安", "南京", "苏州", "武汉", "厦门", "青岛", "大连",
            "天津", "郑州", "长沙", "昆明", "哈尔滨", "长春",
        ]
        found_city = state.get("city")
        if not found_city:
            for c in cities:
                if c in msg:
                    found_city = c
                    break

        day_match = re.search(r"(\d+)天", msg)
        days = state.get("days") or (int(day_match.group(1)) if day_match else None)

        new_attractions = []
        parts = re.split(r"[，,、\n]", msg)
        for p in parts:
            p = p.strip()
            if p and len(p) >= 2 and p not in cities and not re.search(r"\d", p):
                new_attractions.append(p)

        if new_attractions:
            all_attrs = list(dict.fromkeys(attractions + new_attractions))
        else:
            all_attrs = attractions

        if current_state == "initialized" or not found_city:
            return {
                "message": "好的！很高兴帮你规划行程，请告诉我：你想去哪里玩？城市和大概天数是多少？",
                "state": "gathering_requirements",
                "suggestions": ["北京3天", "上海2天外滩城隍庙"],
                "tool_calls": [],
            }

        if found_city and not all_attrs:
            return {
                "message": f"好的！{found_city} {days or ''}天游。你想去哪些景点呢？可以告诉我1-3个你必去的，或者告诉我你喜欢的风格，我来帮你推荐！",
                "state": "gathering_requirements",
                "suggestions": ["故宫、天安门、长城", "外滩、城隍庙、陆家嘴"],
                "tool_calls": [],
            }

        if all_attrs and found_city:
            keyword = all_attrs[0] if all_attrs else found_city
            return {
                "message": f"好的！{found_city} {all_attrs}，我来帮你搜一下这些景点。",
                "state": "searching",
                "suggestions": ["继续补充景点", "确认这些景点，开始规划"],
                "tool_calls": [
                    {"name": "search_poi", "arguments": {
                        "keyword": keyword,
                        "city": found_city,
                        "category": "景点",
                    }}
                ],
            }

        return {
            "message": "我理解了你的需求，让我帮你处理一下...",
            "state": current_state,
            "suggestions": [],
            "tool_calls": [],
        }

    async def _execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """执行工具调用"""
        try:
            if name == "search_poi":
                pois = await self.map_service.search_poi(
                    keyword=arguments.get("keyword", ""),
                    city=arguments.get("city", ""),
                    category=arguments.get("category", "景点"),
                    page_size=5,
                )
                return ToolResult(
                    name=name,
                    success=True,
                    data={"pois": [
                        {"name": p.name, "lat": p.lat, "lng": p.lng,
                         "address": p.address, "rating": p.rating}
                        for p in pois
                    ]},
                )

            elif name == "get_distance":
                info = await self.map_service.get_distance_by_coords(
                    from_lat=arguments["from_lat"],
                    from_lng=arguments["from_lng"],
                    to_lat=arguments["to_lat"],
                    to_lng=arguments["to_lng"],
                    mode=TransportMode(arguments.get("mode", "driving")),
                )
                if info:
                    return ToolResult(
                        name=name,
                        success=True,
                        data={
                            "distance_meters": info.distance_meters,
                            "duration_seconds": info.duration_seconds,
                        },
                    )
                return ToolResult(name=name, success=False, error="距离计算失败")

            elif name == "confirm_attractions":
                poi_ids = arguments.get("poi_ids", [])
                store.update(
                    arguments.get("conversation_id", ""),
                    confirmed_pois=json.dumps(poi_ids),
                    state="planning",
                )
                return ToolResult(name=name, success=True, data={"confirmed": poi_ids})

            elif name == "generate_route":
                cid = arguments.get("conversation_id", "")
                s = store.get_state(cid)
                pois_str = s.get("confirmed_pois", [])
                if isinstance(pois_str, str):
                    pois_list = json.loads(pois_str)
                else:
                    pois_list = pois_str or []

                if not pois_list:
                    return ToolResult(name=name, success=False, error="未确认景点，请先搜索并确认景点")

                all_pois = []
                for poi_info in pois_list:
                    keyword = poi_info.get("name") if isinstance(poi_info, dict) else str(poi_info)
                    results = await self.map_service.search_poi(keyword, s.get("city", ""), "景点")
                    if results:
                        all_pois.append(results[0])

                if not all_pois:
                    return ToolResult(name=name, success=False, error="无法获取景点详情")

                route, segments = await self.optimizer.optimize(
                    pois=all_pois,
                    mode=TransportMode(s.get("transport_mode", "mixed")),
                )

                from app.services.ai_parser import AIParserService
                ai = AIParserService()
                intent = await ai.parse(f"{s.get('city', '')}{s.get('days', 1)}天")
                trip_plan = self.report_gen.generate(intent, route, segments, [])

                return ToolResult(
                    name=name,
                    success=True,
                    data={"trip_plan": trip_plan.model_dump()},
                )

            return ToolResult(name=name, success=False, error=f"未知工具: {name}")

        except Exception as e:
            return ToolResult(name=name, success=False, error=str(e))

    async def _update_after_search(self, conversation_id: str, result: ToolResult, state: dict):
        """搜索后更新状态"""
        pois = result.data.get("pois", [])
        if not pois:
            return
        store.update(
            conversation_id,
            search_results=json.dumps(pois),
            state="confirming",
        )
