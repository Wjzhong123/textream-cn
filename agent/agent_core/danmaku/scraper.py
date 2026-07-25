"""
弹幕截图 + OCR 识别模块（极简方案 - PIL.ImageGrab + pytesseract）

使用 Pillow ImageGrab + pytesseract 实现屏幕 OCR 弹幕捕获
零外部依赖，PIL + pytesseract 已安装

依赖：
- Pillow（ImageGrab 屏幕截图）
- pytesseract（OCR 识别）
- numpy（图像预处理）
"""

import asyncio
import logging
import time
from typing import Any

import numpy as np
import pytesseract
import cv2
from PIL import Image, ImageGrab, ImageGrab

logger = logging.getLogger(__name__)


class DanmakuCapture:
    """
    弹幕捕获器

    通过屏幕截图 + OCR 识别实时捕获弹幕
    依赖: Pillow ImageGrab + pytesseract
    """

    def __init__(
        self,
        capture_interval: float = 1.0,
        lang: str = "chi_sim+eng",
    ):
        """
        初始化弹幕捕获器

        Args:
            capture_interval: 捕获间隔（秒）
            lang: OCR 语言（默认中英文混合）
        """
        self.bbox: tuple[int, int, int, int] | None = None  # (left, top, right, bottom)
        self.cache: set[str] = set()
        self.cache_max_size = 500  # 最多缓存 500 条
        self.running = False
        self.callback: Any = None
        self.capture_interval = capture_interval
        self.lang = lang

        logger.info(f"[DanmakuCapture] 初始化完成 (interval={capture_interval}s, lang={lang})")

    def set_region(self, x: int, y: int, width: int, height: int):
        """
        设置截图区域

        Args:
            x: 左上角 X 坐标
            y: 左上角 Y 坐标
            width: 宽度
            height: 高度
        """
        self.bbox = (x, y, x + width, y + height)
        logger.info(f"[DanmakuCapture] 截图区域: bbox={self.bbox}")

    def set_callback(self, callback):
        """
        设置弹幕回调函数

        Args:
            callback: 回调函数，接收弹幕文本列表
        """
        self.callback = callback

    async def start(self):
        """开始捕获弹幕"""
        if not self.bbox:
            raise ValueError("请先设置截图区域 (set_region)")

        self.running = True
        logger.info("[DanmakuCapture] 开始捕获弹幕")

        try:
            while self.running:
                try:
                    # 截图 + OCR
                    new_texts = await self._capture_and_ocr()

                    # 去重
                    if new_texts:
                        # 回调
                        if self.callback:
                            await self.callback(new_texts)

                except Exception as e:
                    logger.error(f"[DanmakuCapture] 捕获失败: {e}")

                # 控制捕获频率
                await asyncio.sleep(self.capture_interval)
        except asyncio.CancelledError:
            logger.info("[DanmakuCapture] 捕获已取消")
        finally:
            self.running = False
            logger.info("[DanmakuCapture] 停止捕获")

    async def stop(self):
        """停止捕获"""
        self.running = False
        logger.info("[DanmakuCapture] 停止捕获")

    async def _capture_and_ocr(self) -> list[str]:
        """
        截图 + OCR 识别（一步完成）

        Returns:
            识别到的新文本列表
        """
        try:
            # 1. 屏幕截图（使用 Pillow ImageGrab）
            screenshot = ImageGrab.grab(bbox=self.bbox)

            # 2. 图像预处理
            # 转灰度 + 放大 + 二值化，提高 OCR 准确率
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

            # 放大 2 倍
            frame = cv2.resize(frame, (0, 0), fx=2.0, fy=2.0)

            # 二值化，让文字更清晰
            _, thresh = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)

            # 3. OCR 识别
            text = pytesseract.image_to_string(thresh, config="--psm 6", lang=self.lang)

            # 4. 清洗与去重
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            new_lines = []
            for line in lines:
                if line not in self.cache:
                    self.cache.add(line)
                    new_lines.append(line)

                    # 控制缓存大小
                    if len(self.cache) > self.cache_max_size:
                        # 删除最旧的 10%
                        old_size = int(self.cache_max_size * 0.1)
                        cache_list = list(self.cache)
                        self.cache = set(cache_list[-self.cache_max_size:])

            logger.debug(f"[DanmakuCapture] OCR 识别到 {len(new_lines)} 条新文本")
            return new_lines

        except Exception as e:
            logger.error(f"[DanmakuCapture] 截图+OCR 失败: {e}")
            return []

    def get_status(self) -> dict[str, Any]:
        """获取捕获状态"""
        return {
            "running": self.running,
            "bbox": self.bbox,
            "cache_size": len(self.cache),
            "capture_interval": self.capture_interval,
        }


# 测试函数
async def test_basic():
    """基础测试"""
    print("🧪 测试弹幕捕获器（PIL.ImageGrab）")

    capture = DanmakuCapture(capture_interval=1.0)

    # 设置区域（左上角 100,100，大小 400x300）
    capture.set_region(100, 100, 400, 300)

    # 单次截图 + OCR 测试
    print("\n📐 测试截图 + OCR...")
    texts = await capture._capture_and_ocr()

    if texts:
        print(f"  ✅ 识别到 {len(texts)} 条新文本:")
        for i, text in enumerate(texts, 1):
            print(f"  {i}. {text[:80]}")
    else:
        print("  ⚠️  未识别到文本（可能是空白区域）")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_basic())
