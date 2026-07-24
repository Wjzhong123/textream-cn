"""
知识库管理器 - Phase 2 实现（RAG + 向量检索）

基于 One Memory 的向量能力实现语义检索
"""

from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

# 添加 agent 目录到 Python 路径
agent_dir = Path(__file__).parent.parent.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from ..config import get_settings
from one_memory_adapter import MemoryManager

if TYPE_CHECKING:
    pass

settings = get_settings()
logger = logging.getLogger(__name__)


class KnowledgeManager:
    """
    知识库管理器（RAG 增强）

    使用 One Memory 的向量检索能力实现语义搜索
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """
        初始化知识库管理器

        Args:
            memory_manager: One Memory 记忆管理器（可选）
        """
        self.memory_manager = memory_manager
        self._local_cache: dict[str, dict[str, Any]] = {}

    def set_memory_manager(self, memory_manager: MemoryManager):
        """设置 One Memory 记忆管理器"""
        self.memory_manager = memory_manager

    async def list(self) -> list[dict[str, Any]]:
        """
        列出所有知识库文件

        支持两种模式：
        1. One Memory 模式：从记忆系统检索
        2. 本地文件模式：从 data/knowledge/ 读取
        """
        if self.memory_manager:
            # One Memory 模式：查询所有知识库记忆
            try:
                memories = await self.memory_manager.query("知识库", limit=100)
                return [
                    {
                        "id": m.id,
                        "name": m.title,
                        "summary": m.summary,
                        "tags": m.tags,
                        "importance": m.importance,
                    }
                    for m in memories
                ]
            except Exception as e:
                logger.warning(f"[KnowledgeManager] One Memory 查询失败: {e}")

        # 本地文件模式（降级）
        return self._list_local_files()

    def _list_local_files(self) -> list[dict[str, Any]]:
        """本地文件模式：列出 knowledge/ 目录下的文件"""
        KNOWLEDGE_DIR = settings.data_dir / "knowledge"
        results = []
        if not KNOWLEDGE_DIR.exists():
            return results

        for f in sorted(KNOWLEDGE_DIR.glob("*.txt")):
            try:
                content = f.read_text(encoding="utf-8").strip()
                if content:
                    doc_id = hashlib.md5(f.stem.encode()).hexdigest()[:8]
                    results.append({
                        "id": doc_id,
                        "name": f.stem,
                        "content": content,
                        "path": str(f),
                        "size": len(content),
                    })
            except Exception:
                pass
        return results

    async def search(
        self,
        query: str,
        limit: int = 5,
        min_importance: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        语义搜索知识库

        Args:
            query: 搜索查询
            limit: 返回结果数
            min_importance: 最低重要性过滤（仅 One Memory 模式）

        Returns:
            搜索结果列表
        """
        if self.memory_manager:
            # One Memory 模式：语义检索
            try:
                memories = await self.memory_manager.query(
                    query=query,
                    limit=limit,
                    min_importance=min_importance,
                )
                return [
                    {
                        "id": m.id,
                        "name": m.title,
                        "summary": m.summary,
                        "content": m.metadata.get("body", ""),
                        "score": 0.0,  # One Memory 暂未返回分数
                        "tags": m.tags,
                    }
                    for m in memories
                ]
            except Exception as e:
                logger.warning(f"[KnowledgeManager] One Memory 搜索失败: {e}")

        # 本地文件模式（降级）：全文搜索
        return self._search_local(query, limit)

    def _search_local(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """本地文件模式：全文搜索"""
        q = query.lower()
        results = []
        for doc in self._list_local_files():
            content = doc["content"].lower()
            if q in content:
                idx = content.find(q)
                snippet_size = 200
                start = max(0, idx - snippet_size // 2)
                end = min(len(doc["content"]), idx + len(query) + snippet_size // 2)
                snippet = doc["content"][start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(doc["content"]):
                    snippet = snippet + "..."
                results.append({
                    "id": doc["id"],
                    "name": doc["name"],
                    "snippet": snippet,
                    "score": 0.0,
                })
        return results[:limit]

    async def add_file(
        self,
        name: str,
        content: str,
        tags: list[str] | None = None,
        importance: int = 3,
        auto_vectorize: bool = True,
    ) -> dict[str, Any]:
        """
        添加知识库文件

        Args:
            name: 文件名
            content: 文件内容
            tags: 标签
            importance: 重要性（1-10）
            auto_vectorize: 是否自动向量化（One Memory 模式）

        Returns:
            添加结果
        """
        if self.memory_manager and auto_vectorize:
            # One Memory 模式：写入记忆（自动向量化）
            try:
                memory_id = await self.memory_manager.write(
                    title=f"知识库：{name}",
                    summary=content[:200] + ("..." if len(content) > 200 else ""),
                    body=content,
                    tags=tags or ["knowledge_base"],
                    importance=importance,
                    node_type="memory_entry",
                )
                return {
                    "id": memory_id,
                    "name": name,
                    "source": "one_memory",
                }
            except Exception as e:
                logger.warning(f"[KnowledgeManager] One Memory 写入失败: {e}")

        # 本地文件模式（降级）
        return self._add_local_file(name, content)

    def _add_local_file(self, name: str, content: str) -> dict[str, Any]:
        """本地文件模式：添加文件"""
        KNOWLEDGE_DIR = settings.data_dir / "knowledge"
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = KNOWLEDGE_DIR / f"{name}.txt"
        file_path.write_text(content, encoding="utf-8")
        doc_id = hashlib.md5(name.encode()).hexdigest()[:8]
        return {
            "id": doc_id,
            "name": name,
            "path": str(file_path),
            "source": "local_file",
        }

    async def delete_file(self, name: str) -> bool:
        """删除知识库文件"""
        if self.memory_manager:
            # One Memory 模式：查询并删除
            try:
                memories = await self.memory_manager.query(f"知识库：{name}", limit=1)
                if memories:
                    await self.memory_manager.delete(memories[0].id)
                    return True
            except Exception as e:
                logger.warning(f"[KnowledgeManager] One Memory 删除失败: {e}")

        # 本地文件模式（降级）
        KNOWLEDGE_DIR = settings.data_dir / "knowledge"
        file_path = KNOWLEDGE_DIR / f"{name}.txt"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
