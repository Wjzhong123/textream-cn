"""
配置管理
"""

import os
from pathlib import Path
from typing import Any

# 数据目录
DATA_DIR = Path.home() / ".textream"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# LLM 配置
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "siliconflow")
LLM_MODEL = os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

# 服务器端口
AGENT_PORT = int(os.environ.get("AGENT_PORT", "9123"))

# 记忆配置
MEMORY_ENABLED = os.environ.get("MEMORY_ENABLED", "true").lower() == "true"

# 知识库配置
KNOWLEDGE_ENABLED = os.environ.get("KNOWLEDGE_ENABLED", "true").lower() == "true"


class Settings:
    """配置类（实例属性，避免隐式全局可变状态）"""

    def __init__(self):
        self.data_dir: Path = DATA_DIR
        self.llm_provider: str = LLM_PROVIDER
        self.llm_model: str = LLM_MODEL
        self.agent_port: int = AGENT_PORT
        self.memory_enabled: bool = MEMORY_ENABLED
        self.knowledge_enabled: bool = KNOWLEDGE_ENABLED

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self, key, default)


def get_settings() -> Settings:
    """获取配置实例"""
    return Settings()
