#!/usr/bin/env python3
"""
测试弹幕捕获完整流程
"""

import asyncio
import websockets
import json

async def test_danmaku_websocket():
    """测试 WebSocket 弹幕推送"""
    uri = "ws://localhost:9123/ws/danmaku"

    print("🧪 测试 WebSocket 弹幕推送")
    print(f"🔗 连接到: {uri}")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功")

            # 接收消息（等待 10 秒）
            print("\n⏱️  等待弹幕（10 秒）...")
            print("💡 请确保直播弹幕区域有内容\n")

            for i in range(20):
                try:
                    # 等待消息（超时 5 秒）
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)

                    print(f"📩 [{i+1:02d}] 收到消息:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    print("-" * 60)

                except asyncio.TimeoutError:
                    print(f"⏰ [{i+1:02d}] 超时，无新消息")
                    break
                except Exception as e:
                    print(f"❌ 错误: {e}")
                    break

    except ConnectionRefusedError:
        print("❌ 无法连接到 WebSocket")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print("\n" + "=" * 60)
    print("✅ WebSocket 测试完成")


if __name__ == "__main__":
    asyncio.run(test_danmaku_websocket())
