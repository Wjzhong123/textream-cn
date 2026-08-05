"""
AI-memory 集成层 — 通过 MCP 子进程调用 wang-jie-git/AI-memory 记忆系统

替代旧的 JSON 文件记忆和 One OS 适配器。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import sys
import uuid
from datetime import datetime
from typing import Any

from .mcp_client import MCPClient, MCPTimeoutError, MCPError

logger = logging.getLogger(__name__)

# 默认路径
_TEXTREAM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent  # agent/
_DEFAULT_MCP_ROOT = _TEXTREAM_ROOT / "third_party" / "AI-memory"
_DEFAULT_CODEGRAPH_DIR = _TEXTREAM_ROOT / "third_party" / ".codegraph"


class AIMemoryManager:
    """
    AI-memory 记忆管理器（异步）

    通过 MCP 子进程调用 memory-mcp 服务器，提供语义搜索和持久化记忆。
    支持 async with 上下文管理器自动管理生命周期。

    用法:
        async with AIMemoryManager() as mem:
            await mem.add("标题", "内容")
            results = await mem.search("查询")
    """

    def __init__(
        self,
        mcp_root: str | pathlib.Path | None = None,
        codegraph_dir: str | pathlib.Path | None = None,
        embedder: str = "simple",
        user_id: str = "default",
    ):
        self.mcp_root = pathlib.Path(mcp_root or _DEFAULT_MCP_ROOT)
        self.codegraph_dir = pathlib.Path(codegraph_dir or _DEFAULT_CODEGRAPH_DIR)
        self.embedder = embedder
        self.user_id = user_id
        self._client: MCPClient | None = None
        self._initialized = False

    async def _ensure_client(self) -> MCPClient:
        """确保 MCP 客户端已初始化"""
        if self._client is None:
            self._client = MCPClient(
                codegraph_dir=str(self.codegraph_dir),
                mcp_root=str(self.mcp_root),
                embedder=self.embedder,
            )
            await self._client._start_process()
            await self._client.initialize()
            self._initialized = True
            logger.info("AIMemoryManager: MCP 客户端已初始化")
        return self._client

    # ── 核心 API ───────────────────────────────────────────────────────────

    async def add(
        self,
        title: str,
        content: str = "",
        tags: list[str] | None = None,
        importance: int = 3,
        user_id: str | None = None,
        body: str = "",
    ) -> dict[str, Any]:
        """添加一条记忆"""
        client = await self._ensure_client()
        result = await client.write(
            title=title,
            summary=content[:500],
            body=body or content,
            importance=importance,
            tags=tags or [],
            user_id=user_id or self.user_id,
        )
        return {"id": result.get("id", "?"), "title": title, "status": "stored"}

    async def search(
        self,
        query: str,
        limit: int = 20,
        min_importance: int | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """语义搜索记忆"""
        try:
            client = await self._ensure_client()
            results = await client.query(
                query_text=query,
                limit=limit,
                min_importance=min_importance,
                user_id=user_id or self.user_id,
            )
            # 统一字段名
            normalized = []
            for r in results:
                normalized.append({
                    "id": r.get("id", str(uuid.uuid4())[:8]),
                    "title": r.get("title", ""),
                    "content": r.get("summary", "") or r.get("body", ""),
                    "summary": r.get("summary", ""),
                    "body": r.get("body", ""),
                    "tags": r.get("tags", []),
                    "importance": r.get("importance", 3),
                    "timestamp": r.get("created_at", r.get("timestamp", "")),
                    "user_id": r.get("user_id", user_id or self.user_id),
                    "score": r.get("score", r.get("similarity", 0.0)),
                })
            return normalized
        except (MCPError, MCPTimeoutError, ConnectionError) as e:
            logger.warning(f"AIMemoryManager.search 失败: {e}")
            return []

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出记忆"""
        try:
            results = await self.search(
                query="",
                limit=limit + offset,
                user_id=user_id or self.user_id,
            )
            if tag:
                results = [r for r in results if tag in r.get("tags", [])]
            return results[offset:offset + limit]
        except Exception as e:
            logger.warning(f"AIMemoryManager.list 失败: {e}")
            return []

    async def query(
        self,
        query_text: str,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """语义查询（与 search 同义，兼容 responder 接口）"""
        return await self.search(query=query_text, limit=limit, user_id=user_id)

    async def get_persona(self, user_id: str | None = None) -> dict:
        """获取用户画像"""
        uid = user_id or self.user_id
        results = await self.search(query="", limit=100, user_id=uid)
        all_tags: list[str] = []
        important = []
        for r in results:
            all_tags.extend(r.get("tags", []))
            if r.get("importance", 0) >= 4:
                important.append(r)

        return {
            "tag_count": len(set(all_tags)),
            "tags": list(set(all_tags))[:20],
            "memory_count": len(results),
            "important_memories": important[:5],
            "source": "ai_memory",
        }

    async def get_error_book(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """获取错题本（importance >= 5 的记忆 + tag='lesson' 的记忆）"""
        results = await self.search(
            query="",
            limit=100,
            min_importance=5,
            user_id=user_id or self.user_id,
        )
        # 也搜索 lesson 标签的记忆
        lesson_results = await self.search(
            query="lesson",
            limit=20,
            user_id=user_id or self.user_id,
        )
        combined = results + [r for r in lesson_results if r not in results]
        combined.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return combined

    async def record_lesson(
        self,
        title: str,
        content: str,
        importance: int = 5,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        记录一条教训到错题本。

        Args:
            title: 教训标题
            content: 详细描述 + 根因 + 修复方案
            importance: 重要性（5=默认，6=重要，7=致命）
            user_id: 用户 ID

        Returns:
            创建的教训条目
        """
        result = await self.add(
            title=title,
            content=content,
            tags=["lesson", "error_book"],
            importance=importance,
            user_id=user_id or self.user_id,
        )
        return result

    async def delete(self, memory_id: str) -> bool:
        """删除记忆（通过 dreaming 整理机制，暂不支持直接删除）"""
        logger.warning(f"AIMemoryManager.delete: AI-memory 暂不支持直接删除 (id={memory_id})")
        return False

    # ── 生命周期管理 ───────────────────────────────────────────────────────

    async def close(self):
        """关闭 MCP 连接"""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("AIMemoryManager: 已关闭")

    async def __aenter__(self) -> "AIMemoryManager":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @property
    def is_available(self) -> bool:
        """AI-memory 是否可用（检查 MCP 根目录是否存在）"""
        return self.mcp_root.exists() and (self.mcp_root / "packages" / "memory-mcp").exists()


# ── 兼容同步接口（用于不支持 async 的旧代码路径） ──

class SyncAIMemoryManager:
    """同步版本的 AIMemoryManager（内部用 asyncio.run）"""

    def __init__(self, **kwargs):
        self._async = AIMemoryManager(**kwargs)
        self._loop: asyncio.AbstractEventLoop | None = None

    def _run(self, coro):
        """在事件循环中执行协程"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 已经在事件循环中，创建新任务
                return asyncio.run_coroutine_threadsafe(coro, loop).result()
        except RuntimeError:
            pass
        return asyncio.run(coro)

    def add(self, **kwargs):
        return self._run(self._async.add(**kwargs))

    def search(self, **kwargs):
        return self._run(self._async.search(**kwargs))

    def list(self, **kwargs):
        return self._run(self._async.list(**kwargs))

    def query(self, **kwargs):
        return self._run(self._async.query(**kwargs))

    def get_persona(self, **kwargs):
        return self._run(self._async.get_persona(**kwargs))

    def get_error_book(self, **kwargs):
        return self._run(self._async.get_error_book(**kwargs))

    def record_lesson(self, **kwargs):
        return self._run(self._async.record_lesson(**kwargs))

    def delete(self, **kwargs):
        return self._run(self._async.delete(**kwargs))

    def close(self):
        return self._run(self._async.close())