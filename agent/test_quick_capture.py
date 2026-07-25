#!/usr/bin/env python3
"""
快速测试：截图 + OCR（无 cv2）
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'agent_core'))

import mss
import numpy as np
import pytesseract
from PIL import Image
from danmaku.scraper import DanmakuCapture


def test_quick():
    """快速测试"""
    print("🧪 快速截图 + OCR 测试")
    print("=" * 60)

    # 截图
    print("\n📸 截图...")
    with mss.mss() as sct:
        region = {'top': 100, 'left': 100, 'width': 300, 'height': 150}
        screenshot = sct.grab(region)
        img = np.array(screenshot)
        print(f"   Shape: {img.shape}")

    # OCR
    print("\n📝 OCR 识别...")
    pil_img = Image.frombytes('RGB', (img.shape[1], img.shape[0]), img[:, :, :3].tobytes(), 'raw')
    text = pytesseract.image_to_string(pil_img, lang='chi_sim+eng')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    print(f"   ✅ 识别到 {len(lines)} 行:")
    for i, line in enumerate(lines[:5], 1):
        print(f"   {i}. {line[:70]}")

    print("\n✅ 测试完成")


async def test_danmaku_capture():
    """测试 DanmakuCapture"""
    print("\n🧪 DanmakuCapture 测试")
    print("=" * 60)

    capture = DanmakuCapture(capture_interval=1.0)
    capture.set_region(100, 100, 300, 150)

    # 截图
    print("\n📸 截图...")
    img = capture._capture_screenshot()
    print(f"   Shape: {img.shape}")

    # OCR
    print("\n📝 OCR 识别...")
    texts = await capture._ocr_recognize(img)
    print(f"   ✅ 识别到 {len(texts)} 条:")
    for i, t in enumerate(texts, 1):
        print(f"   {i}. {t[:70]}")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_quick()
    asyncio.run(test_danmaku_capture())
