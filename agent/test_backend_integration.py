#!/usr/bin/env python3
"""
后端集成测试 - 弹幕捕获流程

测试 API 端点到捕获器的完整流程
"""

import sys
import time
import asyncio
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://localhost:9123"


def check_backend():
    """检查后端状态"""
    print("🔍 检查后端服务...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 后端运行正常")
            print(f"   Version: {data.get('version')}")
            return True
    except Exception as e:
        print(f"   ❌ 后端未运行: {e}")
    return False


def test_api_flow():
    """测试 API 流程"""
    print("\n🧪 API 流程测试")
    print("=" * 60)

    # 1. 检查初始状态
    print("\n📍 1. 检查初始状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    status = response.json()
    print(f"   Running: {status['running']}")
    print(f"   Region: {status['region']}")

    # 2. 设置截图区域
    print("\n📍 2. 设置截图区域")
    region = {"x": 100, "y": 100, "width": 600, "height": 400}
    response = requests.post(f"{BASE_URL}/api/danmaku/region", json=region)
    print(f"   ✅ 响应: {response.json()}")

    # 3. 启动捕获
    print("\n📍 3. 启动捕获")
    print("   ⏱️  捕获 8 秒...")
    response = requests.post(f"{BASE_URL}/api/danmaku/start")
    print(f"   ✅ 响应: {response.json()}")

    # 4. 等待并检查状态
    print("\n📍 4. 等待捕获...")
    for i in range(8):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/api/danmaku/status")
        status = response.json()
        print(f"   [{i+1:02d}/08] Running: {status['running']}", end="\r")

    print(f"\n   ✅ 捕获完成")

    # 5. 检查最终状态
    print("\n📍 5. 检查最终状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    status = response.json()
    print(f"   Running: {status['running']}")
    print(f"   Region: {status['region']}")

    # 6. 停止捕获
    print("\n📍 6. 停止捕获")
    response = requests.post(f"{BASE_URL}/api/danmaku/stop")
    print(f"   ✅ 响应: {response.json()}")

    print("\n" + "=" * 60)
    print("✅ API 流程测试完成")


def test_direct_capture():
    """直接测试捕获器"""
    print("\n🧪 直接测试捕获器")
    print("=" * 60)

    try:
        from agent_core.danmaku.scraper import DanmakuCapture

        capture = DanmakuCapture(capture_interval=1.0)
        capture.set_region(100, 100, 400, 300)

        print("\n📍 测试截图...")
        import asyncio

        async def test():
            # 截图
            print("   截图中...")
            screenshot_path = await capture._capture_screenshot()
            print(f"   ✅ 截图: {screenshot_path}")

            # OCR
            print("   OCR 识别中...")
            texts = await capture._ocr_recognize(screenshot_path)

            # 清理
            Path(screenshot_path).unlink(missing_ok=True)

            if texts:
                print(f"   ✅ 识别到 {len(texts)} 条:")
                for i, text in enumerate(texts, 1):
                    print(f"   {i}. {text[:70]}")
            else:
                print("   ⚠️  未识别到文本")

            return len(texts) > 0

        result = asyncio.run(test())

        if result:
            print("\n🟢 直接测试通过")
        else:
            print("\n🟡 未捕获到文本")

    except Exception as e:
        print(f"\n❌ 直接测试失败: {e}")
        import traceback
        traceback.print_exc()


def check_backend_log():
    """检查后端日志"""
    print("\n📋 后端日志分析")
    print("=" * 60)

    log_file = Path("/tmp/backend.log")
    if not log_file.exists():
        print("   ⚠️  日志文件不存在")
        return

    lines = log_file.read_text().split('\n')
    print(f"   总行数: {len(lines)}")

    # 检查关键日志
    capture_logs = [l for l in lines if 'DanmakuCapture' in l or 'OCR' in l or 'capture' in l]
    error_logs = [l for l in lines if 'Error' in l or 'error' in l or 'Traceback' in l]

    print(f"   捕获日志: {len(capture_logs)} 行")
    print(f"   错误日志: {len(error_logs)} 行")

    if capture_logs:
        print("\n   最近的捕获日志:")
        for log in capture_logs[-5:]:
            print(f"   {log}")

    if error_logs:
        print("\n   最近的错误日志:")
        for log in error_logs[-5:]:
            print(f"   ❌ {log}")

    print("\n✅ 日志分析完成")


if __name__ == "__main__":
    print("🎬 后端集成测试 - 弹幕捕获流程\n")

    if not check_backend():
        print("\n❌ 后端未运行，请先启动后端服务")
        print("   cd /Users/mac/Desktop/textream-cn-master/agent")
        print("   source .venv/bin/activate")
        print("   python run_agent_v2.py")
        sys.exit(1)

    test_api_flow()
    test_direct_capture()
    check_backend_log()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)
