"""统一 LLM 调用层，支持多 Provider

支持：DeepSeek / OpenAI / 硅基流动
无 API Key 时降级为规则引擎
"""
import json
import logging
import httpx
from typing import Optional, Dict, Any, Tuple
from app.core.config import get_settings
from app.core.exceptions import AIParseError

logger = logging.getLogger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────
# Provider 元数据（消除重复配置）
# ─────────────────────────────────────────────────────────────
_PROVIDER_META = {
    "deepseek": {
        "api_key_attr": "DEEPSEEK_API_KEY",
        "model_attr": "DEEPSEEK_MODEL",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "label": "DeepSeek",
    },
    "openai": {
        "api_key_attr": "OPENAI_API_KEY",
        "model_attr": "OPENAI_MODEL",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "label": "OpenAI",
    },
    "siliconflow": {
        "api_key_attr": "SILICONFLOW_API_KEY",
        "model_attr": "SILICONFLOW_MODEL",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
        "label": "硅基流动",
    },
    "xiaomi_mimo": {
        "api_key_attr": "XIAOMI_MIMO_API_KEY",
        "model_attr": "XIAOMI_MIMO_MODEL",
        "base_url": "https://api.xiaomimimo.com/v1",
        "default_model": "MiMo-8B",
        "label": "小米Mimo",
    },
}


class LLMProvider:
    """
    统一 LLM 调用层

    根据配置自动选择 Provider，支持：
    - deepseek:     DeepSeek-V3（推荐，性价比最高 $0.27/M）
    - openai:       OpenAI GPT 系列
    - siliconflow:  硅基流动（国内直达，支持 DeepSeek/Qwen）

    无 API Key 时，所有方法抛出异常，由调用方降级为规则引擎。
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.LLM_PROVIDER
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ─────────────────────────────────────────────────────────────
    # 公开接口
    # ─────────────────────────────────────────────────────────────

    async def chat(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """
        统一 chat 接口

        Args:
            prompt:     用户 prompt
            system:     系统提示词
            model:      覆盖默认模型
            temperature: 随机性 0~1
            max_tokens: 最大输出 token 数

        Returns:
            LLM 输出的文本内容

        Raises:
            AIParseError: API 调用失败
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self._call_llm(messages, model, temperature, max_tokens)

    async def chat_json(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        返回 JSON 解析后的 dict（需要 LLM 输出 JSON 格式）
        """
        text = await self.chat(prompt, system, model, temperature)
        json_str = self._extract_json(text)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise AIParseError(f"LLM 返回格式异常，无法解析 JSON: {e}")

    # ─────────────────────────────────────────────────────────────
    # 核心调用逻辑（单一实现，消除 DRY 违规）
    # ─────────────────────────────────────────────────────────────

    async def _call_llm(
        self,
        messages: list[Dict[str, str]],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        统一的 LLM 调用实现，所有 Provider 共用同一套请求/错误处理逻辑
        """
        provider_meta = _PROVIDER_META.get(self.provider)
        if not provider_meta:
            raise AIParseError(f"不支持的 LLM Provider: {self.provider}")

        api_key = getattr(self.settings, provider_meta["api_key_attr"], None)
        if not api_key:
            raise AIParseError(f"{provider_meta['label']} API Key 未配置（{provider_meta['api_key_attr']}）")

        model = model or getattr(self.settings, provider_meta["model_attr"], None) or provider_meta["default_model"]
        base_url = provider_meta["base_url"]
        label = provider_meta["label"]

        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"[LLM] {label} 调用 | model={model} | prompt_len={sum(len(m['content']) for m in messages)}")

        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"[LLM] {label} 成功 | output_len={len(content)}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"[LLM] {label} HTTP错误: {e.response.status_code} | {e.response.text[:200]}")
            raise AIParseError(f"{label} API 调用失败，状态码: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"[LLM] {label} 请求超时")
            raise AIParseError(f"{label} API 响应超时")
        except (KeyError, IndexError) as e:
            logger.error(f"[LLM] {label} 响应解析错误: {e}")
            raise AIParseError(f"{label} 返回格式异常")
        except Exception as e:
            logger.error(f"[LLM] {label} 未知错误: {e}", exc_info=True)
            raise AIParseError(f"{label} 调用失败: {e}")

    # ─────────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(content: str) -> str:
        """从 LLM 响应中提取 JSON 字符串"""
        content = content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]
        return content.strip()