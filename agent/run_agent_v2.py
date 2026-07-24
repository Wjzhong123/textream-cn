#!/usr/bin/env python3
"""
Textream Agent Core v2.0 - 启动脚本

用法：
    # 从 agent/ 目录运行
    cd /Users/mac/Desktop/textream-cn-master/agent
    python run_agent_v2.py

    # 或使用 uvicorn
    uvicorn agent.agent_core.server:create_app --host 0.0.0.0 --port 9123
"""

import sys
from pathlib import Path

# 添加 agent 目录到 Python 路径
agent_dir = Path(__file__).parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

import uvicorn

# 直接导入（不使用相对导入）
from agent_core.config import get_settings

settings = get_settings()


if __name__ == "__main__":
    print(f"🤖 Textream Agent Core v2.0")
    print(f"   Port: {settings.agent_port}")
    print(f"   LLM: {settings.llm_provider}")

    uvicorn.run(
        "agent_core.server:create_app",
        host="0.0.0.0",
        port=settings.agent_port,
        reload=False,  # 关闭热重载（避免 import 路径问题）
        log_level="info",
    )
