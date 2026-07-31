"""
LLM 路由层 - 支持多提供商 + 自定义配置 + 自动降级
"""

import json
import os
from typing import Any
from pathlib import Path

from openai import OpenAI

from ..config import get_settings

settings = get_settings()

# 持久化配置路径
_LLM_CONFIG_FILE = Path.home() / ".textream" / "llm_config.json"


# LLM 提供商默认配置（仅作为 fallback 初始值）
DEFAULT_PROVIDERS = {
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen2.5-72B-Instruct",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
    },
}


def _load_persisted_config() -> dict | None:
    """从 ~/.textream/llm_config.json 读取持久化的自定义配置"""
    try:
        if _LLM_CONFIG_FILE.exists():
            return json.loads(_LLM_CONFIG_FILE.read_text())
    except Exception:
        pass
    return None


def _save_persisted_config(config: dict):
    """持久化 LLM 配置到 ~/.textream/llm_config.json"""
    _LLM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LLM_CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))


class LLMRouter:
    """LLM 路由器 — 支持从环境变量 / 持久化文件 / 自定义配置逐级覆盖"""

    def __init__(self, provider: str = "siliconflow"):
        self.provider = provider
        self.api_key = ""
        self.base_url = ""
        self.default_model = ""
        self._apply_config(provider)

    def _apply_config(self, provider: str):
        """按优先级应用配置：持久化 > 环境变量 > 默认"""
        # 1) 尝试从持久化文件加载
        persisted = _load_persisted_config()
        if persisted and persisted.get("provider") == provider:
            self.api_key = persisted.get("api_key", "")
            self.base_url = persisted.get("base_url", "")
            self.default_model = persisted.get("model", "")
            return

        # 2) Fallback：环境变量（兼容旧版命名）
        env_key_map = {
            "siliconflow": "SILICONFLOW_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_key = env_key_map.get(provider)
        if env_key and os.environ.get(env_key):
            self.api_key = os.environ.get(env_key, "")
            default = DEFAULT_PROVIDERS.get(provider, {})
            self.base_url = default.get("base_url", "")
            self.default_model = default.get("default_model", "")
            return

        # 3) 最后 fallback：内置默认
        default = DEFAULT_PROVIDERS.get(provider, {})
        self.base_url = default.get("base_url", "")
        self.default_model = default.get("default_model", "")
        self.api_key = os.environ.get(f"{provider.upper()}_API_KEY", "")

    def update_config(self, provider: str, base_url: str, api_key: str, model: str):
        """动态更新 LLM 配置（运行时生效，自动持久化）"""
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = model

        # 持久化到文件
        _save_persisted_config({
            "provider": provider,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model": self.default_model,
        })

    @property
    def configured(self) -> bool:
        """是否已配置 API Key"""
        return bool(self.api_key)

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
            return "[LLM Error] 未配置 API Key，请在设置中填写"

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
