"""
知识库管理器（RAG 增强）

策略：
  全文 → 本地文件（data/knowledge/）
  摘要 → AI-memory（语义搜索，≤2000 字符）
  search() → AI-memory 语义搜索 → 本地文件映射全文
  list()  → 本地文件 + AI-memory 元数据合并
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class KnowledgeManager:
    """
    知识库管理器（RAG 增强）

    本地文件存储全文，AI-memory 存储摘要用于语义搜索。
    """

    def __init__(self, memory_manager: Any | None = None):
        self.memory_manager = memory_manager
        self._local_cache: dict[str, dict[str, Any]] = {}

    def set_memory_manager(self, memory_manager: Any):
        self.memory_manager = memory_manager

    # ── 本地文件操作 ──────────────────────────────────────────────────────

    @property
    def _knowledge_dir(self) -> Path:
        d = settings.data_dir / "knowledge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _list_local_files(self) -> list[dict[str, Any]]:
        """列出本地 knowledge/ 目录下的所有文件"""
        results = []
        if not self._knowledge_dir.exists():
            return results
        for f in sorted(self._knowledge_dir.glob("*.txt")):
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

    def _read_local(self, name: str) -> str | None:
        """按文件名读取本地文件内容"""
        fp = self._knowledge_dir / f"{name}.txt"
        if fp.exists():
            return fp.read_text(encoding="utf-8", errors="replace")
        return None

    def _write_local(self, name: str, content: str):
        """写入本地文件"""
        safe_name = Path(name).stem
        fp = self._knowledge_dir / f"{safe_name}.txt"
        fp.write_text(content, encoding="utf-8")

    def _delete_local(self, name: str) -> bool:
        """删除本地文件"""
        # 尝试精确匹配
        for fp in self._knowledge_dir.glob(f"{name}.txt"):
            fp.unlink()
            return True
        # 尝试通配（name 可能包含路径信息）
        for fp in self._knowledge_dir.glob("*"):
            if name in fp.stem:
                fp.unlink()
                return True
        return False

    # ── AI-memory 操作 ───────────────────────────────────────────────────

    async def _index_summary(self, name: str, content: str):
        """将摘要写入 AI-memory（≤2000 字符，避免 chunk 超限）"""
        if not self.memory_manager:
            return
        summary = content[:2000]
        # 先查重：已有同名摘要则跳过
        existing = await self.memory_manager.query(
            f"知识库：{name}", limit=1,
        )
        if existing:
            return
        await self.memory_manager.add(
            title=f"知识库：{name}",
            content=summary,
            tags=["knowledge_base"],
            importance=3,
        )

    async def _sync_local_to_ai(self):
        """将本地文件同步到 AI-memory（幂等，重复调用安全）"""
        if not self.memory_manager:
            return
        docs = self._list_local_files()
        for doc in docs:
            try:
                await self._index_summary(doc["name"], doc["content"])
            except Exception as e:
                logger.warning(f"[KnowledgeManager] 同步 '{doc['name']}' 失败: {e}")

    # ── 公开 API ─────────────────────────────────────────────────────────

    async def list(self) -> list[dict[str, Any]]:
        """
        列出所有知识库文件。

        返回：本地文件列表（AI-memory 可用时包含 score 信息）
        """
        docs = self._list_local_files()
        if not self.memory_manager:
            return docs

        # 用 AI-memory 查询辅助排序（非关键，失败不影响）
        try:
            memories = await self.memory_manager.query("知识库", limit=100)
            name_to_score = {}
            for m in memories:
                title = m.get("title", "") if isinstance(m, dict) else getattr(m, "title", "")
                for doc in docs:
                    if doc["name"] in title:
                        score = m.get("score", 0.0) if isinstance(m, dict) else 0.0
                        name_to_score[doc["name"]] = max(score, name_to_score.get(doc["name"], 0.0))
            for doc in docs:
                doc["score"] = name_to_score.get(doc["name"], 0.0)
        except Exception:
            pass
        return docs

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        语义搜索知识库。

        优先使用 AI-memory 语义搜索，返回结果包含全文 content。
        降级到本地子串匹配。
        """
        if self.memory_manager:
            try:
                memories = await self.memory_manager.query(
                    query_text=query,
                    limit=limit,
                )
                results = []
                for m in memories:
                    title = m.get("title", "") if isinstance(m, dict) else getattr(m, "title", "")
                    # 从标题提取文件名：知识库：xxx → xxx
                    name = title.replace("知识库：", "", 1) if "知识库：" in title else title
                    # 去掉 " (第N部分/M部分)" 后缀
                    import re
                    name = re.sub(r"\s*\(第\d+部分/\d+\)", "", name)
                    full_content = self._read_local(name)
                    snippet = full_content[:500] if full_content else (
                        m.get("summary", "") if isinstance(m, dict) else getattr(m, "summary", "")
                    )
                    results.append({
                        "id": m.get("id", "") if isinstance(m, dict) else getattr(m, "id", ""),
                        "name": name,
                        "snippet": snippet,
                        "content": full_content or "",
                        "score": m.get("score", 0.0) if isinstance(m, dict) else 0.0,
                    })
                return results[:limit]
            except Exception as e:
                logger.warning(f"[KnowledgeManager] 语义搜索失败，降级到子串匹配: {e}")

        return self._search_local(query, limit)

    def _search_local(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """本地子串匹配（降级方案）"""
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
                    "content": doc["content"],
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
        添加知识库文件。

        策略：
          1. 全文写入本地文件（单一日志源）
          2. AI-memory 可用时写入摘要索引（≤2000 字符）

        Args:
            name: 文件名
            content: 文件内容
            tags: 标签（仅 AI-memory 模式）
            importance: 重要性（1-10，仅 AI-memory 模式）
            auto_vectorize: 是否自动向量化（AI-memory 模式）

        Returns:
            {"id": str, "name": str, "source": str, "chunks": int}
        """
        # 1. 始终写入本地文件
        self._write_local(name, content)
        doc_id = hashlib.md5(name.encode()).hexdigest()[:8]

        # 2. AI-memory 摘要索引
        source = "local_file"
        chunks = 1
        if self.memory_manager and auto_vectorize:
            try:
                await self._index_summary(name, content)
                source = "ai_memory_indexed"
            except Exception as e:
                logger.warning(f"[KnowledgeManager] AI-memory 索引失败: {e}")

        return {
            "id": doc_id,
            "name": name,
            "source": source,
            "chunks": chunks,
        }

    async def delete_file(self, name: str) -> bool:
        """删除知识库文件"""
        # 删除本地文件
        deleted = self._delete_local(name)
        # 尝试删除 AI-memory 中的索引
        if self.memory_manager and deleted:
            try:
                memories = await self.memory_manager.query(f"知识库：{name}", limit=1)
                if memories:
                    mem_id = memories[0].get("id", "") if isinstance(memories[0], dict) else getattr(memories[0], "id", "")
                    if mem_id:
                        await self.memory_manager.delete(mem_id)
            except Exception:
                pass
        return deleted