"""
弹幕处理流水线

集成捕获、识别、应答、推送的完整流程
支持引擎：
  - DirectorDanmakuCapture（主力）→ DirectorServer（截图权限归 Textream.app）
  - CaptiOCR（视觉框选 + ROVER/TF-IDF 去重）
  - DanmakuCapture（fallback）→ PIL.ImageGrab（需要 Python 进程有屏幕录制权限）
"""

import asyncio
import json
import logging
import os
import time
from typing import Any

from .scraper import DanmakuCapture, DirectorDanmakuCapture
from .responder import DanmakuResponder, ResponseStyle

logger = logging.getLogger(__name__)

# 被导入时自动注入 error_bus（如果可用）
try:
    from agent_core.error_bus import error_bus
except ImportError:
    error_bus = None


class DanmakuProcessor:
    """
    弹幕处理器

    整合弹幕捕获、OCR、意图识别、应答生成的完整流水线
    """

    def __init__(
        self,
        memory_manager = None,
        knowledge_manager = None,
        llm_provider: str | None = None,
        use_captiocr: bool = False,
    ):
        """
        初始化弹幕处理器

        Args:
            memory_manager: 记忆管理器（AIMemoryManager 或 None）
            knowledge_manager: 知识库管理器（KnowledgeManager 或 None）
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

        self._ocr_lang = os.environ.get("OCR_LANG", "chi_sim+eng")

        self.responder = DanmakuResponder(
            memory_manager=memory_manager,
            knowledge_manager=knowledge_manager,
            llm_provider=llm_provider,
        )
        self._memory_manager = memory_manager
        self.running = False
        self.websocket_callback: Any = None
        self._launched = False

        logger.info("[DanmakuProcessor] 初始化完成")

    async def _launch_textream_app(self) -> bool:
        """
        尝试启动 Textream.app（如果未运行）

        检测 /Applications/Textream.app 是否存在，如果存在且未运行则启动。
        Returns:
            True 如果已启动或已在运行
        """
        import subprocess
        import shutil

        textream_path = "/Applications/Textream.app"

        # 如果 /Applications/Textream.app 不存在，检查 agent 同目录
        if not os.path.isdir(textream_path):
            local_path = str(Path(__file__).resolve().parent.parent.parent / "Textream.app")
            if os.path.isdir(local_path):
                textream_path = local_path

        # 检查是否已安装
        if not os.path.isdir(textream_path):
            logger.warning("[DanmakuProcessor] Textream.app 未安装，无法自动启动")
            return False

        # 检查是否已在运行
        try:
            result = subprocess.run(
                ["pgrep", "-x", "Textream"],
                capture_output=True, timeout=3,
            )
            if result.returncode == 0:
                logger.info("[DanmakuProcessor] Textream.app 已在运行")
                return True
        except Exception:
            pass

        # 启动 Textream.app
        try:
            logger.info("[DanmakuProcessor] 正在启动 Textream.app...")
            subprocess.Popen(
                ["open", textream_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # 等待启动
            for i in range(15):
                await asyncio.sleep(1)
                try:
                    result = subprocess.run(
                        ["pgrep", "-x", "Textream"],
                        capture_output=True, timeout=3,
                    )
                    if result.returncode == 0:
                        logger.info(f"[DanmakuProcessor] Textream.app 已启动（等待 {i+1} 秒）")
                        return True
                except Exception:
                    pass
            logger.warning("[DanmakuProcessor] Textream.app 启动超时（15 秒）")
            return False
        except Exception as e:
            logger.error(f"[DanmakuProcessor] 启动 Textream.app 失败: {e}")
            return False

    async def launch(self):
        """
        引擎初始化：自动检测 DirectorServer 并切换引擎

        检测 Textream.app 内的 DirectorServer（端口 7575）是否可用。
        如果可用，使用 DirectorDanmakuCapture（截图权限归 Textream.app）。
        否则回退到 PIL.ImageGrab（需要 Python 进程有屏幕录制权限）。

        注意：macOS 15+ 上无论 PIL.ImageGrab 还是 screencapture，
        都需要调用进程有屏幕录制权限。避免此问题的唯一方法是使用
        DirectorServer（Textream.app 内置 HTTP 截图服务）。
        """
        if self._launched or self._use_captiocr:
            return

        self._launched = True

        # 尝试 DirectorServer
        director = DirectorDanmakuCapture(
            capture_interval=1.0,
            lang=self._ocr_lang,
            timeout=2.0,
        )

        # 复制区域和回调
        if self.capture.bbox:
            x, y, w, h = self.capture.bbox
            director.set_region(x, y, w - x, h - y)

        if await director._check_director_available():
            self.capture = director
            self._capture_engine = "director_server"
            logger.info(f"[DanmakuProcessor] 切换到 DirectorServer 引擎 (端口 {director.DEFAULT_HTTP_PORT})")
            logger.info("[DanmakuProcessor] 截图权限归 Textream.app，不再弹 One.app 权限窗")
        else:
            # DirectorServer 不可用，尝试启动 Textream.app
            logger.info("[DanmakuProcessor] DirectorServer 不可用，尝试启动 Textream.app")
            launched = await self._launch_textream_app()
            if launched:
                # 等待 DirectorServer 就绪
                for i in range(5):
                    await asyncio.sleep(1)
                    if await director._check_director_available():
                        self.capture = director
                        self._capture_engine = "director_server"
                        logger.info(f"[DanmakuProcessor] Textream.app 启动后 DirectorServer 就绪 (端口 {director.DEFAULT_HTTP_PORT})")
                        return
                logger.warning("[DanmakuProcessor] Textream.app 已启动但 DirectorServer 未就绪，使用 PIL.ImageGrab 回退（需要屏幕录制权限）")
            else:
                logger.info("[DanmakuProcessor] Textream.app 未安装或无法启动，使用 PIL.ImageGrab 回退（需要屏幕录制权限）")

            self._capture_engine = "pil_imagegrab"
            # 如果已经是 DanmakuCapture 实例则无需更换
            if not isinstance(self.capture, DanmakuCapture):
                fallback = DanmakuCapture(capture_interval=1.0, lang=self._ocr_lang)
                if self.capture.bbox:
                    x, y, w, h = self.capture.bbox
                    fallback.set_region(x, y, w - x, h - y)
                self.capture = fallback
            logger.info("[DanmakuProcessor] 使用 PIL.ImageGrab 回退引擎（需要 Python 有屏幕录制权限）")

    def set_region(self, x: int, y: int, width: int, height: int):
        """设置截图区域，同时通知前端清空旧弹幕"""
        self.capture.set_region(x, y, width, height)
        # 通知前端清空弹幕列表，避免新旧区域混淆
        if self.websocket_callback:
            try:
                # 使用 asyncio 主动调度（可能被同步上下文调用）
                import asyncio
                asyncio.ensure_future(self.websocket_callback({
                    "type": "clear_danmaku",
                    "timestamp": __import__("time").time() * 1000,
                }))
            except Exception:
                pass

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
            if error_bus:
                error_bus.report("danmaku", "error", "启动失败：未设置截图区域")
            raise ValueError("请先设置截图区域 (set_region)")

        self.running = True

        # 设置弹幕捕获回调：OCR 文本 → 前端推送 + AI 应答生成
        async def on_danmaku(texts: list[str]):
            for text in texts:
                # 1) 推送到前端
                if self.websocket_callback:
                    msg = {
                        "text": text,
                        "timestamp": time.time() * 1000,
                        "platform": self._capture_engine or "unknown",
                    }
                    await self.websocket_callback(msg)
                    logger.info(f"[DanmakuProcessor] 推送到前端: {text}")

                # 2) 触发 AI 应答生成（3 档话术）
                await self._process_single_danmaku(text)

        # CaptiOCR 需要设置事件循环才能从后台线程调度异步回调
        if hasattr(self.capture, 'set_loop'):
            self.capture.set_loop(asyncio.get_event_loop())

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

        # 自动保存弹幕交互到记忆系统
        await self._save_interaction(text)

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
            if error_bus:
                error_bus.report("llm", "error", f"弹幕处理失败: {e}", {"text": text[:50]})

    async def _save_interaction(self, text: str):
        """
        将弹幕交互自动保存到记忆系统

        用于积累主播的应答风格和常见话题，以后生成更精准的回复。
        """
        mgr = getattr(self, '_memory_manager', None)
        if not mgr:
            return

        try:
            # 为记忆管理器增加记忆条目
            # AIMemoryManager 和 LocalMemoryManager 都支持 add 方法
            if hasattr(mgr, 'add'):
                if hasattr(mgr, 'add') and callable(mgr.add):
                    await mgr.add(
                        title=f"弹幕：{text[:30]}",
                        content=text,
                        tags=["danmaku", "auto"],
                        importance=2,
                    )
        except Exception as e:
            logger.debug(f"[DanmakuProcessor] 自动保存弹幕记忆失败（非关键）: {e}")

    async def set_capture_interval(self, interval: float):
        """动态调整捕获间隔（秒），0.1~5.0"""
        interval = max(0.1, min(5.0, interval))
        self.capture.capture_interval = interval
        logger.info(f"[DanmakuProcessor] 捕获间隔调整为 {interval}s")

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
