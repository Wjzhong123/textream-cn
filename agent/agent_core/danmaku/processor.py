"""
弹幕处理流水线

集成捕获、识别、应答、推送的完整流程
支持引擎：
  - DirectorDanmakuCapture（主力）→ 截屏权限归 Textream.app
  - CaptiOCR（视觉框选 + ROVER/TF-IDF 去重）
  - DanmakuCapture（fallback）→ PIL.ImageGrab
"""

import asyncio
import json
import logging
import os
from typing import Any

from .scraper import DanmakuCapture, DirectorDanmakuCapture, create_capture
from .responder import DanmakuResponder, ResponseStyle

logger = logging.getLogger(__name__)


class DanmakuProcessor:
    """
    弹幕处理器

    整合弹幕捕获、OCR、意图识别、应答生成的完整流水线
    """

    def __init__(
        self,
        memory_manager = None,
        llm_provider: str | None = None,
        use_captiocr: bool = False,
    ):
        """
        初始化弹幕处理器

        Args:
            memory_manager: 记忆管理器（AIMemoryManager 或 None）
            llm_provider: LLM 提供商
            use_captiocr: 是否使用 CaptiOCR 引擎（视觉框选 + 智能去重）
        """
        self._use_captiocr = use_captiocr or os.environ.get("CAPTIOCR_ENABLED", "").lower() == "true"

        if self._use_captiocr:
            from captiocr_adapter import CaptiOCRBridge
            self.capture = CaptiOCRBridge()
            self._capture_engine = "captiocr"
            logger.info("[DanmakuProcessor] 使用 CaptiOCR 引擎")
        else:
            # 占位：启动时自动检测 DirectorServer，见 launch()
            self._capture_engine = "auto"
            self.capture = DanmakuCapture()
            logger.info("[DanmakuProcessor] 初始化完成（启动时自动检测 DirectorServer）")

        self.responder = DanmakuResponder(
            memory_manager=memory_manager,
            llm_provider=llm_provider,
        )
        self.running = False
        self.websocket_callback: Any = None
        self._launched = False

        logger.info("[DanmakuProcessor] 初始化完成")

    async def launch(self):
        """
        自动检测 DirectorServer 并切换引擎（如果可用）

        在第一次 start() 前自动调用，也可手动调用。
        """
        if self._launched or self._use_captiocr:
            return

        self._launched = True
        # 尝试 DirectorServer
        director = DirectorDanmakuCapture(
            capture_interval=self.capture.capture_interval
            if hasattr(self.capture, 'capture_interval') else 1.0,
            lang=self.capture.lang if hasattr(self.capture, 'lang') else "chi_sim+eng",
        )
        available = await director._check_director_available()
        if available:
            # 保留旧 capture 的 region 设置
            if self.capture.bbox:
                x, y, right, bottom = self.capture.bbox
                director.set_region(x, y, right - x, bottom - y)
            self.capture = director
            self._capture_engine = "director_server"
            logger.info("[DanmakuProcessor] ✅ 已切换到 DirectorServer 引擎（截屏权限归 Textream.app）")
        else:
            logger.info("[DanmakuProcessor] DirectorServer 不可用，使用 PIL.ImageGrab（将弹出 Python 权限请求）")

    def set_region(self, x: int, y: int, width: int, height: int):
        """设置截图区域"""
        self.capture.set_region(x, y, width, height)

    def set_websocket_callback(self, callback):
        """
        设置 WebSocket 推送回调

        Args:
            callback: 回调函数，接收应答结果并推送到前端
        """
        self.websocket_callback = callback

    async def start(self):
        """启动弹幕处理流水线"""
        # 自动检测 DirectorServer 并切换引擎
        await self.launch()

        if not self.capture.bbox:
            raise ValueError("请先设置截图区域 (set_region)")

        self.running = True

        # 设置弹幕捕获回调
        async def on_danmaku(texts: list[str]):
            for text in texts:
                await self._process_single_danmaku(text)

        self.capture.set_callback(on_danmaku)

        # 开始捕获
        await self.capture.start()

    async def stop(self):
        """停止弹幕处理"""
        self.running = False
        await self.capture.stop()
        logger.info("[DanmakuProcessor] 已停止")

    async def _process_single_danmaku(self, text: str):
        """
        处理单条弹幕

        Args:
            text: 弹幕文本
        """
        logger.info(f"[DanmakuProcessor] 处理弹幕: {text}")

        try:
            # 生成 3 档话术
            for style in [ResponseStyle.SIMPLE, ResponseStyle.DETAILED, ResponseStyle.HUMOR]:
                response = await self.responder.generate_response(
                    danmaku_text=text,
                    style=style,
                )

                # WebSocket 推送
                if self.websocket_callback:
                    await self.websocket_callback(response.to_dict())

                # 间隔一下，避免推送过快
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"[DanmakuProcessor] 处理失败: {e}")

    async def generate_manual_response(
        self,
        text: str,
        style: str = ResponseStyle.SIMPLE,
    ) -> dict[str, Any]:
        """
        手动触发应答生成

        Args:
            text: 弹幕文本
            style: 话术风格

        Returns:
            应答结果字典
        """
        response = await self.responder.generate_response(text, style)
        return response.to_dict()
