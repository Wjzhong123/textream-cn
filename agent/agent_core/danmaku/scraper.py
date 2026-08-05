"""
弹幕截图 + OCR 识别模块

OCR 引擎：
  - RapidOCR（主力，基于 ONNX Runtime）— 中文识别精度远超 Tesseract，跳过文本检测 (~0.4s/帧)
  - 旧版 Tesseract 已弃用（弹幕彩色小字场景精度差）
  - 安装: pip install rapidocr onnxruntime

双引擎架构：
  1. DirectorDanmakuCapture（主力，默认）— 通过 Textream.app 的 DirectorServer 获取截图
     ✅ 屏幕权限归 Textream.app，权限弹窗显示"Textream"而非"Python"
  2. DanmakuCapture（fallback）— 直接使用 PIL.ImageGrab + RapidOCR

流程：
  Textream.app (Swift) → DirectorServer REST API → 本模块 HTTP 获取截图 → RapidOCR
"""

import asyncio
import base64
import logging
import os
import re
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

import numpy as np
import cv2
from PIL import Image

# 换用 RapidOCR（基于 ONNX Runtime，中文识别精度远超 Tesseract）
# 安装: pip install rapidocr onnxruntime
from rapidocr import RapidOCR

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
        # 模糊去重缓存：核心内容 + 首次出现时间戳。
        # 用相似度匹配而非完全相等，避免 OCR 识别同一条弹幕时
        # 名字/标点有细微噪声导致去重失效、重复推送。
        self._core_cache: dict[str, float] = {}
        self.cache_max_size = 500
        self._dedup_similarity = 0.85  # 相似度阈值，超过视为同一条弹幕
        self._dedup_ttl = 20.0  # 秒；超过后允许同内容弹幕再次出现
        # 多帧确认缓存：core -> {text, first_seen}。
        # 弹幕会停留多帧，第一帧识别常有噪声；同一弹幕至少确认 2 帧、
        # 取两帧中更完整的文本再推送，显著降低"同一条弹幕识别出不同结果"。
        self._pending: dict[str, dict] = {}
        self._pending_confirm_timeout = 2.0  # 秒；超过后未确认也推送（防丢弹幕）
        self.running = False
        self.callback: Any = None
        self.capture_interval = capture_interval
        self.lang = lang
        self._director_available: bool | None = None  # None = 未检测

        # RapidOCR 引擎（基于 ONNX Runtime，中文识别精度远超 Tesseract）
        # 弹幕区域是纯文本区域，跳过文本检测 (`use_det=False`) 只做识别，速度翻倍。
        self._rapid_ocr = RapidOCR()
        self._rapid_text_score = 0.5  # 低于此置信度的文本丢弃

        logger.info(f"[DirectorDanmakuCapture] 初始化 (DirectorServer={self.base_url}, interval={capture_interval}s)")

    # ── 接口兼容方法（与 DanmakuCapture 一致） ──────────────────────────

    def set_region(self, x: int, y: int, width: int, height: int):
        """设置截图区域（同时清空 OCR 去重缓存，避免新旧区域混淆）"""
        self._region_params = {"x": x, "y": y, "w": width, "h": height}
        self.bbox = (x, y, x + width, y + height)
        self.cache.clear()
        self._core_cache.clear()
        self._pending.clear()
        self.cache_max_size = 500
        logger.info(f"[DirectorDanmakuCapture] 截图区域已更新: {self._region_params}，OCR 缓存已清空")

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
                    _t0 = __import__("time").time()
                    new_texts = await self._capture_and_ocr()
                    _t1 = __import__("time").time()
                    ocr_time = _t1 - _t0
                    if new_texts and self.callback:
                        asyncio.create_task(self.callback(new_texts))
                    if ocr_time > 1.5:
                        logger.warning(f"[DirectorDanmakuCapture] 耗时较长: OCR={ocr_time:.1f}s, 文本={len(new_texts)}条")
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

            # 2. OCR 识别（在线程池中运行，避免阻塞事件循环）
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._ocr_image, image_data)

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
        """从 DirectorServer 获取截图并裁剪到指定区域"""
        params = self._region_params
        if not params:
            logger.warning("[DirectorDanmakuCapture] 未设置截图区域")
            return None

        # DirectorServer 忽略 w/h 参数，始终返回全屏，需 Python 端自行裁剪
        path = f"/api/screenshot"

        try:
            response = await asyncio.to_thread(self._http_get, path)
            data = response.get("data")
            if not data:
                logger.warning(f"[DirectorDanmakuCapture] 截图返回无数据: {response}")
                return None

            # 解码全屏 JPEG
            img = Image.open(__import__("io").BytesIO(base64.b64decode(data)))

            # 计算缩放比例（DirectorServer 返回的逻辑坐标 vs 实际物理像素）
            # 例：声明 1680x1050，实际 3360x2100 → 缩放 2x
            json_w, json_h = response.get("width", 0), response.get("height", 0)
            scale_x = img.size[0] / json_w if json_w else 1
            scale_y = img.size[1] / json_h if json_h else 1

            # 将逻辑坐标转换为物理像素并裁剪
            crop = img.crop((
                int(params["x"] * scale_x),
                int(params["y"] * scale_y),
                int((params["x"] + params["w"]) * scale_x),
                int((params["y"] + params["h"]) * scale_y),
            ))
            buf = __import__("io").BytesIO()
            crop.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
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
        """
        对 JPEG 数据进行 OCR 识别（RapidOCR 引擎，行聚类 + 单行识别 + 弹幕拼接）

        设计说明：
        - use_det=True（完整检测）能完美识别多行弹幕，但 1.8s/帧太慢
        - use_det=False 假设单行，对多行 region 识别不准、换行会拆开
        - 方案：水平投影拆行（~35ms/行）→ 按行距聚类成弹幕 → 每行单行识别
          → 同一弹幕的多行拼接成一条完整文本（长评论不拆开）
        """
        # 1. 解码 JPEG → numpy (RGB → BGR, RapidOCR 需要 BGR 格式)
        img = Image.open(__import__("io").BytesIO(image_data))
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. 水平投影拆行：找到每一行文本的 y 区间
        #    弹幕列表是深色背景 + 亮色文字 → 检测亮像素比例找文本行
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright_per_row = (gray > 180).sum(axis=1)  # 每行亮像素数

        # 双条件：绝对像素数 >= 8（短文本"跑了"在宽区域占比 <2%，
        # 比例阈值会漏掉），或占比 >= 0.5%（防止宽区域噪声行）
        def _is_text_row(y: int) -> bool:
            return bright_per_row[y] >= 8 or bright_per_row[y] >= w * 0.005

        in_text = False
        row_regions = []  # [(y_start, y_end), ...] 按 y 排序
        region_start = 0
        for y in range(h):
            if _is_text_row(y) and not in_text:
                in_text = True
                region_start = y
            elif not _is_text_row(y) and in_text:
                in_text = False
                if y - region_start > 5:
                    row_regions.append((region_start, y))
        if in_text and h - region_start > 5:
            row_regions.append((region_start, h))

        # 3. 按行距聚类：相邻行 gap 小 → 同一弹幕的换行；gap 大 → 不同弹幕
        #    截图实测：弹幕行高 ~30px，换行 gap 4-8px，不同弹幕 gap > 50px
        LINE_MERGE_GAP = 20  # gap < 20px 视为同一弹幕的换行
        groups = []  # [[(y0,y1), ...], ...]
        cur: list = []
        for r in row_regions:
            if cur and r[0] - cur[-1][1] > LINE_MERGE_GAP:
                groups.append(cur)
                cur = []
            cur.append(r)
        if cur:
            groups.append(cur)

        # 4. 每组弹幕：每行单独用 use_det=False 识别（单行假设 → 准确），
        #    多行结果用空格拼接成一条完整弹幕（长评论换行不拆开）
        MIN_REC_HEIGHT = 32  # RapidOCR 识别模型最小高度
        lines = []
        for group in groups:
            group_texts = []
            for y_start, y_end in group:
                region = frame[y_start:y_end, :, :]
                if region.shape[0] < MIN_REC_HEIGHT:
                    pad_top = (MIN_REC_HEIGHT - region.shape[0]) // 2
                    pad_bottom = MIN_REC_HEIGHT - region.shape[0] - pad_top
                    region = cv2.copyMakeBorder(region, pad_top, pad_bottom, 0, 0,
                                                cv2.BORDER_CONSTANT, value=(255, 255, 255))
                try:
                    result = self._rapid_ocr(region, use_det=False, use_cls=True, use_rec=True)
                    if hasattr(result, "txts") and result.txts:
                        for text in result.txts:
                            if isinstance(text, str):
                                for line in text.split("\n"):
                                    line = line.strip()
                                    if line:
                                        group_texts.append(line)
                except Exception as e:
                    logger.debug(f"[DirectorDanmakuCapture] 行识别跳过 ({y_start}-{y_end}): {e}")
                    continue
            if group_texts:
                # 清理弹幕列表左侧的行号序号（如 "17①"、"34⑩"），
                # 这是应用 UI 的行号，不是弹幕内容
                joined = " ".join(group_texts)
                joined = re.sub(r'^\d{1,3}[①-⑩]?\s*', '', joined)
                if joined:
                    lines.append(joined)

        # 5. 清洗、多帧确认与去重
        new_lines = []
        now = time.time()

        # 5.0 超时未确认的待确认弹幕 → 直接推送（避免弹幕太快滚过导致永久丢失）
        for core, info in list(self._pending.items()):
            if now - info["first_seen"] > self._pending_confirm_timeout:
                del self._pending[core]
                if info["text"] not in self.cache:
                    self.cache.add(info["text"])
                    self._core_cache[core] = now
                    new_lines.append(info["text"])

        for line in lines:
            if not self._is_meaningful_text(line):
                continue

            # 模糊去重：提取核心内容（去掉用户名前缀），避免"小明:你好"和"小红:你好"重复
            core = self._extract_core(line)
            if self._is_duplicate(core):
                continue

            if core in self._pending:
                # 多帧确认：同一弹幕再次出现，取两帧中更完整的文本再推送。
                # 第一次识别可能有噪声（名字乱码/漏字），第二帧往往更清晰。
                info = self._pending.pop(core)
                final_text = line if len(line) >= len(info["text"]) else info["text"]
                self._core_cache[core] = now
                if final_text not in self.cache:
                    self.cache.add(final_text)
                    new_lines.append(final_text)
            else:
                # 首次出现：检查是否与待确认队列中的核心相似（OCR 噪声下
                # 同一弹幕不同帧的核心可能有细微差异），相似则视为确认。
                confirmed_key = self._find_similar_pending(core)
                if confirmed_key is not None:
                    info = self._pending.pop(confirmed_key)
                    final_text = line if len(line) >= len(info["text"]) else info["text"]
                    self._core_cache[core] = now
                    if final_text not in self.cache:
                        self.cache.add(final_text)
                        new_lines.append(final_text)
                else:
                    # 真正首次出现 → 进入待确认队列，等下一帧确认
                    self._pending[core] = {"text": line, "first_seen": now}

        logger.debug(f"[DirectorDanmakuCapture] OCR 识别到 {len(new_lines)} 条新文本")
        return new_lines

    @staticmethod
    def _extract_core(text: str) -> str:
        """提取文本核心内容（去掉用户名前缀），用于模糊去重"""
        import re
        # 优先：找冒号分隔符（弹幕标准格式"名字: 内容"），取冒号后的内容。
        # OCR 噪声下名字可能含空格/特殊字符（如 "@2 & 李不管 泽**xxx: 内容"），
        # 不能靠"非冒号字符"匹配，必须直接用冒号定位。
        m = re.search(r'[:：]', text)
        if m:
            text = text[m.end():].strip()
        # 无冒号 → 保留全文（无法可靠判断名字边界，宁可保留也不误删内容）
        # 去掉末尾标点
        text = re.sub(r'[，。！？、；：""''【】《》…~]+$', '', text)
        return text.strip()

    def _is_duplicate(self, core: str) -> bool:
        """
        判断核心内容是否与缓存中的某条重复（相似度去重）

        OCR 识别同一条滚动弹幕时，名字/标点常有细微噪声，完全相等判断
        会漏掉这些"看起来不同实则相同"的弹幕。这里用 SequenceMatcher
        相似度 > 阈值视为同一条，且超过 TTL 后允许相同内容再次出现
        （避免弹幕重复轰炸被永久吞掉）。
        """
        import difflib
        now = time.time()
        stale_keys = [k for k, ts in self._core_cache.items() if now - ts > self._dedup_ttl]
        for k in stale_keys:
            self._core_cache.pop(k, None)

        # 极短内容（<=2字）直接精确匹配，避免误杀不同弹幕
        if len(core) <= 2:
            return core in self._core_cache

        for cached in self._core_cache:
            sim = difflib.SequenceMatcher(None, cached, core).ratio()
            if sim >= self._dedup_similarity:
                # 命中重复：刷新时间戳（避免长时间不出现）
                self._core_cache[cached] = now
                return True
        return False

    def _find_similar_pending(self, core: str) -> str | None:
        """
        在待确认队列中查找与 core 相似的核心内容（相似度匹配）

        OCR 噪声下同一弹幕不同帧的核心可能有细微差异（如漏字/错字），
        用相似度匹配确认，而不是依赖精确相等。
        Returns:
            命中的 pending key；无则返回 None
        """
        import difflib
        best_key: str | None = None
        best_sim = 0.0
        for key in self._pending:
            sim = difflib.SequenceMatcher(None, key, core).ratio()
            if sim > best_sim:
                best_sim = sim
                best_key = key
        if best_key is not None and best_sim >= self._dedup_similarity:
            return best_key
        return None

        logger.debug(f"[DirectorDanmakuCapture] OCR 识别到 {len(new_lines)} 条新文本")
        return new_lines

    @staticmethod
    def _is_meaningful_text(text: str) -> bool:
        """
        判断 OCR 文本是否有意义（过滤垃圾识别结果）

        过滤规则：
        - 太少字符（< 2）→ 过滤
        - 不含中文字符 → 过滤（弹幕场景主要是中文）
        - 中文字符 < 3 个 → 过滤（避免送礼动画"送出了 x1"等误识别）
        - 中文占比 < 25% → 过滤
        - 包含送礼/礼物特征（"x1"/"x2"/"BH"/"DB" 等大写字母+数字组合）→ 过滤
        - 入场通知（"来了"、"等\d+人"）→ 过滤
        """
        if len(text) < 2:
            return False

        # 统计中文字符（Unicode CJK 统一表意文字区块）
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if chinese_chars < 3:
            return False

        # 中文占比
        ratio = chinese_chars / len(text)
        if ratio < 0.25:
            return False

        import re

        # 过滤送礼/礼物特征：文本中同时包含大写字母和数字的短片段
        # 典型模式："送出了 BH x1"、"ADH x1"、"图 x1"
        # 匹配 "大写字母+数字" 组合（如 BH1, x1, x2, DB x1）
        if re.search(r'[A-Z]{2,}\s*x?\d', text):
            return False
        # 匹配 "x1"、"x2" 等礼物倍数
        if re.search(r'\bx\d\b', text):
            return False

        # 过滤入场通知：如"鹏(*^_^*)哥等35人来了"、"小武。等50人来了"
        # 模式：等 + 数字 + 人 + 来了，或 来了 结尾
        if re.search(r'等\d+人', text) or re.search(r'来了$', text):
            return False

        # 过滤送礼/互动消息
        # 典型：送人气票、送玫瑰、送表情、送xxx
        if re.search(r'^送', text):
            return False
        # 送礼消息常见形态（OCR 合并后）："名字:送出了 粉丝团 × 1"
        # 注意名字前缀可能让 ^送 匹配不到，必须全文搜索关键词
        if re.search(r'送出了', text):
            return False
        # 礼物倍数：全角 × 或半角 x 加数字（"× 1"、"x2"）
        if re.search(r'[×xX]\s*\d', text):
            return False
        # 纯礼物名称：玫瑰、人气票、荧光棒、小心心、粉丝牌等
        gift_keywords = ['人气票', '荧光棒', '小心心', '粉丝牌', '大啤酒', '亲密度', '粉丝团', '玫瑰', '表情', '穿云箭', '火箭', '嘉年华']
        for kw in gift_keywords:
            if kw in text:
                return False

        return True

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

    通过 PIL.ImageGrab 截图 + pytesseract OCR。
    注意：macOS 上 PIL.ImageGrab 底层也调用 screencapture，因此需要
    Python 进程有屏幕录制权限。推荐使用 DirectorServer（Textream.app）
    来避免权限问题。
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
        self.cache.clear()
        logger.info(f"[DanmakuCapture] 截图区域已更新: bbox={self.bbox}，OCR 缓存已清空")

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
                    _t0 = __import__("time").time()
                    new_texts = await self._capture_and_ocr()
                    _t1 = __import__("time").time()
                    ocr_time = _t1 - _t0
                    if new_texts and self.callback:
                        # 异步触发回调，不阻塞截图循环
                        asyncio.create_task(self.callback(new_texts))
                    if ocr_time > 1.5:
                        logger.warning(f"[DanmakuCapture] 耗时较长: OCR={ocr_time:.1f}s, 文本={len(new_texts)}条")
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
        """
        使用 PIL.ImageGrab 截图 + pytesseract OCR

        注意：macOS 上 PIL.ImageGrab 底层调用 screencapture，因此 Python 进程
        需要屏幕录制权限。推荐使用 DirectorDanmakuCapture 来避免权限问题。
        """
        if not self.bbox:
            return []

        x, y, right, bottom = self.bbox

        try:
            # PIL.ImageGrab 底层调用 macOS screencapture
            img = ImageGrab.grab(bbox=(x, y, right, bottom))
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
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
        logger.info("[create_capture] DirectorServer 不可用，回退到 PIL.ImageGrab（需要屏幕录制权限）")

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
