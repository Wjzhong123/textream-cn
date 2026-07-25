"""
CaptiOCR 桥接层 — 将 CaptiOCR 引擎接入 Textream 后端 API

CaptiOCR 提供：
  1. 视觉区域选择（SelectionWindow）— 全屏遮罩 + 鼠标拖拽框选
  2. 连续截图 + OCR（ScreenCapture）— 定时截取选区 + pytesseract OCR
  3. 智能去重（TextProcessor）— ROVER 合并 + TF-IDF 新颖度评分

本桥接层将 CaptiOCR 的输出转为 Textream 后端可消费的格式。
"""

import asyncio
import logging
import threading
from typing import Callable, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CaptiOCRBridge:
    """
    桥接 CaptiOCR 引擎到 Textream 后端。

    用法:
        bridge = CaptiOCRBridge()
        bridge.set_callback(my_async_callback)
        bridge.show_region_selector()  # 视觉框选
        await bridge.start()           # 开始捕获
        await bridge.stop()            # 停止捕获
    """

    def __init__(self, lang: str = "chi_sim+eng"):
        self._lang = lang
        self._capture = None
        self._ocr = None
        self._text_processor = None
        self._callback: Optional[Callable] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── 接口兼容属性（与 DanmakuCapture 保持一致） ──────────

    @property
    def bbox(self) -> tuple[int, int, int, int] | None:
        """当前捕获区域 (left, top, right, bottom)"""
        if self._capture and self._capture.capture_area:
            return self._capture.capture_area
        return None

    @property
    def running(self) -> bool:
        """是否正在捕获"""
        if not self._capture:
            return False
        return (self._capture.capture_thread is not None
                and self._capture.capture_thread.is_alive())

    @property
    def lang(self) -> str:
        """OCR 语言"""
        return self._lang

    def _lazy_init(self):
        """延迟导入 CaptiOCR（避免启动时加载所有依赖）"""
        if self._capture is not None:
            return

        # 确保 TESSDATA_PREFIX 指向正确的系统路径
        # CaptiOCR 的默认值硬编码为 Windows 路径，macOS 需要覆盖
        import os as _os
        _system_tessdata = "/usr/local/share/tessdata"
        if _os.path.isdir(_system_tessdata):
            _os.environ.setdefault("TESSDATA_PREFIX", _system_tessdata)
        # 确保 pytesseract 能找到 tesseract 命令
        _tesseract_cmd = "/usr/local/bin/tesseract"
        if _os.path.isfile(_tesseract_cmd):
            import pytesseract as _pt
            _pt.pytesseract.tesseract_cmd = _tesseract_cmd

        try:
            from PIL import ImageGrab  # noqa: ensure Pillow available
            import pytesseract  # noqa: ensure pytesseract available

            from vendor.captiocr.captiocr.core.ocr import OCRProcessor
            from vendor.captiocr.captiocr.core.text_processor import TextProcessor
            from vendor.captiocr.captiocr.core.capture import ScreenCapture
            from vendor.captiocr.captiocr.models.capture_config import CaptureConfig

            self._ocr = OCRProcessor()
            # OCRProcessor.__init__ 内部调用了 initialize_tesseract()，
            # 它在 macOS 上会把 TESSDATA_PREFIX 错误设为 Windows 路径。
            # 这里修正回正确的系统路径。
            import os as _os2
            _real_tessdata = "/usr/local/share/tessdata"
            if _os2.path.isdir(_real_tessdata):
                _os2.environ["TESSDATA_PREFIX"] = _real_tessdata
                self._ocr.logger.info(f"TESSDATA_PREFIX corrected to: {_real_tessdata}")
            self._text_processor = TextProcessor()
            config = CaptureConfig()
            self._capture = ScreenCapture(self._ocr, self._text_processor, config)

            # 设置 CaptiOCR 的回调
            self._capture.on_text_captured = self._on_text_captured

            logger.info("[CaptiOCRBridge] 引擎初始化完成")
        except ImportError as e:
            logger.error(f"[CaptiOCRBridge] 导入 CaptiOCR 失败: {e}")
            raise

    def set_callback(self, callback: Callable):
        """设置新文本回调（async function(texts: list[str])）"""
        self._callback = callback

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """设置异步事件循环（用于回调）"""
        self._loop = loop

    def show_region_selector(self) -> tuple[int, int, int, int] | None:
        """
        打开 CaptiOCR 的视觉区域选择器（全屏遮罩 + 鼠标拖拽）。
        返回 (x, y, width, height) 或 None（用户取消）。
        """
        self._lazy_init()

        try:
            import tkinter as tk
            from vendor.captiocr.captiocr.ui.selection_window import SelectionWindow

            logger.info("[CaptiOCRBridge] 打开区域选择器...")

            # 创建 tkinter 根窗口（隐藏）
            root = tk.Tk()
            root.withdraw()

            # 创建选择窗口
            win = SelectionWindow(root)
            area = win.select_area()  # 同步阻塞，返回 (x1, y1, x2, y2)

            root.destroy()

            if area:
                x1, y1, x2, y2 = area
                w, h = x2 - x1, y2 - y1
                # CaptiOCR 的 set_capture_area 也接受 (x1,y1,x2,y2)
                self._capture.set_capture_area((x1, y1, x2, y2))
                logger.info(f"[CaptiOCRBridge] 区域已选择: ({x1}, {y1}, {w}, {h})")
                return (x1, y1, w, h)
            else:
                logger.info("[CaptiOCRBridge] 用户取消区域选择")
                return None
        except ImportError as e:
            logger.error(f"[CaptiOCRBridge] 无法打开区域选择器: {e}")
            return None
        except Exception as e:
            logger.error(f"[CaptiOCRBridge] 选择器异常: {e}")
            return None

    def set_region(self, x: int, y: int, width: int, height: int):
        """以编程方式设置捕获区域"""
        self._lazy_init()
        self._capture.set_capture_area((x, y, x + width, y + height))
        logger.info(f"[CaptiOCRBridge] 区域已设为: ({x}, {y}, {width}, {height})")

    async def start(self):
        """异步启动捕获循环"""
        self._lazy_init()
        if not self._capture.capture_area:
            raise ValueError("请先设置捕获区域 (set_region 或 show_region_selector)")

        logger.info("[CaptiOCRBridge] 启动捕获...")
        self._loop = self._loop or asyncio.get_event_loop()

        # 在后台线程运行 CaptiOCR 的同步捕获
        self._capture.start_capture(language=self.lang)

        # CaptiOCR 的 start_capture 内部已启动线程，
        # 我们只需返回一个已完成的 Future
        logger.info("[CaptiOCRBridge] 捕获已启动")

    async def stop(self):
        """停止捕获"""
        if self._capture:
            self._capture.stop_capture()
            logger.info("[CaptiOCRBridge] 捕获已停止")

    def get_status(self) -> dict:
        """获取当前状态"""
        if not self._capture:
            return {"running": False, "area": None}
        return {
            "running": self._capture.capture_thread is not None and self._capture.capture_thread.is_alive(),
            "area": self._capture.capture_area,
        }

    # ── 内部 ────────────────────────────────────────────────

    def _on_text_captured(self, text: str):
        """CaptiOCR 的回调 — 新文本到达（从后台线程调用）"""
        if not text or not text.strip():
            return

        # 1) 同步日志 — 确认回调被触发（stderr 确保可见）
        import sys
        print(f"[CaptiOCRBridge] 回调触发: {text.strip()[:80]}", file=sys.stderr, flush=True)
        logger.info(f"[CaptiOCRBridge] 回调触发: {text.strip()[:80]}")

        callback = self._callback
        loop = self._loop

        if callback and loop:
            try:
                # 将回调投递到异步事件循环
                future = asyncio.run_coroutine_threadsafe(
                    callback([text.strip()]), loop
                )
                # 不阻塞等待，但记录异常
                def _log_exception(f):
                    exc = f.exception()
                    if exc:
                        print(f"[CaptiOCRBridge] 回调异常: {exc}", file=sys.stderr, flush=True)
                        logger.error(f"[CaptiOCRBridge] 回调异常: {exc}")
                future.add_done_callback(_log_exception)
            except Exception as e:
                print(f"[CaptiOCRBridge] 投递回调失败: {e}", file=sys.stderr, flush=True)
                logger.error(f"[CaptiOCRBridge] 投递回调失败: {e}")
        elif callback:
            # 同步回调（用于测试）
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        callback([text.strip()]), loop
                    )
                else:
                    loop.run_until_complete(callback([text.strip()]))
            except RuntimeError as e:
                print(f"[CaptiOCRBridge] 同步回调失败: {e}", file=sys.stderr, flush=True)
                logger.error(f"[CaptiOCRBridge] 同步回调失败: {e}")
        else:
            print(f"[CaptiOCRBridge] 回调未设置，丢弃文本: {text.strip()[:50]}", file=sys.stderr, flush=True)
            logger.warning("[CaptiOCRBridge] 回调未设置，丢弃文本")
