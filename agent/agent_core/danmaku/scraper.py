"""
弹幕截图 + OCR 识别模块

双引擎架构：
  1. DirectorDanmakuCapture（主力，默认）— 通过 Textream.app 的 DirectorServer 获取截图
     ✅ 屏幕权限归 Textream.app，权限弹窗显示"Textream"而非"Python"
  2. DanmakuCapture（fallback）— 直接使用 PIL.ImageGrab + pytesseract

流程：
  Textream.app (Swift) → DirectorServer REST API → 本模块 HTTP 获取截图 → pytesseract OCR
"""

import asyncio
import base64
import logging
import os
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

import numpy as np
import pytesseract
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


# ── 引擎 1: 通过 DirectorServer 截图（主力） ─────────────────────────────


class DirectorDanmakuCapture:
    """
    通过 Textream.app 的 DirectorServer 获取截图的弹幕捕获器

    截图发生在 Textream.app（Swift）侧，权限弹窗显示"Textream"而非"Python"。
    OCR 仍在 Python 侧进行（pytesseract）。

    用法与 DanmakuCapture 完全一致（鸭子类型接口）。
    """

    # DirectorServer 默认端口
    DEFAULT_HTTP_PORT = 7575

    def __init__(
        self,
        capture_interval: float = 1.0,
        lang: str = "chi_sim+eng",
        director_port: int | None = None,
        timeout: float = 3.0,
    ):
        """
        初始化 DirectorServer 弹幕捕获器

        Args:
            capture_interval: 捕获间隔（秒）
            lang: OCR 语言（默认中英文混合）
            director_port: DirectorServer HTTP 端口，默认 7575
            timeout: HTTP 请求超时（秒）
        """
        port = director_port or int(os.environ.get("DIRECTOR_HTTP_PORT", str(self.DEFAULT_HTTP_PORT)))
        self.base_url = f"http://127.0.0.1:{port}"
        self.timeout = timeout
        self.bbox: tuple[int, int, int, int] | None = None  # (left, top, right, bottom)
        self._region_params: dict[str, int] = {}  # x, y, w, h
        self.cache: set[str] = set()
        self.cache_max_size = 500
        self.running = False
        self.callback: Any = None
        self.capture_interval = capture_interval
        self.lang = lang
        self._director_available: bool | None = None  # None = 未检测

        logger.info(f"[DirectorDanmakuCapture] 初始化 (DirectorServer={self.base_url}, interval={capture_interval}s)")

    # ── 接口兼容方法（与 DanmakuCapture 一致） ──────────────────────────

    def set_region(self, x: int, y: int, width: int, height: int):
        """设置截图区域"""
        self._region_params = {"x": x, "y": y, "w": width, "h": height}
        self.bbox = (x, y, x + width, y + height)
        logger.info(f"[DirectorDanmakuCapture] 截图区域: {self._region_params}")

    def set_callback(self, callback):
        """设置弹幕回调函数"""
        self.callback = callback

    async def start(self):
        """开始捕获弹幕"""
        if not self.bbox:
            raise ValueError("请先设置截图区域 (set_region)")

        # 启动前先检测 DirectorServer 是否可用
        if not await self._check_director_available():
            raise RuntimeError(
                f"DirectorServer 不可达 ({self.base_url})。"
                "请确保 Textream.app 已运行且 DirectorServer 已启用。"
            )

        self.running = True
        logger.info("[DirectorDanmakuCapture] 开始捕获弹幕")

        try:
            while self.running:
                try:
                    new_texts = await self._capture_and_ocr()
                    if new_texts and self.callback:
                        await self.callback(new_texts)
                except Exception as e:
                    logger.error(f"[DirectorDanmakuCapture] 捕获失败: {e}")

                await asyncio.sleep(self.capture_interval)
        except asyncio.CancelledError:
            logger.info("[DirectorDanmakuCapture] 捕获已取消")
        finally:
            self.running = False
            logger.info("[DirectorDanmakuCapture] 停止捕获")

    async def stop(self):
        """停止捕获"""
        self.running = False
        logger.info("[DirectorDanmakuCapture] 停止捕获")

    async def _capture_and_ocr(self) -> list[str]:
        """
        通过 DirectorServer 获取截图 + OCR 识别

        Returns:
            识别到的新文本列表
        """
        try:
            # 1. 通过 DirectorServer API 获取截图（base64 JPEG）
            image_data = await self._fetch_screenshot()
            if image_data is None:
                return []

            # 2. OCR 识别
            return self._ocr_image(image_data)

        except Exception as e:
            logger.error(f"[DirectorDanmakuCapture] 截图+OCR 失败: {e}")
            return []

    # ── 内部方法 ────────────────────────────────────────────────────────

    async def _check_director_available(self) -> bool:
        """检测 DirectorServer 是否可达"""
        if self._director_available is not None:
            return self._director_available

        try:
            await asyncio.to_thread(self._http_get, "/api/capture-status")
            self._director_available = True
            logger.info(f"[DirectorDanmakuCapture] DirectorServer 可达 ({self.base_url})")
        except (URLError, ConnectionError, OSError, TimeoutError) as e:
            self._director_available = False
            logger.warning(f"[DirectorDanmakuCapture] DirectorServer 不可达: {e}")
        return self._director_available

    async def _fetch_screenshot(self) -> bytes | None:
        """从 DirectorServer 获取截图 JPEG 数据"""
        params = self._region_params
        if not params:
            logger.warning("[DirectorDanmakuCapture] 未设置截图区域")
            return None

        query = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"/api/screenshot?{query}"

        try:
            response = await asyncio.to_thread(self._http_get, path)
            data = response.get("data")
            if data:
                return base64.b64decode(data)
            logger.warning(f"[DirectorDanmakuCapture] 截图返回无数据: {response}")
            return None
        except Exception as e:
            logger.error(f"[DirectorDanmakuCapture] 获取截图失败: {e}")
            return None

    def _http_get(self, path: str) -> dict[str, Any]:
        """同步 HTTP GET 请求（在 asyncio.to_thread 中运行）"""
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        req = Request(url, method="GET")

        import json
        with urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {result.get('error', body[:200])}")
            return result

    def _ocr_image(self, image_data: bytes) -> list[str]:
        """对 JPEG 数据进行 OCR 识别"""
        # 1. 解码 JPEG → PIL Image → numpy
        img = Image.open(__import__("io").BytesIO(image_data))
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

        # 2. 图像预处理：放大 + 二值化
        frame = cv2.resize(frame, (0, 0), fx=2.0, fy=2.0)
        _, thresh = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)

        # 3. OCR
        text = pytesseract.image_to_string(thresh, config="--psm 6", lang=self.lang)

        # 4. 清洗与去重
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        new_lines = []
        for line in lines:
            if line not in self.cache:
                self.cache.add(line)
                new_lines.append(line)
                if len(self.cache) > self.cache_max_size:
                    cache_list = list(self.cache)
                    self.cache = set(cache_list[-self.cache_max_size:])

        logger.debug(f"[DirectorDanmakuCapture] OCR 识别到 {len(new_lines)} 条新文本")
        return new_lines

    def get_status(self) -> dict[str, Any]:
        """获取捕获状态"""
        return {
            "running": self.running,
            "bbox": self.bbox,
            "cache_size": len(self.cache),
            "capture_interval": self.capture_interval,
            "engine": "director_server",
            "director_url": self.base_url,
            "director_available": self._director_available,
        }


# ── 引擎 2: 直接 PIL.ImageGrab（fallback） ──────────────────────────────


class DanmakuCapture:
    """
    弹幕捕获器（fallback）

    直接通过 PIL.ImageGrab + pytesseract 实现屏幕 OCR。
    仅当 DirectorServer 不可用时使用。
    """

    def __init__(
        self,
        capture_interval: float = 1.0,
        lang: str = "chi_sim+eng",
    ):
        self.bbox: tuple[int, int, int, int] | None = None
        self.cache: set[str] = set()
        self.cache_max_size = 500
        self.running = False
        self.callback: Any = None
        self.capture_interval = capture_interval
        self.lang = lang
        logger.info(f"[DanmakuCapture] 初始化完成 (fallback, interval={capture_interval}s, lang={lang})")

    def set_region(self, x: int, y: int, width: int, height: int):
        self.bbox = (x, y, x + width, y + height)
        logger.info(f"[DanmakuCapture] 截图区域: bbox={self.bbox}")

    def set_callback(self, callback):
        self.callback = callback

    async def start(self):
        if not self.bbox:
            raise ValueError("请先设置截图区域 (set_region)")
        self.running = True
        logger.info("[DanmakuCapture] 开始捕获弹幕")
        try:
            while self.running:
                try:
                    new_texts = await self._capture_and_ocr()
                    if new_texts and self.callback:
                        await self.callback(new_texts)
                except Exception as e:
                    logger.error(f"[DanmakuCapture] 捕获失败: {e}")
                await asyncio.sleep(self.capture_interval)
        except asyncio.CancelledError:
            logger.info("[DanmakuCapture] 捕获已取消")
        finally:
            self.running = False
            logger.info("[DanmakuCapture] 停止捕获")

    async def stop(self):
        self.running = False
        logger.info("[DanmakuCapture] 停止捕获")

    async def _capture_and_ocr(self) -> list[str]:
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=self.bbox)
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            frame = cv2.resize(frame, (0, 0), fx=2.0, fy=2.0)
            _, thresh = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)
            text = pytesseract.image_to_string(thresh, config="--psm 6", lang=self.lang)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            new_lines = []
            for line in lines:
                if line not in self.cache:
                    self.cache.add(line)
                    new_lines.append(line)
                    if len(self.cache) > self.cache_max_size:
                        cache_list = list(self.cache)
                        self.cache = set(cache_list[-self.cache_max_size:])
            return new_lines
        except Exception as e:
            logger.error(f"[DanmakuCapture] 截图+OCR 失败: {e}")
            return []

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "bbox": self.bbox,
            "cache_size": len(self.cache),
            "capture_interval": self.capture_interval,
            "engine": "pil_imagegrab",
        }


# ── 工厂函数 ──────────────────────────────────────────────────────────────


async def create_capture(
    prefer_director: bool = True,
    capture_interval: float = 1.0,
    lang: str = "chi_sim+eng",
    director_port: int | None = None,
) -> DanmakuCapture | DirectorDanmakuCapture:
    """
    创建弹幕捕获器（自动选择引擎）

    Args:
        prefer_director: 是否优先使用 DirectorServer 引擎
        capture_interval: 捕获间隔
        lang: OCR 语言
        director_port: DirectorServer HTTP 端口

    Returns:
        DirectorDanmakuCapture（优先）或 DanmakuCapture（fallback）
    """
    if prefer_director:
        capture = DirectorDanmakuCapture(
            capture_interval=capture_interval,
            lang=lang,
            director_port=director_port,
        )
        available = await capture._check_director_available()
        if available:
            logger.info("[create_capture] 使用 DirectorServer 引擎（截屏权限归 Textream.app）")
            return capture
        logger.info("[create_capture] DirectorServer 不可用，回退到 PIL.ImageGrab")

    return DanmakuCapture(capture_interval=capture_interval, lang=lang)


# ── 测试 ──────────────────────────────────────────────────────────────────


async def test_basic():
    """基础测试"""
    capture = await create_capture(prefer_director=True)
    capture.set_region(100, 100, 400, 300)
    print(f"\n📐 引擎: {capture.get_status().get('engine', '?')}")

    texts = await capture._capture_and_ocr()
    if texts:
        print(f"  ✅ 识别到 {len(texts)} 条新文本:")
        for i, text in enumerate(texts, 1):
            print(f"  {i}. {text[:80]}")
    else:
        print("  ⚠️  未识别到文本（可能是空白区域）")


if __name__ == "__main__":
    asyncio.run(test_basic())
