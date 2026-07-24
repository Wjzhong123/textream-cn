"""
弹幕处理流水线

集成捕获、识别、应答、推送的完整流程
"""

import asyncio
import json
import logging
from typing import Any

from .scraper import DanmakuCapture
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
    ):
        """
        初始化弹幕处理器

        Args:
            memory_manager: One Memory 记忆管理器
            llm_provider: LLM 提供商
        """
        self.capture = DanmakuCapture()
        self.responder = DanmakuResponder(
            memory_manager=memory_manager,
            llm_provider=llm_provider,
        )
        self.running = False
        self.websocket_callback: Any = None

        logger.info("[DanmakuProcessor] 初始化完成")

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
        if not self.capture.region:
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
