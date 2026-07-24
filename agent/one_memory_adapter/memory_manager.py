"""
记忆管理器 - 高 Level API

封装 One Memory 的常用记忆操作
"""

import logging
from datetime import datetime
from typing import Any

from .client import OneMemoryClient
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class Memory:
    """记忆对象"""

    def __init__(
        self,
        id: str,
        title: str,
        summary: str,
        user_id: str,
        importance: int = 3,
        tags: list[str] | None = None,
        symbols: list[str] | None = None,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = id
        self.title = title
        self.summary = summary
        self.user_id = user_id
        self.importance = importance
        self.tags = tags or []
        self.symbols = symbols or []
        self.created_at = created_at or datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "user_id": self.user_id,
            "importance": self.importance,
            "tags": self.tags,
            "symbols": self.symbols,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Memory":
        """从字典创建"""
        return cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            user_id=data["user_id"],
            importance=data.get("importance", 3),
            tags=data.get("tags", []),
            symbols=data.get("symbols", []),
            created_at=data.get("created_at"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self):
        return f"<Memory id={self.id} title={self.title} importance={self.importance}>"


class MemoryManager:
    """
    记忆管理器

    提供简化的记忆读写接口
    """

    def __init__(self, mcp_url: str = "http://localhost:3000", user_id: str = "default"):
        """
        初始化记忆管理器

        Args:
            mcp_url: One Memory MCP 服务地址
            user_id: 用户 ID（多租户隔离）
        """
        self.client = OneMemoryClient(mcp_url=mcp_url)
        self.user_id = user_id

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.client.close()

    async def write(
        self,
        title: str,
        summary: str,
        tags: list[str] | None = None,
        importance: int = 5,
        symbols: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        body: str | None = None,
        node_type: str = "memory_entry",
        ttl_days: int | None = None,
    ) -> str:
        """
        写入记忆

        Args:
            title: 记忆标题
            summary: 记忆摘要
            tags: 标签列表
            importance: 重要性（1-5）
            symbols: 关联代码符号（可选）
            metadata: 元数据（可选）

        Returns:
            记忆 ID
        """
        if importance < 1 or importance > 10:
            raise ValidationError("重要性必须在 1-10 之间")

        arguments = {
            "title": title,
            "summary": summary,
            "importance": importance,
            "tags": tags or [],
            "type": node_type,
        }

        if body:
            arguments["body"] = body
        if ttl_days:
            arguments["ttl_days"] = ttl_days
        if metadata:
            arguments["metadata"] = metadata

        result = await self.client.call_tool("memory_write", arguments)

        # 解析结果
        if isinstance(result, dict) and "id" in result:
            return result["id"]
        elif isinstance(result, dict) and "title" in result:
            # 直接返回节点对象
            return result.get("id", "")
        else:
            logger.warning(f"[MemoryManager] write 返回意外格式: {result}")
            return ""

    async def write_with_symbols(
        self,
        title: str,
        summary: str,
        symbols: list[str],
        **kwargs,
    ) -> str:
        """
        写入记忆并关联代码符号（便捷方法）

        Args:
            title: 记忆标题
            summary: 记忆摘要
            symbols: 代码符号列表（如 ["DirectorServer.swift:215"]）
            **kwargs: 其他参数

        Returns:
            记忆 ID
        """
        return await self.write(
            title=title,
            summary=summary,
            symbols=symbols,
            **kwargs,
        )

    async def query(
        self,
        query: str,
        limit: int = 5,
        threshold: float | None = None,
        min_importance: int | None = None,
    ) -> list[Memory]:
        """
        语义搜索记忆

        Args:
            query: 搜索查询
            limit: 返回结果数
            threshold: 相似度阈值（0-1）（One Memory 不支持，仅兼容接口）
            min_importance: 最低重要性过滤（1-10）

        Returns:
            记忆列表（按相关度排序）
        """
        arguments = {
            "query": query,
            "limit": limit,
        }

        if min_importance is not None:
            arguments["min_importance"] = min_importance

        result = await self.client.call_tool("memory_query", arguments)

        # 解析结果
        memories_data = []
        if isinstance(result, dict):
            if "memories" in result:
                memories_data = result["memories"]
            elif "text" in result:
                # 纯文本格式（One Memory 默认返回格式）
                text = result["text"]
                if text and text != "无匹配项目记忆":
                    # 简单解析文本格式（生产环境建议使用结构化格式）
                    logger.warning("[MemoryManager] 收到非结构化结果，建议升级到 JSON 格式")

        return [Memory.from_dict(m) for m in memories_data]

    async def delete(self, memory_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            是否删除成功
        """
        result = await self.client.call_tool("memory_delete", {"id": memory_id})
        return result.get("status") == "deleted"

    async def stats(self) -> dict[str, Any]:
        """
        获取记忆统计信息

        Returns:
            统计信息（总记忆数、今日新增、重要性分布等）
        """
        # TODO: One Memory 是否提供 stats 接口？
        # 临时实现：从查询结果统计
        all_memories = await self.query("", limit=1000, threshold=0.0)

        today = datetime.now().strftime("%Y-%m-%d")
        today_count = sum(1 for m in all_memories if m.created_at.startswith(today))

        importance_dist = {}
        for m in all_memories:
            importance_dist[m.importance] = importance_dist.get(m.importance, 0) + 1

        return {
            "total": len(all_memories),
            "today": today_count,
            "by_importance": importance_dist,
        }
