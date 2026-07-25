"""
Textream 智能体内核 v2.0 - FastAPI 主服务

升级目标：
- Phase 1: 重构 agent_server.py，模块化架构
- Phase 2: 接入 One Memory + 弹幕实时联动
- Phase 3: 跨平台支持 + Windows 打包
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 添加 agent 目录到 Python 路径
agent_dir = Path(__file__).parent.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent_core.config import get_settings
from agent_core.knowledge.manager import KnowledgeManager
from agent_core.llm.router import LLMRouter
from agent_core.memory.manager import MemoryManager as LocalMemoryManager
from agent_core.danmaku.processor import DanmakuProcessor, ResponseStyle

settings = get_settings()
logger = logging.getLogger(__name__)

# 全局管理器实例（延迟初始化）
memory_mgr: LocalMemoryManager | None = None
knowledge_mgr: KnowledgeManager | None = None
llm_router: LLMRouter | None = None
danmaku_processor: DanmakuProcessor | None = None

# One Memory 模式
USE_ONE_MEMORY = os.environ.get("ONE_ROOT") is not None
one_memory_mgr = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global memory_mgr, knowledge_mgr, llm_router, danmaku_processor, one_memory_mgr

    # 启动时
    print(f"🤖 Textream Agent Core v2.0 starting on port {settings.agent_port}")
    print(f"   One Memory: {'enabled' if USE_ONE_MEMORY else 'disabled'}")

    # 初始化管理器
    memory_mgr = LocalMemoryManager()
    knowledge_mgr = KnowledgeManager()
    llm_router = LLMRouter()

    # One Memory 集成（如果可用）
    if USE_ONE_MEMORY:
        try:
            from one_memory_adapter import MemoryManager as OneMemoryManager
            one_memory_mgr = OneMemoryManager()
            async with one_memory_mgr:
                knowledge_mgr.set_memory_manager(one_memory_mgr)
                print("   ✅ One Memory 已连接")
        except Exception as e:
            logger.warning(f"One Memory 连接失败: {e}")

    # 弹幕处理器
    danmaku_processor = DanmakuProcessor(
        memory_manager=one_memory_mgr,
        llm_provider=settings.llm_provider if settings.llm_provider != "none" else None,
    )

    yield

    # 关闭时
    if danmaku_processor:
        await danmaku_processor.stop()
    print("👋 Textream Agent Core shutting down")


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
    async def health():
        return {
            "status": "ok",
            "version": "2.0.0-alpha",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

    # ── Status ─────────────────────────────────────────────────────────────
    @app.get("/api/status")
    async def status():
        if not memory_mgr or not knowledge_mgr:
            return {"agent": "initializing", "version": "2.0.0-alpha"}

        memories_count = len(memory_mgr._cache) if hasattr(memory_mgr, '_cache') else 0
        knowledge = await knowledge_mgr.list() if knowledge_mgr else []
        return {
            "agent": "online",
            "version": "2.0.0-alpha",
            "memory": {
                "count": memories_count,
                "enabled": settings.memory_enabled,
            },
            "knowledge": {
                "count": len(knowledge),
                "enabled": settings.knowledge_enabled,
            },
            "llm": {
                "provider": settings.llm_provider,
                "configured": bool(__import__("os").environ.get(f"{settings.llm_provider.upper()}_API_KEY")),
            },
        }

    # ── Memory ─────────────────────────────────────────────────────────────
    @app.get("/api/memory/list")
    async def list_memories(limit: int = 50, offset: int = 0, user_id: str = "default", tag: str | None = None):
        if not memory_mgr:
            return {"total": 0, "offset": offset, "limit": limit, "items": []}
        items = memory_mgr.list(limit=limit, offset=offset, user_id=user_id, tag=tag)
        return {"total": len(items), "offset": offset, "limit": limit, "items": items}

    @app.post("/api/memory/add")
    async def add_memory(entry: dict):
        """添加记忆（支持 JSON body）"""
        if not memory_mgr:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Memory not available")
        title = entry.get("title", "")
        content = entry.get("content", "")
        tags = entry.get("tags", [])
        importance = entry.get("importance", 3)
        user_id = entry.get("user_id", "default")
        result = memory_mgr.add(title=title, content=content, tags=tags, importance=importance, user_id=user_id)
        return {"status": "ok", "id": result["id"]}

    @app.delete("/api/memory/delete/{memory_id}")
    async def delete_memory(memory_id: str):
        if not memory_mgr:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Memory not available")
        if memory_mgr.delete(memory_id):
            return {"status": "deleted", "id": memory_id}
        raise __import__("fastapi").HTTPException(status_code=404, detail="Memory not found")

    @app.get("/api/memory/search")
    async def search_memory(q: str, limit: int = 20, user_id: str = "default"):
        if not memory_mgr:
            return {"query": q, "items": []}
        items = memory_mgr.search(q, limit=limit)
        # 如果指定了 user_id，过滤结果
        if user_id != "default":
            items = [m for m in items if m.get("user_id") == user_id]
        return {"query": q, "items": items}

    @app.get("/api/memory/persona")
    async def get_persona(user_id: str = "default"):
        """获取用户画像"""
        if not memory_mgr:
            return {"tags": [], "memory_count": 0, "source": "unavailable"}
        return memory_mgr.get_persona(user_id)

    @app.get("/api/memory/error-book")
    async def get_error_book(user_id: str = "default"):
        """获取错题本"""
        if not memory_mgr:
            return {"items": []}
        return {"items": memory_mgr.get_error_book(user_id)}

    # ── Knowledge ───────────────────────────────────────────────────────────
    @app.get("/api/knowledge/list")
    async def list_knowledge():
        if not knowledge_mgr:
            return {"items": []}
        items = await knowledge_mgr.list()
        return {"items": items}

    @app.get("/api/knowledge/search")
    async def search_knowledge(q: str):
        if not knowledge_mgr:
            return {"query": q, "items": []}
        return {"query": q, "items": await knowledge_mgr.search(q)}

    @app.post("/api/knowledge/add")
    async def add_knowledge(request: dict):
        """添加知识库文档（支持 JSON body 或 form data）"""
        if not knowledge_mgr:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Knowledge not available")
        name = request.get("name", "")
        content = request.get("content", "")
        if not name or not content:
            raise __import__("fastapi").HTTPException(status_code=400, detail="name and content are required")
        result = await knowledge_mgr.add_file(name, content)
        return {"status": "ok", **result}

    @app.delete("/api/knowledge/delete/{name}")
    async def delete_knowledge(name: str):
        if not knowledge_mgr:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Knowledge not available")
        if knowledge_mgr.delete_file(name):
            return {"status": "deleted", "name": name}
        raise __import__("fastapi").HTTPException(status_code=404, detail="Knowledge file not found")

    # ── Chat ───────────────────────────────────────────────────────────────
    @app.post("/api/chat")
    async def chat(request: dict):
        """LLM 聊天（支持记忆 + 知识库增强）"""
        message = request.get("message", "")
        user_id = request.get("user_id", "default")
        use_memory = request.get("use_memory", True)
        use_knowledge = request.get("use_knowledge", True)
        """LLM 聊天（支持记忆 + 知识库增强）"""
        context_parts = []

        if use_memory:
            memories = memory_mgr.list(limit=10, user_id=user_id)
            if memories:
                context_parts.append("## 用户记忆")
                for m in memories:
                    context_parts.append(f"- [{m.get('timestamp', '')[:10]}] {m.get('title', '')}: {m.get('content', '')[:200]}")

        if use_knowledge:
            knowledge_results = knowledge_mgr.search(message)
            if knowledge_results:
                context_parts.append("\n## 知识库检索结果")
                for k in knowledge_results[:3]:
                    context_parts.append(f"- **{k['name']}**: {k['snippet']}")

        context = "\n".join(context_parts) if context_parts else "暂无相关记忆或知识库内容"

        system_prompt = f"""你是一个专业的直播/演讲 AI 军师助手。

{context}

请基于以上信息回答用户的问题。如果记忆和知识库中没有相关信息，请如实告知，并使用你的通用知识给出合理建议。
回答风格：简洁、专业、实用。"""

        reply = llm_router.chat_with_system(message, system_prompt)
        return {"reply": reply}

    # ── Danmaku ──────────────────────────────────────────────────────────────
    @app.get("/api/danmaku/status")
    async def danmaku_status():
        """获取弹幕捕获状态"""
        if not danmaku_processor:
            return {"running": False, "region": None, "engine": None}
        return {
            "running": danmaku_processor.running,
            "region": danmaku_processor.capture.bbox,
            "engine": "captiocr" if danmaku_processor._use_captiocr else "danmakucapture",
            "lang": getattr(danmaku_processor.capture, 'lang', 'chi_sim+eng'),
        }

    @app.post("/api/danmaku/start")
    async def danmaku_start():
        """启动弹幕捕获"""
        if not danmaku_processor:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Danmaku processor not available")
        if danmaku_processor.running:
            return {"status": "already_running"}

        try:
            await danmaku_processor.start()
            return {"status": "started"}
        except ValueError as e:
            raise __import__("fastapi").HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to start danmaku capture: {e}")
            raise __import__("fastapi").HTTPException(status_code=500, detail=str(e))

    @app.post("/api/danmaku/stop")
    async def danmaku_stop():
        """停止弹幕捕获"""
        if not danmaku_processor:
            return {"status": "not_running"}
        await danmaku_processor.stop()
        return {"status": "stopped"}

    @app.post("/api/danmaku/region")
    async def danmaku_region(request: dict):
        """设置截图区域（支持手动坐标 或 CaptiOCR 视觉框选）"""
        if not danmaku_processor:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Danmaku processor not available")

        x = request.get("x", 0)
        y = request.get("y", 0)
        width = request.get("width", 300)
        height = request.get("height", 200)

        danmaku_processor.set_region(x, y, width, height)
        return {"status": "ok", "region": {"x": x, "y": y, "width": width, "height": height}}

    @app.post("/api/danmaku/selector")
    async def danmaku_selector():
        """
        打开 CaptiOCR 视觉区域选择器。
        在全屏遮罩上拖拽鼠标框选弹幕区，松开即确认。
        仅在 CAPTIOCR_ENABLED=true 时可用。
        """
        if not danmaku_processor:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Danmaku processor not available")

        if not hasattr(danmaku_processor.capture, 'show_region_selector'):
            raise __import__("fastapi").HTTPException(status_code=400, detail="CaptiOCR 未启用。设置 CAPTIOCR_ENABLED=true 或 use_captiocr=True")

        # 在新线程中打开选择器（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, danmaku_processor.capture.show_region_selector)

        if result is None:
            return {"status": "cancelled", "region": None}

        x, y, w, h = result
        return {"status": "ok", "region": {"x": x, "y": y, "width": w, "height": h}}

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

    return app
