"""
弹幕实时应答生成器

根据弹幕内容生成救场话术（3 档：简单应答 / 深度解析 / 幽默化解）
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# 添加 agent 目录到 Python 路径
agent_dir = Path(__file__).parent.parent.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from one_memory_adapter import MemoryManager

logger = logging.getLogger(__name__)


class ResponseStyle:
    """话术风格"""
    SIMPLE = "simple"      # 简单应答（1-2 句话）
    DETAILED = "detailed"  # 深度解析（3-5 句话）
    HUMOR = "humor"        # 幽默化解（轻松氛围）


class DanmakuResponse:
    """弹幕应答结果"""

    def __init__(
        self,
        original: str,
        style: str,
        response: str,
        memories: list[str] | None = None,
    ):
        self.original = original
        self.style = style
        self.response = response
        self.memories = memories or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "style": self.style,
            "response": self.response,
            "memories": self.memories,
        }


class DanmakuResponder:
    """
    弹幕应答生成器

    根据弹幕意图生成对应的话术
    """

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        llm_provider: str | None = None,
    ):
        """
        初始化应答生成器

        Args:
            memory_manager: One Memory 记忆管理器（用于检索相关记忆）
            llm_provider: LLM 提供商（"siliconflow"、"openai"、"deepseek" 等）
        """
        self.memory_manager = memory_manager
        self.llm_provider = llm_provider
        logger.info("[DanmakuResponder] 初始化完成")

    def set_memory_manager(self, memory_manager: MemoryManager):
        """设置记忆管理器"""
        self.memory_manager = memory_manager

    async def generate_response(
        self,
        danmaku_text: str,
        style: str = ResponseStyle.SIMPLE,
        context: dict[str, Any] | None = None,
    ) -> DanmakuResponse:
        """
        生成弹幕应答

        Args:
            danmaku_text: 弹幕文本
            style: 话术风格（simple / detailed / humor）
            context: 上下文信息（如当前演讲主题）

        Returns:
            应答结果
        """
        logger.info(f"[DanmakuResponder] 生成应答: {danmaku_text[:50]}... (style={style})")

        # 1. 检索相关记忆（如果可用）
        memories = []
        if self.memory_manager:
            try:
                results = await self.memory_manager.query(danmaku_text, limit=3)
                memories = [m.summary for m in results]
            except Exception as e:
                logger.warning(f"[DanmakuResponder] 记忆检索失败: {e}")

        # 2. 生成话术
        if self.llm_provider:
            # 使用 LLM 生成
            response = await self._generate_with_llm(
                danmaku_text, style, memories, context
            )
        else:
            # 使用模板
            response = self._generate_with_template(danmaku_text, style)

        return DanmakuResponse(
            original=danmaku_text,
            style=style,
            response=response,
            memories=memories,
        )

    async def _generate_with_llm(
        self,
        danmaku_text: str,
        style: str,
        memories: list[str],
        context: dict[str, Any] | None,
    ) -> str:
        """使用 LLM 生成话术"""
        try:
            from ..llm.router import get_llm

            llm = get_llm(self.llm_provider)

            # 构建 prompt
            style_desc = {
                ResponseStyle.SIMPLE: "简洁有力（1-2 句话）",
                ResponseStyle.DETAILED: "深度解析（3-5 句话）",
                ResponseStyle.HUMOR: "幽默化解（轻松氛围）",
            }

            prompt = f"""你是一个专业的直播主持人和演讲者。现在有观众发了一条弹幕，请根据以下信息生成合适的回应：

**弹幕内容**：{danmaku_text}

**回应风格**：{style_desc.get(style, "简洁")}

**相关记忆**（如果有）：
{chr(10).join(f"- {m}" for m in memories) if memories else "（无相关记忆）"}

**当前上下文**：
{json.dumps(context, ensure_ascii=False) if context else "（无上下文）"}

**要求**：
1. 回应自然、亲切、专业
2. 根据风格调整长度和语气
3. 如果有相关记忆，可以适当引用
4. 不要重复弹幕原文，直接给出回应

**回应**："""

            response = await llm.chat(prompt)
            return response.strip()

        except Exception as e:
            logger.error(f"[DanmakuResponder] LLM 生成失败: {e}")
            # 降级到模板
            return self._generate_with_template(danmaku_text, style)

    def _generate_with_template(self, danmaku_text: str, style: str) -> str:
        """使用模板生成话术（降级方案）"""

        # 简单意图识别
        intent = self._classify_intent(danmaku_text)

        templates = {
            ResponseStyle.SIMPLE: {
                "question": f"谢谢你的问题！关于“{danmaku_text}”，我稍后会详细解答。",
                "praise": f"感谢你的认可！我会继续努力的。",
                "suggestion": f"感谢你的建议，这个想法很不错！",
                "default": f"感谢你的关注！",
            },
            ResponseStyle.DETAILED: {
                "question": f"关于你提到的“{danmaku_text}”，这个问题非常好。让我从几个方面来回答...",
                "praise": f"非常感谢你的认可！其实这个过程中我也学到了很多，比如...",
                "suggestion": f"这个建议非常好！我思考一下...",
                "default": f"感谢你的留言！",
            },
            ResponseStyle.HUMOR: {
                "question": f"哈哈，这个问题问得好！不过别急，等我吹完这个牛再告诉你～",
                "praise": f"你这么一说我都不好意思了😅",
                "suggestion": f"你这建议绝了，我怎么没想到！",
                "default": f"感谢你的弹幕，看到就是缘分！",
            },
        }

        style_templates = templates.get(style, templates[ResponseStyle.SIMPLE])
        return style_templates.get(intent, style_templates["default"])

    def _classify_intent(self, text: str) -> str:
        """
        简单意图分类

        Args:
            text: 弹幕文本

        Returns:
            意图类型（question / praise / suggestion / default）
        """
        # 问题关键词
        question_keywords = ["?", "？", "怎么", "如何", "什么", "为什么", "吗", "呢", "？"]
        if any(kw in text for kw in question_keywords):
            return "question"

        # 夸奖关键词
        praise_keywords = ["好", "棒", "厉害", "赞", "牛", "优秀", "强", "666"]
        if any(kw in text for kw in praise_keywords):
            return "praise"

        # 建议关键词
        suggestion_keywords = ["建议", "可以", "应该", "不如", "试试", "如果"]
        if any(kw in text for kw in suggestion_keywords):
            return "suggestion"

        return "default"
