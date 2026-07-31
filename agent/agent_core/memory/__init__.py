"""
记忆系统模块

- MemoryManager: 本地 JSON 文件记忆（Phase 1，向后兼容）
- AIMemoryManager: AI-memory 语义记忆（主推，通过 MCP 子进程调用）
"""

from .manager import MemoryManager as LocalMemoryManager
from .ai_memory import AIMemoryManager, SyncAIMemoryManager

__all__ = ["LocalMemoryManager", "AIMemoryManager", "SyncAIMemoryManager"]