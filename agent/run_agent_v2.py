#!/usr/bin/env python3
"""
Textream Agent Core v2.0 - 启动脚本

启动后自动打开 Web Console (http://localhost:9123)，
弹幕捕获功能在 Web Console 的「弹幕监控」面板中。

用法：
    cd /Users/mac/Desktop/textream-cn-master/agent
    python run_agent_v2.py
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# 添加 agent 目录到 Python 路径
agent_dir = Path(__file__).parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

# 添加 CaptiOCR vendor 路径
vendor_captiocr = str(agent_dir / "vendor" / "captiocr")
if vendor_captiocr not in sys.path:
    sys.path.insert(0, vendor_captiocr)

import uvicorn

# 直接导入（不使用相对导入）
from agent_core.config import get_settings

settings = get_settings()


def _open_browser_later(port: int, delay: float = 3.0):
    """延迟打开浏览器（等待服务器就绪）"""
    def _open():
        time.sleep(delay)
        url = f"http://localhost:{port}"
        print(f"   🌐 正在打开 Web Console: {url}")
        webbrowser.open(url)
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


if __name__ == "__main__":
    # 检测 CaptiOCR 是否可用
    _captiocr_available = (agent_dir / "vendor" / "captiocr" / "captiocr").is_dir()
    _captiocr_enabled = os.environ.get("CAPTIOCR_ENABLED", "").lower() == "true"

    print(f"🤖 Textream Agent Core v2.0")
    print(f"   Port: {settings.agent_port}")
    print(f"   LLM: {settings.llm_provider}")
    print(f"   CaptiOCR: {'🟢 可用' if _captiocr_available else '🔴 未安装'}" +
          f" {'（已启用）' if _captiocr_enabled else '（默认 DirectorServer）'}")
    print(f"   🌐 Web Console: http://localhost:{settings.agent_port}")
    print()
    print(f"   📋 使用说明：")
    print(f"      1. 浏览器自动打开（或手动访问 http://localhost:{settings.agent_port}）")
    print(f"      2. 点击「📐 读取屏幕」→ 框选弹幕区域")
    print(f"      3. 点击「▶ 开始捕获」→ 自动识别弹幕 ✅")
    print(f"      4. 弹幕出现后点击「💬」生成救场话术")
    print()

    # 自动打开浏览器
    _open_browser_later(settings.agent_port)

    uvicorn.run(
        "agent_core.server:create_app",
        host="0.0.0.0",
        port=settings.agent_port,
        reload=False,  # 关闭热重载（避免 import 路径问题）
        log_level="info",
    )