"""统一 LLM 调用层，支持多 Provider

支持：DeepSeek / OpenAI / 硅基流动
无 API Key 时降级为规则引擎
"""
import json
import logging
import httpx
from typing import Optional, Dict, Any
from app.core.config import get_settings
from app.core.exceptions import AIParseError

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProvider:
    """
    统一 LLM 调用层
    
    根据配置自动选择 Provider，支持：
    - deepseek:     DeepSeek-V3（推荐，性价比最高 $0.27/M）
    - openai:       OpenAI GPT 系列
    - siliconflow:  硅基流动（国内直达，支持 DeepSeek/Qwen）
    
    无 API Key 时，所有方法抛出异常，由调用方降级为规则引擎。
    """

    PROVIDER_CONFIGS = {
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "default_model": "deepseek-chat",
            "auth_header": "Bearer",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "auth_header": "Bearer",
        },
        "siliconflow": {
            "base_url": "https://api.siliconflow.cn/v1",
            "default_model": "deepseek-ai/DeepSeek-V3",
            "auth_header": "Bearer",
        },
    }

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
        if self.provider == "deepseek":
            return await self._deepseek_chat(prompt, system, model, temperature, max_tokens)
        elif self.provider == "openai":
            return await self._openai_chat(prompt, system, model, temperature, max_tokens)
        elif self.provider == "siliconflow":
            return await self._siliconflow_chat(prompt, system, model, temperature, max_tokens)
        else:
            raise AIParseError(f"不支持的 LLM Provider: {self.provider}")

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
    # Provider 实现
    # ─────────────────────────────────────────────────────────────

    async def _deepseek_chat(
        self,
        prompt: str,
        system: str,
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        api_key = self.settings.DEEPSEEK_API_KEY
        if not api_key:
            raise AIParseError("DeepSeek API Key 未配置（DEEPSEEK_API_KEY）")

        config = self.PROVIDER_CONFIGS["deepseek"]
        model = model or self.settings.DEEPSEEK_MODEL or config["default_model"]

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{config['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"[LLM] DeepSeek 调用 | model={model} | prompt_len={len(prompt)}")

        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"[LLM] DeepSeek 成功 | output_len={len(content)}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"[LLM] DeepSeek HTTP错误: {e.response.status_code} | {e.response.text[:200]}")
            raise AIParseError(f"DeepSeek API 调用失败，状态码: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("[LLM] DeepSeek 请求超时")
            raise AIParseError("DeepSeek API 响应超时")
        except (KeyError, IndexError) as e:
            logger.error(f"[LLM] DeepSeek 响应解析错误: {e}")
            raise AIParseError("DeepSeek 返回格式异常")
        except Exception as e:
            logger.error(f"[LLM] DeepSeek 未知错误: {e}", exc_info=True)
            raise AIParseError(f"DeepSeek 调用失败: {e}")

    async def _openai_chat(
        self,
        prompt: str,
        system: str,
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        api_key = self.settings.OPENAI_API_KEY
        if not api_key:
            raise AIParseError("OpenAI API Key 未配置（OPENAI_API_KEY）")

        config = self.PROVIDER_CONFIGS["openai"]
        model = model or self.settings.OPENAI_MODEL or config["default_model"]

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{config['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"[LLM] OpenAI 调用 | model={model} | prompt_len={len(prompt)}")

        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"[LLM] OpenAI 成功 | output_len={len(content)}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"[LLM] OpenAI HTTP错误: {e.response.status_code}")
            raise AIParseError(f"OpenAI API 调用失败，状态码: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("[LLM] OpenAI 请求超时")
            raise AIParseError("OpenAI API 响应超时")
        except (KeyError, IndexError) as e:
            logger.error(f"[LLM] OpenAI 响应解析错误: {e}")
            raise AIParseError("OpenAI 返回格式异常")
        except Exception as e:
            logger.error(f"[LLM] OpenAI 未知错误: {e}", exc_info=True)
            raise AIParseError(f"OpenAI 调用失败: {e}")

    async def _siliconflow_chat(
        self,
        prompt: str,
        system: str,
        model: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        api_key = self.settings.SILICONFLOW_API_KEY
        if not api_key:
            raise AIParseError("硅基流动 API Key 未配置（SILICONFLOW_API_KEY）")

        config = self.PROVIDER_CONFIGS["siliconflow"]
        model = model or self.settings.SILICONFLOW_MODEL or config["default_model"]

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{config['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"[LLM] 硅基流动调用 | model={model} | prompt_len={len(prompt)}")

        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"[LLM] 硅基流动成功 | output_len={len(content)}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"[LLM] 硅基流动HTTP错误: {e.response.status_code} | {e.response.text[:200]}")
            raise AIParseError(f"硅基流动 API 调用失败，状态码: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("[LLM] 硅基流动请求超时")
            raise AIParseError("硅基流动 API 响应超时")
        except (KeyError, IndexError) as e:
            logger.error(f"[LLM] 硅基流动响应解析错误: {e}")
            raise AIParseError("硅基流动返回格式异常")
        except Exception as e:
            logger.error(f"[LLM] 硅基流动未知错误: {e}", exc_info=True)
            raise AIParseError(f"硅基流动调用失败: {e}")

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
