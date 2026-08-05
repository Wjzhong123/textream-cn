"""
Textream 智能体内核 v2.0 - FastAPI 主服务

记忆系统：
- 主推：AI-memory（wang-jie-git/AI-memory，MCP 子进程，语义搜索）
- 回退：LocalMemoryManager（JSON 文件）
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

# 添加 agent 目录到 Python 路径
agent_dir = Path(__file__).parent.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from agent_core.config import get_settings
from agent_core.error_bus import error_bus
from agent_core.knowledge.manager import KnowledgeManager
from agent_core.llm.router import LLMRouter
from agent_core.memory import AIMemoryManager, LocalMemoryManager
from agent_core.danmaku.processor import DanmakuProcessor, ResponseStyle

settings = get_settings()
logger = logging.getLogger(__name__)

# 全局管理器实例（延迟初始化）
memory_mgr: LocalMemoryManager | None = None
ai_memory_mgr: AIMemoryManager | None = None
knowledge_mgr: KnowledgeManager | None = None
llm_router: LLMRouter | None = None
danmaku_processor: DanmakuProcessor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global memory_mgr, ai_memory_mgr, knowledge_mgr, llm_router, danmaku_processor

    # 初始化管理器
    memory_mgr = LocalMemoryManager()
    llm_router = LLMRouter()

    # AI-memory 集成（通过 MCP 子进程调用 wang-jie-git/AI-memory）
    ai_memory = AIMemoryManager()
    if ai_memory.is_available:
        try:
            await ai_memory._ensure_client()
            ai_memory_mgr = ai_memory
            print("   ✅ AI-memory 已连接（语义记忆）")
        except Exception as e:
            logger.warning(f"AI-memory 连接失败，回退到本地 JSON 记忆: {e}")
            ai_memory_mgr = None
    else:
        print("   ℹ️  AI-memory 未安装（third_party/AI-memory 不存在），使用本地 JSON 记忆")

    # 知识库（AI-memory 可用时自动语义搜索，否则本地子串匹配）
    knowledge_mgr = KnowledgeManager(memory_manager=ai_memory_mgr)

    # 同步：将本地知识库摘要索引到 AI-memory（幂等操作）
    if ai_memory_mgr:
        await knowledge_mgr._sync_local_to_ai()

    # 弹幕处理器（DirectorServer 自动检测 + AI-memory + 知识库）
    danmaku_processor = DanmakuProcessor(
        memory_manager=ai_memory_mgr,  # None 时回退到本地记忆
        knowledge_manager=knowledge_mgr,
        llm_provider=settings.llm_provider if settings.llm_provider != "none" else None,
        use_captiocr=False,  # 默认 DirectorServer 引擎（自动检测 Textream.app）
    )

    # 启动时自动拉起 Textream.app 的 DirectorServer（确保截图权限归 Textream.app）
    # 这样用户点击「开始捕获」时 DirectorServer 已经就绪，不会回退到 PIL
    try:
        await danmaku_processor.launch()
    except Exception as e:
        logger.warning(f"启动时自动拉起 Textream.app 失败（非关键，用户点击捕获时会重试）: {e}")

    print(f"🤖 Textream Agent Core v2.0 starting on port {settings.agent_port}")
    print(f"   记忆: {'AI-memory (语义搜索)' if ai_memory_mgr else '本地 JSON 文件'}")

    yield

    # 关闭时
    if danmaku_processor:
        await danmaku_processor.stop()
    if ai_memory_mgr:
        await ai_memory_mgr.close()
    print("👋 Textream Agent Core shutting down")


def _show_standalone_selector():
    """
    独立启动 CaptiOCR 区域选择器（子进程方式）。
    tkinter 必须在主线程运行，但 FastAPI 工作在线程池中，
    因此将选择器隔离到独立子进程执行，通过 stdout 传回结果。
    返回 (x, y, width, height) 或 None。
    """
    import subprocess
    import json

    _agent_dir = Path(__file__).parent.parent
    _script = str(_agent_dir / "scripts" / "run_selector.py")

    if not Path(_script).is_file():
        logger.error(f"选择器脚本不存在: {_script}")
        return None

    try:
        result = subprocess.run(
            [sys.executable, _script],
            capture_output=True, text=True, timeout=120,
            cwd=str(_agent_dir),
        )
        if result.returncode != 0:
            logger.error(f"选择器进程异常: {result.stderr.strip()}")
            return None

        data = json.loads(result.stdout.strip())
        if data is None:
            return None

        return (data["x"], data["y"], data["width"], data["height"])
    except subprocess.TimeoutExpired:
        logger.warning("选择器超时（用户可能未操作）")
        return None
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.error(f"选择器结果解析失败: {e}")
        return None


def _extract_file_text(filename: str, content: bytes) -> str | None:
    """
    从上传文件中提取纯文本内容。
    支持 .txt .md .json .docx .doc
    """
    import re
    import subprocess
    import tempfile
    from pathlib import Path

    ext = Path(filename).suffix.lower()

    if ext in (".txt", ".md"):
        return content.decode("utf-8", errors="replace")

    if ext == ".json":
        return content.decode("utf-8", errors="replace")

    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"解析 .docx 失败: {e}")
            return None

    if ext == ".doc":
        # macOS 内置 textutil 可转换 .doc → .txt
        try:
            with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            out_path = tmp_path + ".txt"
            subprocess.run(
                ["textutil", "-convert", "txt", "-output", out_path, tmp_path],
                capture_output=True, timeout=30,
            )
            result = Path(out_path).read_text(encoding="utf-8", errors="replace")
            Path(tmp_path).unlink(missing_ok=True)
            Path(out_path).unlink(missing_ok=True)
            return result
        except Exception as e:
            logger.error(f"解析 .doc 失败: {e}")
            return None

    return None


def require_api_key(authorization: str | None = Header(default=None)):
    """API 鉴权依赖：默认放行（本地应用）；设置 TEXTREAM_API_KEY 后强制校验 Bearer token。

    设计说明：Textream 是本地桌面应用，前端直连 localhost。
    默认无密钥时保持零配置可用；设置 TEXTREAM_API_KEY 后所有路由
    要求 Authorization: Bearer <key>，用于局域网/公网部署场景。
    """
    expected = os.environ.get("TEXTREAM_API_KEY", "").strip()
    if not expected:
        return {"authenticated": True, "source": "open"}
    if authorization and authorization.startswith("Bearer ") and authorization[7:].strip() == expected:
        return {"authenticated": True, "source": "api_key"}
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key",
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Textream Agent Core",
        description="直播/演讲 AI 军师 - 智能提词器 + 弹幕联动 + 知识库",
        version="2.0.0-alpha",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health ─────────────────────────────────────────────────────────────
    @app.get("/api/health")
    async def health(_auth: dict = Depends(require_api_key)):
        return {
            "status": "ok",
            "version": "2.0.0-alpha",
            "timestamp": datetime.now().isoformat(),
        }

    # ── Status ─────────────────────────────────────────────────────────────
    @app.get("/api/status")
    async def status(_auth: dict = Depends(require_api_key)):
        if not memory_mgr or not knowledge_mgr:
            return {"agent": "initializing", "version": "2.0.0-alpha"}

        # AI-memory 优先
        active_mgr = ai_memory_mgr or memory_mgr
        if ai_memory_mgr:
            memories_count = len(await ai_memory_mgr.search("", limit=100))
        else:
            memories_count = len(memory_mgr._cache) if hasattr(memory_mgr, '_cache') else 0

        knowledge = await knowledge_mgr.list() if knowledge_mgr else []
        return {
            "agent": "online",
            "version": "2.0.0-alpha",
            "memory": {
                "count": memories_count,
                "backend": "ai_memory" if ai_memory_mgr else "json_file",
                "enabled": settings.memory_enabled,
            },
            "knowledge": {
                "count": len(knowledge),
                "enabled": settings.knowledge_enabled,
            },
            "llm": {
                "provider": settings.llm_provider,
                "configured": bool(os.environ.get(f"{settings.llm_provider.upper()}_API_KEY")),
            },
        }

    # ── Memory（AI-memory 优先，回退到本地 JSON） ──────────────────────────
    def _get_active_memory():
        """活跃的记忆管理器（AI-memory 优先）"""
        return ai_memory_mgr or memory_mgr

    @app.get("/api/memory/list")
    async def list_memories(limit: int = 50, offset: int = 0, user_id: str = "default", tag: str | None = None, _auth: dict = Depends(require_api_key)):
        mgr = _get_active_memory()
        if not mgr:
            return {"total": 0, "offset": offset, "limit": limit, "items": []}
        if isinstance(mgr, AIMemoryManager):
            items = await mgr.list(limit=limit, offset=offset, user_id=user_id, tag=tag)
        else:
            items = mgr.list(limit=limit, offset=offset, user_id=user_id, tag=tag)
        return {"total": len(items), "offset": offset, "limit": limit, "items": items}

    @app.post("/api/memory/add")
    async def add_memory(entry: dict, _auth: dict = Depends(require_api_key)):
        """添加记忆（支持 JSON body）"""
        mgr = _get_active_memory()
        if not mgr:
            raise HTTPException(status_code=503, detail="Memory not available")
        title = entry.get("title", "")
        content = entry.get("content", "")
        tags = entry.get("tags", [])
        importance = entry.get("importance", 3)
        user_id = entry.get("user_id", "default")
        if isinstance(mgr, AIMemoryManager):
            result = await mgr.add(title=title, content=content, tags=tags, importance=importance, user_id=user_id)
        else:
            result = mgr.add(title=title, content=content, tags=tags, importance=importance, user_id=user_id)
        return {"status": "ok", "id": result.get("id", "?")}

    @app.delete("/api/memory/delete/{memory_id}")
    async def delete_memory(memory_id: str, _auth: dict = Depends(require_api_key)):
        mgr = _get_active_memory()
        if not mgr:
            raise HTTPException(status_code=503, detail="Memory not available")
        if isinstance(mgr, AIMemoryManager):
            ok = await mgr.delete(memory_id)
        else:
            ok = mgr.delete(memory_id)
        if ok:
            return {"status": "deleted", "id": memory_id}
        raise HTTPException(status_code=404, detail="Memory not found")

    @app.get("/api/memory/search")
    async def search_memory(q: str, limit: int = 20, user_id: str = "default", _auth: dict = Depends(require_api_key)):
        mgr = _get_active_memory()
        if not mgr:
            return {"query": q, "items": []}
        if isinstance(mgr, AIMemoryManager):
            items = await mgr.search(query=q, limit=limit, user_id=user_id)
        else:
            items = mgr.search(q, limit=limit)
            if user_id != "default":
                items = [m for m in items if m.get("user_id") == user_id]
        return {"query": q, "items": items}

    @app.get("/api/memory/persona")
    async def api_get_persona(user_id: str = "default", _auth: dict = Depends(require_api_key)):
        """获取用户画像"""
        mgr = _get_active_memory()
        if not mgr:
            return {"tags": [], "memory_count": 0, "source": "unavailable"}
        if isinstance(mgr, AIMemoryManager):
            return await mgr.get_persona(user_id)
        return mgr.get_persona(user_id)

    @app.get("/api/memory/error-book")
    async def api_get_error_book(user_id: str = "default", _auth: dict = Depends(require_api_key)):
        """获取错题本"""
        mgr = _get_active_memory()
        if not mgr:
            return {"items": []}
        if isinstance(mgr, AIMemoryManager):
            items = await mgr.get_error_book(user_id)
        else:
            items = mgr.get_error_book(user_id)
        return {"items": items}

    # ── Knowledge ───────────────────────────────────────────────────────────
    @app.get("/api/knowledge/list")
    async def list_knowledge(_auth: dict = Depends(require_api_key)):
        if not knowledge_mgr:
            return {"items": []}
        items = await knowledge_mgr.list()
        return {"items": items}

    @app.get("/api/knowledge/search")
    async def search_knowledge(q: str, _auth: dict = Depends(require_api_key)):
        if not knowledge_mgr:
            return {"query": q, "items": []}
        return {"query": q, "items": await knowledge_mgr.search(q)}

    @app.post("/api/knowledge/add")
    async def add_knowledge(request: dict, _auth: dict = Depends(require_api_key)):
        """添加知识库文档（支持 JSON body 或 form data）"""
        if not knowledge_mgr:
            raise HTTPException(status_code=503, detail="Knowledge not available")
        name = request.get("name", "")
        content = request.get("content", "")
        if not name or not content:
            raise HTTPException(status_code=400, detail="name and content are required")
        result = await knowledge_mgr.add_file(name, content)
        return {"status": "ok", **result}

    @app.post("/api/knowledge/upload")
    async def upload_knowledge(file: UploadFile = File(...), _auth: dict = Depends(require_api_key)):
        """上传知识库文档（支持 .txt .md .json .docx .doc）"""
        if not knowledge_mgr:
            raise HTTPException(status_code=503, detail="Knowledge not available")

        filename = file.filename or "unnamed"
        content_bytes = await file.read()

        # 提取文本内容
        text = _extract_file_text(filename, content_bytes)
        if text is None:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式或解析失败: {filename}",
            )

        result = await knowledge_mgr.add_file(filename, text)
        return {"status": "ok", "filename": filename, **result}

    @app.delete("/api/knowledge/delete/{name}")
    async def delete_knowledge(name: str, _auth: dict = Depends(require_api_key)):
        if not knowledge_mgr:
            raise HTTPException(status_code=503, detail="Knowledge not available")
        if knowledge_mgr.delete_file(name):
            return {"status": "deleted", "name": name}
        raise HTTPException(status_code=404, detail="Knowledge file not found")

    # ── Chat ───────────────────────────────────────────────────────────────
    @app.post("/api/chat")
    async def chat(request: dict, _auth: dict = Depends(require_api_key)):
        """LLM 聊天（支持记忆 + 知识库增强）"""
        message = request.get("message", "")
        user_id = request.get("user_id", "default")
        use_memory = request.get("use_memory", True)
        use_knowledge = request.get("use_knowledge", True)
        context_parts = []

        # 记忆检索：AI-memory 语义搜索 / 本地 JSON 回退
        mgr = _get_active_memory()
        if use_memory and mgr:
            if isinstance(mgr, AIMemoryManager):
                memories = await mgr.search(query=message, limit=10, user_id=user_id)
            else:
                memories = mgr.list(limit=10, user_id=user_id)
            if memories:
                context_parts.append("## 用户记忆")
                for m in memories:
                    ts = m.get('timestamp', '')[:10] if m.get('timestamp') else ''
                    content = m.get('content', '') or m.get('summary', '') or ''
                    context_parts.append(f"- [{ts}] {m.get('title', '')}: {content[:200]}")

        if use_knowledge:
            knowledge_results = await knowledge_mgr.search(message)
            if knowledge_results:
                context_parts.append("\n## 知识库检索结果")
                for k in knowledge_results[:3]:
                    context_parts.append(f"- **{k['name']}**: {k['snippet']}")

        context = "\n".join(context_parts) if context_parts else "暂无相关记忆或知识库内容"

        system_prompt = f"""你是一个专业的直播/演讲 AI 军师助手。

{context}

请基于以上信息回答用户的问题。如果记忆和知识库中没有相关信息，请如实告知，并使用你的通用知识给出合理建议。
回答风格：简洁、专业、实用。"""

        try:
            reply = await llm_router.async_chat_with_system(message, system_prompt)
            return {"reply": reply}
        except Exception as e:
            error_bus.report("llm", "error", f"LLM 聊天失败: {e}", {"message": message[:50]})
            raise

    # ── Teleprompter ─────────────────────────────────────────────────────────
    @app.post("/api/teleprompter")
    async def teleprompter(request: dict, _auth: dict = Depends(require_api_key)):
        """将文本投送到 Textream.app 原生提词器（通过 textream:// URL scheme）"""
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        import urllib.parse, asyncio
        encoded = urllib.parse.quote(text)
        proc = await asyncio.create_subprocess_exec(
            "open", f"textream://read?text={encoded}",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        return {"status": "ok", "text": text[:50]}

    # ── Danmaku ──────────────────────────────────────────────────────────────
    @app.get("/api/danmaku/status")
    async def danmaku_status(_auth: dict = Depends(require_api_key)):
        """获取弹幕捕获状态"""
        if not danmaku_processor:
            return {"running": False, "region": None, "engine": None}
        return {
            "running": danmaku_processor.running,
            "region": danmaku_processor.capture.bbox,
            "engine": getattr(danmaku_processor, '_capture_engine', 'unknown'),
            "lang": getattr(danmaku_processor.capture, 'lang', 'chi_sim+eng'),
        }

    @app.get("/api/danmaku/settings")
    async def danmaku_settings_get(_auth: dict = Depends(require_api_key)):
        """获取弹幕捕获设置"""
        return {
            "capture_interval": danmaku_processor.capture.capture_interval if danmaku_processor else 1.0,
            "engine": getattr(danmaku_processor, '_capture_engine', 'unknown') if danmaku_processor else None,
        }

    @app.put("/api/danmaku/settings")
    async def danmaku_settings_update(body: dict, _auth: dict = Depends(require_api_key)):
        """更新弹幕捕获设置"""
        if not danmaku_processor:
            raise HTTPException(status_code=503, detail="Danmaku processor not available")
        if "capture_interval" in body:
            await danmaku_processor.set_capture_interval(float(body["capture_interval"]))
        return {"status": "ok"}

    @app.post("/api/danmaku/start")
    async def danmaku_start(_auth: dict = Depends(require_api_key)):
        """启动弹幕捕获"""
        if not danmaku_processor:
            raise HTTPException(status_code=503, detail="Danmaku processor not available")
        if danmaku_processor.running:
            return {"status": "already_running"}

        try:
            # 后台启动（不阻塞 HTTP 响应）
            task = asyncio.create_task(danmaku_processor.start())
            # 保存任务引用，防止 GC 回收
            danmaku_processor._capture_task = task
            return {"status": "started"}
        except ValueError as e:
            error_bus.report("danmaku", "error", f"启动弹幕捕获失败: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to start danmaku capture: {e}")
            error_bus.report("danmaku", "error", f"启动弹幕捕获异常: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/danmaku/stop")
    async def danmaku_stop(_auth: dict = Depends(require_api_key)):
        """停止弹幕捕获"""
        if not danmaku_processor:
            return {"status": "not_running"}
        await danmaku_processor.stop()
        return {"status": "stopped"}

    @app.post("/api/danmaku/region")
    async def danmaku_region(request: dict, _auth: dict = Depends(require_api_key)):
        """设置截图区域（支持手动坐标 或 CaptiOCR 视觉框选）"""
        if not danmaku_processor:
            raise HTTPException(status_code=503, detail="Danmaku processor not available")

        x = request.get("x", 0)
        y = request.get("y", 0)
        width = request.get("width", 300)
        height = request.get("height", 200)

        danmaku_processor.set_region(x, y, width, height)
        return {"status": "ok", "region": {"x": x, "y": y, "width": width, "height": height}}

    @app.post("/api/danmaku/selector")
    async def danmaku_selector(_auth: dict = Depends(require_api_key)):
        """
        打开 CaptiOCR 视觉区域选择器（tkinter 原生透明遮罩）。
        与当前捕获引擎无关，独立可用。
        通过独立子进程运行（tkinter 需要主线程，FastAPI 工作在线程池中）。
        """
        if not danmaku_processor:
            raise HTTPException(status_code=503, detail="Danmaku processor not available")

        # 始终使用独立子进程方式（tkinter 需要主线程，不能在线程池中运行）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _show_standalone_selector)

        if result is None:
            return {"status": "cancelled", "region": None}

        x, y, w, h = result
        # 将选择的区域同步到处理器
        danmaku_processor.set_region(x, y, w, h)
        return {"status": "ok", "region": {"x": x, "y": y, "width": w, "height": h}}

    @app.post("/api/danmaku/engine")
    async def danmaku_engine(body: dict, _auth: dict = Depends(require_api_key)):
        """
        切换弹幕捕获引擎

        Body:
            {"engine": "director_server"}  — DirectorServer（主力，截屏权限归 Textream.app）
            {"engine": "captiocr"}         — CaptiOCR（视觉框选 + ROVER/TF-IDF 去重）
            {"engine": "pil_imagegrab"}    — PIL.ImageGrab（fallback）
        """
        if not danmaku_processor:
            raise HTTPException(status_code=503, detail="Danmaku processor not available")

        engine = body.get("engine", "").strip().lower()
        if engine not in ("director_server", "captiocr", "pil_imagegrab"):
            raise HTTPException(status_code=400, detail=f"不支持的引擎: {engine}")

        # 如果正在运行，先停止
        was_running = danmaku_processor.running
        if was_running:
            await danmaku_processor.stop()

        # 切换引擎
        if engine == "captiocr":
            from captiocr_adapter import CaptiOCRBridge
            # 保留旧区域设置
            old_bbox = danmaku_processor.capture.bbox
            bridge = CaptiOCRBridge()
            if old_bbox:
                x, y, right, bottom = old_bbox
                bridge.set_region(x, y, right - x, bottom - y)
            danmaku_processor.capture = bridge
            danmaku_processor._capture_engine = "captiocr"
            danmaku_processor._use_captiocr = True
            logger.info("[DanmakuProcessor] 切换到 CaptiOCR 引擎")
        elif engine == "pil_imagegrab":
            from agent_core.danmaku.scraper import DanmakuCapture
            old_bbox = danmaku_processor.capture.bbox
            fallback = DanmakuCapture()
            if old_bbox:
                x, y, right, bottom = old_bbox
                fallback.set_region(x, y, right - x, bottom - y)
            danmaku_processor.capture = fallback
            danmaku_processor._capture_engine = "pil_imagegrab"
            danmaku_processor._use_captiocr = False
            logger.info("[DanmakuProcessor] 切换到 PIL.ImageGrab 引擎")
        else:
            # director_server — 重新检测/启动 DirectorServer
            from agent_core.danmaku.scraper import DirectorDanmakuCapture
            old_bbox = danmaku_processor.capture.bbox
            director = DirectorDanmakuCapture()
            if old_bbox:
                x, y, right, bottom = old_bbox
                director.set_region(x, y, right - x, bottom - y)
            danmaku_processor.capture = director
            danmaku_processor._capture_engine = "director_server"
            danmaku_processor._use_captiocr = False
            logger.info("[DanmakuProcessor] 切换到 DirectorServer 引擎")

        # 如果之前正在运行，重新启动
        if was_running:
            await danmaku_processor.start()

        return {"status": "ok", "engine": engine, "was_running": was_running}

    @app.websocket("/ws/danmaku")
    async def websocket_danmaku(websocket: WebSocket):
        """WebSocket 弹幕推送"""
        await websocket.accept()

        if not danmaku_processor:
            await websocket.send_json({"error": "Danmaku processor not available"})
            await websocket.close()
            return

        # 设置 WebSocket 回调
        async def ws_callback(data: dict):
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")

        danmaku_processor.set_websocket_callback(ws_callback)

        try:
            # 保持连接活跃
            while True:
                data = await websocket.receive_text()
                # 可以处理客户端消息（如调整设置）
                await websocket.send_json({"echo": data})
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # 断开后清除回调，避免继续往关闭的 socket 发送
            if danmaku_processor:
                danmaku_processor.set_websocket_callback(None)
                logger.info("WebSocket callback cleared")

    # ── Model Settings ─────────────────────────────────────────────────────
    @app.get("/api/models/settings")
    async def get_model_settings(_auth: dict = Depends(require_api_key)):
        """获取当前 LLM 配置"""
        if not llm_router:
            return {"provider": settings.llm_provider, "model": settings.llm_model}

        return {
            "provider": llm_router.provider,
            "api_key": "***" if llm_router.api_key else "",
            "base_url": llm_router.base_url,
            "model": llm_router.default_model,
            "configured": llm_router.configured,
        }

    @app.put("/api/models/settings")
    async def update_model_settings(body: dict, _auth: dict = Depends(require_api_key)):
        """更新 LLM 配置（运行时生效，自动持久化）"""
        if not llm_router:
            raise HTTPException(status_code=503, detail="LLM Router not available")

        provider = body.get("provider", llm_router.provider)
        base_url = body.get("base_url", llm_router.base_url)
        api_key = body.get("api_key", llm_router.api_key)
        model = body.get("model", llm_router.default_model)

        llm_router.update_config(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

        return {"status": "ok", "provider": provider, "model": model, "configured": bool(api_key)}

    @app.get("/api/models/providers")
    async def get_model_providers(_auth: dict = Depends(require_api_key)):
        """返回所有支持的 LLM 提供商列表及其默认配置"""
        from agent_core.llm.router import DEFAULT_PROVIDERS

        providers = []
        for key, cfg in DEFAULT_PROVIDERS.items():
            providers.append({
                "id": key,
                "name": key.capitalize(),
                "base_url": cfg["base_url"],
                "default_model": cfg["default_model"],
            })
        return {"providers": providers}

    # ── Error Bus ──────────────────────────────────────────────────────────
    @app.get("/api/errors")
    async def get_errors(limit: int = 50, level: str | None = None, _auth: dict = Depends(require_api_key)):
        """获取错误总线中的错误列表"""
        return {"errors": error_bus.list(limit=limit, level=level), "total": error_bus.count}

    @app.post("/api/errors/clear")
    async def clear_errors(_auth: dict = Depends(require_api_key)):
        """清空错误总线"""
        error_bus.clear()
        return {"status": "cleared"}

    # ── Web Console (静态文件) ─────────────────────────────────────────────
    web_console_dist = agent_dir / "web-console-dist"
    if web_console_dist.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=str(web_console_dist), html=True),
            name="web_console",
        )
        print(f"   🌐 Web Console 静态文件: {web_console_dist}")
    else:
        print(f"   ℹ️  Web Console 未构建（{web_console_dist} 不存在）")

    # ── 错误总线注入（全局可用） ───────────────────────────────────────────
    # 将 error_bus 注入到 app.state，方便各路由访问
    app.state.error_bus = error_bus

    return app
