#!/usr/bin/env python3
"""
完整弹幕捕获流程测试
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent_core.danmaku.scraper import DanmakuCapture


async def test_full_flow():
    """测试完整流程"""
    print("🧪 完整弹幕捕获流程测试")
    print("=" * 60)
    print("💡 请在截图区域显示文本内容")
    print("=" * 60)

    capture = DanmakuCapture(capture_interval=1.0)
    capture.set_region(100, 100, 600, 400)

    # 设置回调
    captured_texts = []

    async def on_danmaku(texts: list[str]):
        print(f"\n📩 收到弹幕 ({len(texts)} 条):")
        for text in texts:
            print(f"  - {text[:80]}")
            captured_texts.append(text)

    capture.set_callback(on_danmaku)

    # 开始捕获
    print("\n▶️  启动捕获（5 轮）...")
    try:
        await asyncio.wait_for(capture.start(), timeout=6.0)
    except asyncio.TimeoutError:
        print("  ⏱️  捕获超时（正常，用于测试）")
    except Exception as e:
        print(f"  ❌ 错误: {e}")

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"✅ 捕获弹幕: {len(captured_texts)} 条")

    if captured_texts:
        print("\n🟢 弹幕捕获功能正常！")
        return True
    else:
        print("\n🟡 未捕获到弹幕（可能是截图区域无内容）")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_full_flow())
    sys.exit(0 if result else 1)
