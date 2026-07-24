"""
弹幕截图 + OCR 识别模块

支持 macOS Vision 和 Windows RapidOCR
"""

import asyncio
import base64
import io
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DanmakuCapture:
    """
    弹幕捕获器

    通过屏幕截图 + OCR 识别实时捕获弹幕
    """

    def __init__(self, platform: str | None = None):
        """
        初始化弹幕捕获器

        Args:
            platform: 平台（"macos" 或 "windows"），自动检测如果为 None
        """
        self.platform = platform or self._detect_platform()
        self.region: dict[str, int] | None = None
        self.cache: list[str] = []
        self.cache_max_size = 100
        self.running = False
        self.callback: Any = None

        logger.info(f"[DanmakuCapture] 平台: {self.platform}")

    def _detect_platform(self) -> str:
        """自动检测平台"""
        import sys
        if sys.platform == "darwin":
            return "macos"
        elif sys.platform == "win32":
            return "windows"
        else:
            return "unknown"

    def set_region(self, x: int, y: int, width: int, height: int):
        """
        设置截图区域

        Args:
            x: 左上角 X 坐标
            y: 左上角 Y 坐标
            width: 宽度
            height: 高度
        """
        self.region = {"top": y, "left": x, "width": width, "height": height}
        logger.info(f"[DanmakuCapture] 截图区域: {self.region}")

    def set_callback(self, callback):
        """
        设置弹幕回调函数

        Args:
            callback: 回调函数，接收弹幕文本列表
        """
        self.callback = callback

    async def start(self):
        """开始捕获弹幕"""
        if not self.region:
            raise ValueError("请先设置截图区域 (set_region)")

        self.running = True
        logger.info("[DanmakuCapture] 开始捕获弹幕")

        while self.running:
            try:
                # 截图
                screenshot = await self._capture_screenshot()

                # OCR 识别
                texts = await self._ocr_recognize(screenshot)

                # 去重
                new_texts = [t for t in texts if t not in self.cache]

                # 更新缓存
                if new_texts:
                    self.cache.extend(new_texts)
                    if len(self.cache) > self.cache_max_size:
                        self.cache = self.cache[-self.cache_max_size:]

                    # 回调
                    if self.callback:
                        await self.callback(new_texts)

            except Exception as e:
                logger.error(f"[DanmakuCapture] 捕获失败: {e}")

            # 控制捕获频率（每秒 2-3 次）
            await asyncio.sleep(0.5)

    async def stop(self):
        """停止捕获"""
        self.running = False
        logger.info("[DanmakuCapture] 停止捕获")

    async def _capture_screenshot(self) -> bytes:
        """
        截取屏幕区域

        Returns:
            截图字节流（PNG）
        """
        if self.platform == "macos":
            return await self._capture_macos()
        elif self.platform == "windows":
            return await self._capture_windows()
        else:
            raise NotImplementedError(f"不支持的平台: {self.platform}")

    async def _capture_macos(self) -> bytes:
        """macOS 屏幕截图（使用 screencapture）"""
        import tempfile

        if not self.region:
            raise ValueError("未设置截图区域")

        # 使用 screencapture 命令
        cmd = [
            "screencapture",
            "-x",  # 不播放声音
            "-R",  # 区域截图
            f"{self.region['left']},{self.region['top']},"
            f"{self.region['width']},{self.region['height']}",
            "-t", "png",  # PNG 格式
            "-",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"screencapture 失败: {stderr.decode()}")

        return stdout

    async def _capture_windows(self) -> bytes:
        """Windows 屏幕截图（使用 mss）"""
        try:
            import mss
            import numpy as np

            with mss.mss() as sct:
                monitor = {
                    "top": self.region["top"],
                    "left": self.region["left"],
                    "width": self.region["width"],
                    "height": self.region["height"],
                }
                screenshot = sct.grab(monitor)

                # 转换为 PNG
                import cv2
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                _, buffer = cv2.imencode(".png", img)
                return buffer.tobytes()

        except ImportError:
            raise ImportError("Windows 平台需要安装 mss 和 opencv-python")

    async def _ocr_recognize(self, screenshot: bytes) -> list[str]:
        """
        OCR 识别弹幕文本

        Args:
            screenshot: 截图字节流

        Returns:
            识别到的文本列表
        """
        if self.platform == "macos":
            return await self._ocr_macos(screenshot)
        elif self.platform == "windows":
            return await self._ocr_windows(screenshot)
        else:
            return []

    async def _ocr_macos(self, screenshot: bytes) -> list[str]:
        """macOS OCR（使用 Vision 框架）"""
        import tempfile

        # 保存临时文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(screenshot)
            temp_path = f.name

        try:
            # 使用 macOS 的 Vision 框架 OCR
            script = f"""
            use framework "Foundation"
            use framework "Vision"

            set imagePath to "{temp_path}"
            set imageURL to current application's NSURL's fileURLWithPath:imagePath

            set imageRef to current application's CIImage's imageWithContentsOfURL:imageURL
            set requestHandler to current application's VNImageRequestHandler's alloc()'s initWithCIImage:imageRef options:(current application's NSDictionary's dictionary())

            set ocrRequest to current application's VNRecognizeTextRequest's alloc()'s init()
            ocrRequest's setRecognitionLevel:(current application's VNRequestTextRecognitionLevelAccurate)
            ocrRequest's setRecognitionLanguages:{{"zh-Hans", "en"}}
            ocrRequest's setUsesLanguageCorrection:true

            requestHandler's performRequests:{ocrRequest}'s |error|:(missing value)

            set results to ocrRequest's results()
            set outputTexts to current application's NSMutableArray's array()

            repeat with observation in results
                set topCandidate to (observation's topCandidates:1)'s firstObject()
                if topCandidate is not missing value then
                    (outputTexts's addObject:(topCandidate's |string|() as text))
                end if
            end repeat

            return outputTexts as list
            """

            # 执行 AppleScript
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"Vision OCR 失败: {stderr.decode()}")
                return []

            # 解析结果
            import json
            try:
                # AppleScript 返回 AppleScript 列表格式
                output = stdout.decode().strip()
                if output.startswith("{") and output.endswith("}"):
                    # 转换为 JSON 数组
                    json_str = "[" + output[1:-1].replace(", ", ", ") + "]"
                    texts = json.loads(json_str)
                    return [t for t in texts if t.strip()]

            except Exception as e:
                logger.warning(f"解析 OCR 结果失败: {e}")

            return []

        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    async def _ocr_windows(self, screenshot: bytes) -> list[str]:
        """Windows OCR（使用 RapidOCR）"""
        try:
            from rapidocr_onnxruntime import RapidOCR

            # 初始化 OCR（懒加载）
            if not hasattr(self, "_ocr_engine"):
                self._ocr_engine = RapidOCR()

            # 识别
            result, _ = self._ocr_engine(np.frombuffer(screenshot, dtype=np.uint8))

            if result:
                return [line[1] for line in result if line[1].strip()]
            return []

        except ImportError:
            logger.error("Windows 平台需要安装 rapidocr-onnxruntime")
            return []
