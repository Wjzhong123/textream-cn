"""
内存桥接器 - 三层记忆管理

基于 One Memory 实现 Textream 的三层记忆架构：
- Working（工作记忆）：当前会话临时存储
- Short-term（短期记忆）：会话级（7 天）
- Long-term（长期记忆）：永久存储
"""

from datetime import datetime, timedelta
from typing import Any

from .client import OneMemoryClient
from .exceptions import ValidationError
from .memory_manager import Memory, MemoryManager


class Tier:
    """记忆层级"""
    WORKING = "working"       # 工作记忆
    SHORT_TERM = "short_term" # 短期记忆
    LONG_TERM = "long_term"   # 长期记忆


class MemoryBridge:
    """
    内存桥接器

    提供三层记忆管理：
    - 自动将记忆分配到合适的层级
    - 分级检索（优先返回高层级记忆）
    - 记忆梦境整理（熵减）
    """

    def __init__(
        self,
        project_path: str,
        user_id: str = "default",
        mcp_url: str = "http://localhost:3000",
    ):
        self.project_path = project_path
        self.user_id = user_id
        self.manager = MemoryManager(mcp_url=mcp_url, user_id=user_id)
        self._tier_metadata = {}  # 记忆 ID → 层级

    async def __aenter__(self):
        await self.manager.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.manager.client.close()

    async def store_working(self, summary: str, **kwargs) -> str:
        """
        存储工作记忆（临时）

        Args:
            summary: 记忆摘要
            **kwargs: 其他参数

        Returns:
            记忆 ID
        """
        memory_id = await self.manager.write(
            title=f"[Working] {summary[:50]}",
            summary=summary,
            importance=2,  # 工作记忆默认重要性较低
            **kwargs,
        )
        self._tier_metadata[memory_id] = Tier.WORKING
        return memory_id

    async def store_short_term(self, summary: str, ttl_days: int = 7, **kwargs) -> str:
        """
        存储短期记忆（会话级）

        Args:
            summary: 记忆摘要
            ttl_days: 过期天数（默认 7 天）
            **kwargs: 其他参数

        Returns:
            记忆 ID
        """
        memory_id = await self.manager.write(
            title=f"[Short-term] {summary[:50]}",
            summary=summary,
            importance=3,
            metadata={"ttl_days": ttl_days, "expires_at": (datetime.now() + timedelta(days=ttl_days)).isoformat()},
            **kwargs,
        )
        self._tier_metadata[memory_id] = Tier.SHORT_TERM
        return memory_id

    async def store_long_term(self, summary: str, **kwargs) -> str:
        """
        存储长期记忆（永久）

        Args:
            summary: 记忆摘要
            **kwargs: 其他参数

        Returns:
            记忆 ID
        """
        memory_id = await self.manager.write(
            title=f"[Long-term] {summary[:50]}",
            summary=summary,
            importance=4,  # 长期记忆默认重要性较高
            **kwargs,
        )
        self._tier_metadata[memory_id] = Tier.LONG_TERM
        return memory_id

    async def retrieve(
        self,
        query: str,
        tiers: list[str] | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """
        分级检索记忆

        Args:
            query: 搜索查询
            tiers: 要检索的层级（默认全部）
            limit: 返回结果数

        Returns:
            记忆列表（按层级优先级排序）
        """
        # 查询所有相关记忆
        all_memories = await self.manager.query(query, limit=limit * 2)

        # 过滤层级
        if tiers:
            all_memories = [m for m in all_memories if self._tier_metadata.get(m.id) in tiers]

        # 按层级排序（Long-term > Short-term > Working）
        tier_order = {Tier.LONG_TERM: 0, Tier.SHORT_TERM: 1, Tier.WORKING: 2}

        def sort_key(memory: Memory) -> tuple[int, int]:
            tier = self._tier_metadata.get(memory.id, Tier.WORKING)
            return (tier_order.get(tier, 99), -memory.importance)

        all_memories.sort(key=sort_key)
        return all_memories[:limit]

    async def dream(self) -> dict[str, Any]:
        """
        记忆梦境整理（熵减）

        自动执行：
        1. 合并冗余记忆
        2. 主题聚类
        3. 低价值记忆修剪
        4. 计算健康评分

        Returns:
            梦境报告
        """
        # TODO: 调用 One Memory 的 dream 工具
        # result = await self.client.call_tool("global_dream", {...})

        # 临时实现：统计记忆健康度
        stats = await self.manager.stats()

        health_score = 85  # 占位值
        if stats["total"] > 1000:
            health_score -= 10
        if stats["by_importance"].get(1, 0) > stats["total"] * 0.3:
            health_score -= 15

        return {
            "health_score": health_score,
            "total_memories": stats["total"],
            "suggestions": [
                "建议清理 importance=1 的低价值记忆",
                "定期整理短期记忆（7 天过期）",
            ],
        }
