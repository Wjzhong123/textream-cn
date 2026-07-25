#!/usr/bin/env python3
"""
Direct danmaku capture test (no websockets, no requests)
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent_core.danmaku.scraper import DanmakuCapture


async def test():
    print("🧪 直接测试 DanmakuCapture")
    print("=" * 60)

    capture = DanmakuCapture(capture_interval=0.5)

    # Set region
    capture.set_region(100, 100, 400, 300)

    # Capture once
    print("\n📸 截图...")
    img = capture._capture_screenshot()
    print(f"   Shape: {img.shape}")

    # OCR
    print("\n📝 OCR 识别...")
    texts = await capture._ocr_recognize(img)

    if texts:
        print(f"   ✅ 识别到 {len(texts)} 条:")
        for i, t in enumerate(texts, 1):
            print(f"   {i}. {t[:80]}")
    else:
        print("   ⚠️  未识别到文本")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test())
