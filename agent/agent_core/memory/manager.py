"""
记忆系统 - Phase 1 实现（JSON 文件）
Phase 2 目标：替换为 One Memory 客户端
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import get_settings

settings = get_settings()

MEMORY_FILE = settings.data_dir / "memories.json"


def load_memories() -> list[dict[str, Any]]:
    """加载所有记忆"""
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_memories(memories: list[dict[str, Any]]) -> None:
    """保存记忆到文件"""
    MEMORY_FILE.write_text(
        json.dumps(memories, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


class MemoryManager:
    """记忆管理器（当前版本：JSON 文件）"""

    def __init__(self):
        self._cache: list[dict[str, Any]] = load_memories()

    def add(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        importance: int = 3,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """添加新记忆"""
        entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "content": content,
            "tags": tags or [],
            "importance": importance,
            "user_id": user_id,
        }
        self._cache.append(entry)
        save_memories(self._cache)
        return entry

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: str = "default",
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """列出记忆（支持分页和标签过滤）"""
        results = [
            m for m in self._cache
            if m.get("user_id", "default") == user_id
            and (tag is None or tag in m.get("tags", []))
        ]
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[offset:offset + limit]

    def search(self, query: str, limit: int = 20) -> list:
        """全文搜索记忆"""
        q = query.lower()
        results = [
            m for m in self._cache
            if q in m.get("title", "").lower()
            or q in m.get("content", "").lower()
        ]
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:limit]

    def get_persona(self, user_id: str = "default") -> dict:
        """
        获取用户画像（从记忆中提取标签和风格）

        Phase 2：从 One Memory 的结构化画像 API 获取
        """
        user_memories = [m for m in self._cache if m.get("user_id") == user_id]

        # 提取所有标签
        all_tags: list[str] = []
        for m in user_memories:
            all_tags.extend(m.get("tags", []))

        # 提取高重要性记忆（可能包含风格描述）
        important = [m for m in user_memories if m.get("importance", 0) >= 4]

        return {
            "tag_count": len(set(all_tags)),
            "tags": list(set(all_tags))[:20],
            "memory_count": len(user_memories),
            "important_memories": important[:5],
            "source": "json_file",  # Phase 2: "one_memory"
        }

    def get_error_book(self, user_id: str = "default") -> list:
        """获取错题本（importance >= 5 的记忆）"""
        user_memories = [m for m in self._cache if m.get("user_id") == user_id]
        errors = [m for m in user_memories if m.get("importance", 0) >= 5]
        errors.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return errors

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        before = len(self._cache)
        self._cache = [m for m in self._cache if m.get("id") != memory_id]
        if len(self._cache) < before:
            save_memories(self._cache)
            return True
        return False
