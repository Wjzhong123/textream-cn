#!/usr/bin/env python3
"""
完整测试：弹幕捕获 + WebSocket 推送

测试流程：
1. 启动后端服务
2. 设置截图区域
3. 启动弹幕捕获
4. 接收 WebSocket 推送
5. 停止捕获并验证
"""

import sys
import time
import asyncio
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://localhost:9123"
WS_URL = "ws://localhost:9123/ws/danmaku"

import websockets
import json
import os

# 绕过系统代理
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('all_proxy', None)


async def test_danmaku_capture_flow():
    """测试完整弹幕捕获流程"""

    print("🧪 弹幕捕获完整流程测试")
    print("=" * 60)
    print("💡 请在弹幕区域显示一些文本内容")
    print("=" * 60)

    ws_messages = []

    try:
        # 1. 设置截图区域
        print("\n📍 步骤 1: 设置截图区域")
        region = {"x": 100, "y": 100, "width": 600, "height": 400}
        response = requests.post(f"{BASE_URL}/api/danmaku/region", json=region)
        print(f"   Status: {response.status_code}")
        print(f"   Region: {response.json()['region']}")

        # 2. 连接 WebSocket
        print("\n🔗 步骤 2: 连接 WebSocket")
        async with websockets.connect(WS_URL) as websocket:
            print("   ✅ WebSocket 已连接")

            # 3. 启动弹幕捕获
            print("\n▶️  步骤 3: 启动弹幕捕获")
            response = requests.post(f"{BASE_URL}/api/danmaku/start")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")

            # 4. 接收消息
            print("\n📡 步骤 4: 接收弹幕（15 秒）")
            print("-" * 60)

            capture_count = 0
            start_time = time.time()

            while time.time() - start_time < 15:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)

                    if "error" in data:
                        print(f"   ❌ Error: {data['error']}")
                        continue

                    if "danmaku" in data:
                        capture_count += 1
                        print(f"\n   📩 弹幕 #{capture_count}:")
                        print(f"      Time: {data.get('timestamp', 'N/A')}")
                        print(f"      Text: {data['danmaku'][:100]}")

                        if "ocr_confidence" in data:
                            print(f"      OCR: {data['ocr_confidence']:.2%}")

                        if "styles" in data:
                            print(f"      Styles: {list(data['styles'].keys())}")

                        ws_messages.append(data)

                except asyncio.TimeoutError:
                    if capture_count > 0:
                        print(f"\n   ⏳ 等待新弹幕... ({capture_count} 条已接收)")
                except Exception as e:
                    print(f"   ❌ 错误: {e}")
                    break

            # 5. 停止捕获
            print("\n⏹️  步骤 5: 停止捕获")
            response = requests.post(f"{BASE_URL}/api/danmaku/stop")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")

            # 6. 验证状态
            print("\n✅ 步骤 6: 验证状态")
            response = requests.get(f"{BASE_URL}/api/danmaku/status")
            status = response.json()
            print(f"   Running: {status['running']}")
            print(f"   Region: {status['region']}")

    except ConnectionRefusedError:
        print("   ❌ 无法连接到服务器")
        return False
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return False

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"✅ 捕获弹幕: {capture_count} 条")
    print(f"✅ WebSocket 消息: {len(ws_messages)} 条")
    print(f"✅ 后端服务: 运行中")

    if capture_count > 0:
        print("\n🟢 弹幕捕获功能正常")
        return True
    else:
        print("\n🟡 未捕获到弹幕（可能是截图区域无内容）")
        return False


def test_api_endpoints():
    """测试 API 端点"""
    print("\n🧪 API 端点测试")
    print("=" * 60)

    endpoints = [
        ("GET", "/api/health", None),
        ("GET", "/api/danmaku/status", None),
        ("POST", "/api/danmaku/region", {"x": 0, "y": 0, "width": 100, "height": 100}),
        ("GET", "/api/memory/list", None),
        ("GET", "/api/knowledge/list", None),
    ]

    for method, endpoint, data in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json=data)

            status_icon = "✅" if response.status_code == 200 else "❌"
            print(f"{status_icon} {method} {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint}: {e}")

    print("=" * 60)


if __name__ == "__main__":
    # 测试 API 端点
    test_api_endpoints()

    # 测试弹幕捕获流程
    result = asyncio.run(test_danmaku_capture_flow())

    sys.exit(0 if result else 1)
