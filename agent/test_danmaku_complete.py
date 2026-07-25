#!/usr/bin/env python3
"""
完整弹幕捕获流程测试（后端集成）

测试：
1. 后端服务健康检查
2. 设置截图区域
3. 启动弹幕捕获
4. 验证状态
5. 停止捕获
"""

import sys
import time
import asyncio
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://localhost:9123"


def test_backend_health():
    """测试后端健康状态"""
    print("🔍 测试后端健康状态...")
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


def test_danmaku_api_flow():
    """测试弹幕 API 完整流程"""
    print("\n🧪 测试弹幕 API 流程")
    print("=" * 60)

    # 1. 设置截图区域
    print("\n📍 1. 设置截图区域")
    region = {"x": 100, "y": 100, "width": 600, "height": 400}
    response = requests.post(f"{BASE_URL}/api/danmaku/region", json=region)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 响应: {data}")
    else:
        print(f"   ❌ 失败: {response.status_code}")
        return False

    # 2. 启动捕获
    print("\n📍 2. 启动弹幕捕获")
    response = requests.post(f"{BASE_URL}/api/danmaku/start")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 响应: {data}")
    else:
        print(f"   ❌ 失败: {response.status_code}")
        return False

    # 3. 检查状态
    print("\n📍 3. 检查捕获状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Running: {data['running']}")
        print(f"   ✅ Region (bbox): {data['region']}")
    else:
        print(f"   ❌ 失败: {response.status_code}")
        return False

    # 4. 等待几秒让捕获进行
    print("\n⏳ 等待 5 秒...")
    for i in range(5):
        time.sleep(1)
        print(f"   [{i+1}/5]...", end="\r")
    print("   ✅ 等待完成")

    # 5. 检查最终状态
    print("\n📍 5. 检查最终状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Running: {data['running']}")
        print(f"   ✅ Region: {data['region']}")
    else:
        print(f"   ❌ 失败: {response.status_code}")
        return False

    # 6. 停止捕获
    print("\n📍 6. 停止捕获")
    response = requests.post(f"{BASE_URL}/api/danmaku/stop")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 响应: {data}")
    else:
        print(f"   ❌ 失败: {response.status_code}")
        return False

    # 7. 验证停止状态
    print("\n📍 7. 验证停止状态")
    response = requests.get(f"{BASE_URL}/api/danmaku/status")
    if response.status_code == 200:
        data = response.json()
        if not data["running"]:
            print(f"   ✅ 捕获已停止")
        else:
            print(f"   ⚠️  捕获仍在运行")
    else:
        print(f"   ❌ 失败: {response.status_code}")
        return False

    print("\n" + "=" * 60)
    print("✅ API 流程测试通过")
    return True


async def test_direct_capture():
    """直接测试捕获器"""
    print("\n🧪 测试直接捕获")
    print("=" * 60)

    try:
        from agent_core.danmaku.scraper import DanmakuCapture

        capture = DanmakuCapture(capture_interval=0.5)
        capture.set_region(100, 100, 300, 200)

        print("\n📍 截图 + OCR...")
        texts = await capture._capture_and_ocr()

        if texts:
            print(f"   ✅ 识别到 {len(texts)} 条:")
            for i, text in enumerate(texts[:5], 1):
                print(f"   {i}. {text[:70]}")
        else:
            print("   ⚠️  未识别到文本")

        return len(texts) > 0

    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_backend_log():
    """检查后端日志"""
    print("\n📋 检查后端日志")
    print("=" * 60)

    log_file = Path("/tmp/backend.log")
    if not log_file.exists():
        print("   ⚠️  日志文件不存在")
        return

    logs = log_file.read_text()
    lines = logs.split("\n")

    # 统计
    api_200 = logs.count("200 OK")
    api_500 = logs.count("500 Internal")
    api_errors = logs.count("Error") + logs.count("Traceback")

    print(f"   总行数: {len(lines)}")
    print(f"   API 200: {api_200}")
    print(f"   API 500: {api_500}")
    print(f"   错误数: {api_errors}")

    if api_500 > 0 or api_errors > 0:
        print("\n   ⚠️  发现错误，检查日志...")
        for line in lines:
            if "500" in line or "Error" in line or "Traceback" in line:
                print(f"   ❌ {line}")

    print("\n✅ 日志检查完成")


def main():
    """主函数"""
    print("=" * 60)
    print("🧪 弹幕捕获完整流程测试")
    print("=" * 60)

    # 1. 检查后端
    if not test_backend_health():
        print("\n❌ 后端未运行")
        print("启动命令:")
        print("  cd /Users/mac/Desktop/textream-cn-master/agent")
        print("  source .venv/bin/activate")
        print("  python run_agent_v2.py")
        return False

    # 2. API 流程测试
    if not test_danmaku_api_flow():
        print("\n❌ API 流程测试失败")
        return False

    # 3. 直接捕获测试
    result = asyncio.run(test_direct_capture())
    if not result:
        print("\n⚠️  直接捕获测试未识别到文本")

    # 4. 日志检查
    check_backend_log()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
