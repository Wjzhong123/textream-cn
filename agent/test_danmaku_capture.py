#!/usr/bin/env python3
"""
弹幕捕获集成测试 - mss + pytesseract

测试屏幕截图 + OCR 识别功能
"""

import sys
import time
import asyncio
from pathlib import Path
from typing import Union

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import mss
import numpy as np
import cv2
from PIL import Image
import pytesseract


def test_screen_capture():
    """测试屏幕捕获"""
    print("=" * 60)
    print("🧪 测试 1: 屏幕捕获 (mss)")
    print("=" * 60)

    try:
        with mss.mss() as sct:
            # 获取主显示器
            monitor = sct.monitors[1]  # monitors[0] 是所有显示器的组合
            print(f"📺 主显示器: {monitor}")

            # 捕获全屏
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)

            print(f"✅ 截图成功: {img.shape}")

            # 转换为 PNG 并保存
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            output_path = Path(__file__).parent / "test_screenshot.png"
            cv2.imwrite(str(output_path), img_bgr)
            print(f"💾 截图已保存: {output_path}")

            return True
    except Exception as e:
        print(f"❌ 屏幕捕获失败: {e}")
        return False


def test_ocr(image_path: Union[str, Path]):
    """测试 OCR 识别"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: OCR 文本识别 (pytesseract)")
    print("=" * 60)

    try:
        # 读取图像
        img = Image.open(image_path)

        # OCR 识别（中英文混合）
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')

        print(f"✅ OCR 识别完成")
        print(f"📝 识别结果（前 200 字符）:")
        print("-" * 60)
        print(text[:200] if text else "(空)")
        print("-" * 60)

        return text
    except Exception as e:
        print(f"❌ OCR 识别失败: {e}")
        return ""


def test_region_capture():
    """测试区域截图"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 区域截图")
    print("=" * 60)

    try:
        with mss.mss() as sct:
            # 定义区域（左上角 100x100，大小 400x300）
            region = {
                "top": 100,
                "left": 100,
                "width": 400,
                "height": 300
            }

            print(f"📐 截图区域: {region}")

            screenshot = sct.grab(region)
            img = np.array(screenshot)

            print(f"✅ 区域截图成功: {img.shape}")

            # 保存
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            output_path = Path(__file__).parent / "test_region.png"
            cv2.imwrite(str(output_path), img_bgr)
            print(f"💾 区域截图已保存: {output_path}")

            return True
    except Exception as e:
        print(f"❌ 区域截图失败: {e}")
        return False


def test_realtime_capture(duration: int = 5):
    """测试实时捕获（每 1 秒一次）"""
    print(f"\n" + "=" * 60)
    print(f"🧪 测试 4: 实时捕获（{duration} 秒，每秒 1 次）")
    print("=" * 60)

    try:
        with mss.mss() as sct:
            start_time = time.time()

            for i in range(duration):
                # 截图
                screenshot = sct.grab(sct.monitors[1])
                img = np.array(screenshot)
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 保存
                output_path = Path(__file__).parent / f"test_realtime_{i+1:02d}.png"
                cv2.imwrite(str(output_path), img_bgr)

                print(f"  ⏱️  [{i+1:02d}/{duration}] 截图已保存: {output_path.name}")

                # OCR 识别
                pil_img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
                text = pytesseract.image_to_string(pil_img, lang='chi_sim+eng')

                if text.strip():
                    print(f"  📝  OCR: {text[:50].strip()}...")

                time.sleep(1)

            elapsed = time.time() - start_time
            print(f"\n✅ 实时捕获完成: {duration} 次，耗时 {elapsed:.1f}s")

            return True
    except Exception as e:
        print(f"❌ 实时捕获失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n🎬 弹幕捕获集成测试\n")

    # 测试 1: 全屏截图
    success = test_screen_capture()

    if success:
        # 测试 2: OCR 识别
        test_screenshot = Path(__file__).parent / "test_screenshot.png"
        if test_screenshot.exists():
            test_ocr(test_screenshot)

        # 测试 3: 区域截图
        test_region_capture()

        # 测试 4: 实时捕获
        test_realtime_capture(duration=3)

    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
