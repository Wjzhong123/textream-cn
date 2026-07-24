"""
One Memory Python 适配器 - 核心模块

通过 MCP（Model Context Protocol）调用 One Memory 的能力
"""

__version__ = "1.0.0-alpha"
__author__ = "Textream Agent Team"

from .client import OneMemoryClient
from .memory_manager import MemoryManager, Memory
from .memory_bridge import MemoryBridge

__all__ = [
    "OneMemoryClient",
    "MemoryManager",
    "Memory",
    "MemoryBridge",
]
