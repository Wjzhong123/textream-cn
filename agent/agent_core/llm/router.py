"""
LLM 路由层 - 支持多提供商 + 自动降级
"""

import os
from typing import Any

from openai import OpenAI

from ..config import get_settings

settings = get_settings()


# LLM 提供商配置
PROVIDERS = {
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "env_key": "SILICONFLOW_API_KEY",
        "default_model": "Qwen/Qwen2.5-72B-Instruct",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-sonnet-20241022",
    },
}


class LLMRouter:
    """LLM 路由器"""

    def __init__(self, provider: str = "siliconflow"):
        self.provider = provider
        self.config = PROVIDERS.get(provider, PROVIDERS["siliconflow"])
        self.api_key = os.environ.get(self.config["env_key"], "")
        self.base_url = self.config["base_url"]
        self.default_model = self.config["default_model"]

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称（默认使用提供商默认模型）
            max_tokens: 最大生成长度
            temperature: 温度参数

        Returns:
            LLM 回复文本
        """
        if not self.api_key:
            return "[LLM Error] 未配置 API Key，请在环境变量中设置"

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            resp = client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"[LLM Error] {e}"

    def chat_with_system(
        self,
        user_message: str,
        system_prompt: str = "",
        **kwargs,
    ) -> str:
        """便捷方法：带系统提示词的聊天"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages, **kwargs)


def get_llm_router(provider: str | None = None) -> LLMRouter:
    """获取 LLM 路由器实例"""
    provider = provider or settings.llm_provider
    return LLMRouter(provider=provider)
