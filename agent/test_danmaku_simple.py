#!/usr/bin/env python3
"""
简化的弹幕捕获测试（不使用 WebSocket）

测试流程：
1. 启动弹幕捕获
2. 等待 10 秒
3. 检查捕获日志
4. 停止捕获
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:9123"


def check_backend():
    """检查后端是否运行"""
    print("🔍 检查后端服务...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            print("   ✅ 后端运行正常")
            return True
    except:
        pass
    print("   ❌ 后端未运行")
    return False


def test_danmaku_flow():
    """测试弹幕捕获流程"""

    print("\n🧪 弹幕捕获流程测试")
    print("=" * 60)

    # 1. 检查状态
    print("\n📍 步骤 1: 检查初始状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    status = response.json()
    print(f"   Running: {status['running']}")
    print(f"   Region: {status['region']}")

    # 2. 设置截图区域
    print("\n📍 步骤 2: 设置截图区域")
    region = {"x": 100, "y": 100, "width": 600, "height": 400}
    response = requests.post(f"{BASE_URL}/api/danmaku/region", json=region)
    print(f"   ✅ 区域已设置: {response.json()['region']}")

    # 3. 启动捕获
    print("\n▶️  步骤 3: 启动弹幕捕获")
    print("   💡 请在截图区域显示文本内容")
    print("   ⏱️  捕获 10 秒...")

    response = requests.post(f"{BASE_URL}/api/danmaku/start")
    print(f"   Response: {response.json()}")

    # 4. 等待捕获
    print("\n⏳ 步骤 4: 等待捕获...")
    for i in range(10):
        time.sleep(1)
        print(f"   [{i+1:02d}/10] 等待中...", end="\r")

    print("\n   ✅ 捕获完成")

    # 5. 检查状态
    print("\n📍 步骤 5: 检查捕获状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    status = response.json()
    print(f"   Running: {status['running']}")
    print(f"   Region: {status['region']}")

    # 6. 停止捕获
    print("\n⏹️  步骤 6: 停止捕获")
    response = requests.post(f"{BASE_URL}/api/danmaku/stop")
    print(f"   Response: {response.json()}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    print("\n💡 注意: 检查后端日志查看 OCR 识别结果")
    print(f"   日志路径: /tmp/backend.log")


def test_manual_capture():
    """手动测试：截图 + OCR"""
    print("\n🧪 手动截图 + OCR 测试")
    print("=" * 60)

    try:
        # 延迟导入（避免与后端 venv 冲突）
        import sys
        sys.path.insert(0, str(Path(__file__).parent / "agent_core"))

        from danmaku.scraper import DanmakuCapture

        capture = DanmakuCapture(capture_interval=1.0)

        # 设置区域
        capture.set_region(100, 100, 400, 300)

        # 截图
        print("\n📸 截图...")
        img = capture._capture_screenshot()
        print(f"   ✅ 截图成功: {img.shape}")

        # OCR
        print("\n📝 OCR 识别...")
        import asyncio
        texts = asyncio.run(capture._ocr_recognize(img))

        if texts:
            print(f"   ✅ 识别到 {len(texts)} 条文本:")
            for i, text in enumerate(texts, 1):
                print(f"   {i}. {text[:60]}")
        else:
            print("   ⚠️  未识别到文本")

    except Exception as e:
        print(f"   ❌ 错误: {e}")


if __name__ == "__main__":
    if not check_backend():
        print("\n请先启动后端服务:")
        print("  cd /Users/mac/Desktop/textream-cn-master/agent")
        print("  source .venv/bin/activate")
        print("  python run_agent_v2.py")
        exit(1)

    test_danmaku_flow()
    test_manual_capture()
