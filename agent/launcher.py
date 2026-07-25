#!/usr/bin/env python3
"""直播AI军师 Launcher - 常驻进程，Dock 图标不会退出"""

import os
import sys
import signal
import subprocess
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
AGENT_DIR = BASE_DIR / "agent"
FRONTEND_DIR = BASE_DIR / "web-console" / "dist"
VENV_PYTHON = BASE_DIR / "agent" / ".venv" / "bin" / "python"

processes = []

def cleanup(signum=None, frame=None):
    """退出时清理所有子进程"""
    for p in processes:
        if p.poll() is None:
            try:
                p.terminate()
                p.wait(timeout=3)
            except:
                try:
                    p.kill()
                except:
                    pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

def main():
    # 1. 启动后端 (port 9123)
    env = os.environ.copy()
    env["CAPTIOCR_ENABLED"] = "true"
    env["PYTHONPATH"] = ""
    
    backend_cmd = [
        str(VENV_PYTHON),
        str(AGENT_DIR / "run_agent_v2.py")
    ]
    
    print("[启动] 后端服务 (port 9123)...")
    p_backend = subprocess.Popen(
        backend_cmd,
        cwd=str(AGENT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(p_backend)
    
    # 等待后端启动
    time.sleep(2)
    
    # 2. 启动前端文件服务 (port 3000)
    print("[启动] 前端服务 (port 3000)...")
    frontend_cmd = [
        str(VENV_PYTHON),
        "-m", "http.server", "3000",
        "--directory", str(FRONTEND_DIR)
    ]
    p_frontend = subprocess.Popen(
        frontend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(p_frontend)
    
    # 3. 打开浏览器
    print("[启动] 打开浏览器 http://localhost:3000")
    webbrowser.open("http://localhost:3000")
    
    # 4. 保持运行 - 直到用户退出
    print("[运行中] 直播AI军师已启动")
    print("[运行中] 按 Ctrl+C 或从 Dock 退出")
    try:
        while True:
            time.sleep(1)
            # 检查子进程是否存活
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"[警告] 子进程 {i} 已退出，退出码: {p.returncode}")
                    cleanup()
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()