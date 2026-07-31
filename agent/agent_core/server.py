"""
Textream 智能体内核 v2.0 - FastAPI 主服务

记忆系统：
- 主推：AI-memory（wang-jie-git/AI-memory，MCP 子进程，语义搜索）
- 回退：LocalMemoryManager（JSON 文件）
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
    knowledge_mgr = KnowledgeManager()
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

    # 弹幕处理器（使用 CaptiOCR 引擎 + AI-memory）
    danmaku_processor = DanmakuProcessor(
        memory_manager=ai_memory_mgr,  # None 时回退到本地记忆
        llm_provider=settings.llm_provider if settings.llm_provider != "none" else None,
        use_captiocr=True,
    )

    print(f"🤖 Textream Agent Core v2.0 starting on port {settings.agent_port}")
    print(f"   记忆: {'AI-memory (语义搜索)' if ai_memory_mgr else '本地 JSON 文件'}")

    yield

    # 关闭时
    if danmaku_processor:
        await danmaku_processor.stop()
    if ai_memory_mgr:
        await ai_memory_mgr.close()
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
                "configured": bool(__import__("os").environ.get(f"{settings.llm_provider.upper()}_API_KEY")),
            },
        }

    # ── Memory（AI-memory 优先，回退到本地 JSON） ──────────────────────────
    def _get_active_memory():
        """活跃的记忆管理器（AI-memory 优先）"""
        return ai_memory_mgr or memory_mgr

    @app.get("/api/memory/list")
    async def list_memories(limit: int = 50, offset: int = 0, user_id: str = "default", tag: str | None = None):
        mgr = _get_active_memory()
        if not mgr:
            return {"total": 0, "offset": offset, "limit": limit, "items": []}
        if isinstance(mgr, AIMemoryManager):
            items = await mgr.list(limit=limit, offset=offset, user_id=user_id, tag=tag)
        else:
            items = mgr.list(limit=limit, offset=offset, user_id=user_id, tag=tag)
        return {"total": len(items), "offset": offset, "limit": limit, "items": items}

    @app.post("/api/memory/add")
    async def add_memory(entry: dict):
        """添加记忆（支持 JSON body）"""
        mgr = _get_active_memory()
        if not mgr:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Memory not available")
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
    async def delete_memory(memory_id: str):
        mgr = _get_active_memory()
        if not mgr:
            raise __import__("fastapi").HTTPException(status_code=503, detail="Memory not available")
        if isinstance(mgr, AIMemoryManager):
            ok = await mgr.delete(memory_id)
        else:
            ok = mgr.delete(memory_id)
        if ok:
            return {"status": "deleted", "id": memory_id}
        raise __import__("fastapi").HTTPException(status_code=404, detail="Memory not found")

    @app.get("/api/memory/search")
    async def search_memory(q: str, limit: int = 20, user_id: str = "default"):
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
    async def get_persona(user_id: str = "default"):
        """获取用户画像"""
        mgr = _get_active_memory()
        if not mgr:
            return {"tags": [], "memory_count": 0, "source": "unavailable"}
        if isinstance(mgr, AIMemoryManager):
            return await mgr.get_persona(user_id)
        return mgr.get_persona(user_id)

    @app.get("/api/memory/error-book")
    async def get_error_book(user_id: str = "default"):
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
            "engine": getattr(danmaku_processor, '_capture_engine', 'unknown'),
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

    # ── Model Settings ─────────────────────────────────────────────────────
    @app.get("/api/models/settings")
    async def get_model_settings():
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
    async def update_model_settings(body: dict):
        """更新 LLM 配置（运行时生效，自动持久化）"""
        if not llm_router:
            raise __import__("fastapi").HTTPException(status_code=503, detail="LLM Router not available")

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
    async def get_model_providers():
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

    return app
