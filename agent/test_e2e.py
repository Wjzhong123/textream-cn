#!/usr/bin/env python3
"""
完整端到端测试 - 弹幕捕获流程

演示：
1. 启动后端服务
2. 设置截图区域
3. 启动弹幕捕获
4. 实时监控日志
5. 停止捕获
6. 验证结果
"""

import subprocess
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:9123"
LOG_FILE = "/tmp/danmaku_test.log"


def start_backend():
    """启动后端服务"""
    print("🚀 启动后端服务...")
    subprocess.Popen(
        ["bash", "-c", "cd /Users/mac/Desktop/textream-cn-master/agent && source .venv/bin/activate && python run_agent_v2.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(5)

    # 验证
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            print("   ✅ 后端启动成功")
            return True
    except:
        pass
    print("   ❌ 后端启动失败")
    return False


def set_region():
    """设置截图区域"""
    print("\n📍 设置截图区域...")
    region = {"x": 100, "y": 100, "width": 600, "height": 400}
    response = requests.post(f"{BASE_URL}/api/danmaku/region", json=region)
    if response.status_code == 200:
        print(f"   ✅ 区域已设置: {response.json()['region']}")
        return True
    print("   ❌ 设置失败")
    return False


def start_capture():
    """启动弹幕捕获"""
    print("\n▶️  启动弹幕捕获...")
    response = requests.post(f"{BASE_URL}/api/danmaku/start")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ {data.get('status', 'started')}")

        # 等待 1 秒让捕获开始
        time.sleep(1)

        # 检查状态
        status = requests.get(f"{BASE_URL}/api/danmaku/status").json()
        if status.get("running"):
            print("   ✅ 捕获正在运行")
            return True
    print("   ❌ 启动失败")
    return False


def monitor_capture(duration: int = 10):
    """监控捕获过程"""
    print(f"\n📡 监控捕获（{duration} 秒）...")
    print("   💡 请在截图区域显示文本内容")

    for i in range(duration):
        time.sleep(1)
        status = requests.get(f"{BASE_URL}/api/danmaku/status").json()
        print(f"   [{i+1:02d}/{duration:02d}] Running: {status.get('running')}", end="\r")

    print(f"\n   ✅ 监控完成")


def stop_capture():
    """停止弹幕捕获"""
    print("\n⏹️  停止捕获...")
    response = requests.post(f"{BASE_URL}/api/danmaku/stop")
    if response.status_code == 200:
        print(f"   ✅ {response.json().get('status', 'stopped')}")
        return True
    print("   ❌ 停止失败")
    return False


def check_logs():
    """检查后端日志"""
    print("\n📋 检查后端日志...")

    log_file = Path("/tmp/backend.log")
    if not log_file.exists():
        print("   ⚠️  日志文件不存在")
        return

    logs = log_file.read_text()

    # 统计
    capture_count = logs.count("[DanmakuCapture] 开始捕获弹幕")
    ocr_count = logs.count("OCR 识别")
    process_count = logs.count("[DanmakuProcessor] 处理弹幕")
    error_count = logs.count("Error") + logs.count("Traceback")

    print(f"   捕获次数: {capture_count}")
    print(f"   OCR 次数: {ocr_count}")
    print(f"   处理弹幕: {process_count}")
    print(f"   错误数: {error_count}")

    # 提取关键日志
    print("\n   关键日志:")
    for line in logs.split('\n'):
        if 'DanmakuCapture' in line or 'DanmakuProcessor' in line or 'OCR' in line:
            if 'INFO' in line or 'ERROR' in line:
                print(f"   {line}")


def main():
    """主流程"""
    print("=" * 60)
    print("🎬 完整端到端测试 - 弹幕捕获流程")
    print("=" * 60)

    # 1. 启动后端
    if not start_backend():
        return False

    # 2. 设置区域
    if not set_region():
        return False

    # 3. 启动捕获
    if not start_capture():
        return False

    # 4. 监控
    monitor_capture(duration=8)

    # 5. 停止
    if not stop_capture():
        return False

    # 6. 检查日志
    check_logs()

    print("\n" + "=" * 60)
    print("✅ 端到端测试完成")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
