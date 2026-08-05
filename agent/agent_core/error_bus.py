"""轻量内存错误聚合总线

各模块统一调用此总线报告错误，供 Web Console 调试面板实时查看。
不写磁盘、无外部依赖，纯内存队列。

使用：
    from agent_core.error_bus import error_bus
    error_bus.report("ocr", "error", "截图区域无文本", {"region": "..."})
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any


class ErrorBus:
    """轻量内存错误聚合器"""

    def __init__(self, max_entries: int = 200):
        self.errors: deque[dict[str, Any]] = deque(maxlen=max_entries)

    def report(
        self,
        module: str,
        level: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        """各模块统一调用此方法报告错误。

        Args:
            module: 模块名，如 "ocr", "llm", "memory", "danmaku"
            level: 级别，如 "error", "warn", "info"
            message: 人类可读的错误描述
            detail: 附加的详细数据（可选）
        """
        entry = {
            "time": time.time(),
            "module": module,
            "level": level,
            "message": message,
            "detail": detail or {},
        }
        self.errors.append(entry)

    def list(self, limit: int = 50, level: str | None = None) -> list[dict[str, Any]]:
        """返回错误列表，按时间倒序。

        Args:
            limit: 返回条数上限
            level: 可选级别过滤（先过滤再 limit，确保返回尽可能多的匹配条目）
        """
        result = list(self.errors)
        if level:
            result = [e for e in result if e["level"] == level]
        result = result[-limit:]
        result.reverse()
        return result

    def clear(self) -> None:
        """清空所有错误"""
        self.errors.clear()

    @property
    def count(self) -> int:
        return len(self.errors)


# 全局单例
error_bus = ErrorBus()