"""
Textream 智能体内核 - Phase 1 MVP
替换简陋的 agent_server.py，为后续升级打基础

架构：
- memory/      → 记忆系统（当前：JSON 文件；未来：One Memory）
- knowledge/   → 知识库（当前：全文搜索；未来：向量化 + RAG）
- llm/         → LLM 路由层（多提供商支持）
- danmaku/     → 弹幕处理（Phase 2 实现）
"""

__version__ = "2.0.0-alpha"
__author__ = "Textream Agent Team"
