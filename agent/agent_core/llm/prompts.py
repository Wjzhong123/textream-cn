"""
提词器专用 Prompt 模板

集中管理所有话术生成相关的 Prompt，方便调优和场景切换。
"""

# ── 风格描述 ──────────────────────────────────────────────────────────

STYLE_DESCRIPTIONS = {
    "simple": "简洁有力（1-2 句话）",
    "detailed": "深度解析（3-5 句话）",
    "humor": "幽默化解（轻松氛围）",
}

# ── 话术生成 System Prompt ────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """你是一个专业的直播主持人和演讲者。现在有观众发了一条弹幕，请根据以下信息生成合适的回应：

**弹幕内容**：{danmaku_text}

**回应风格**：{style_desc}

**相关记忆**（如果有）：
{memories_section}

**相关知识库**（如果有）：
{knowledge_section}

**当前上下文**：
{context_section}

**要求**：
1. 回应自然、亲切、专业
2. 根据风格调整长度和语气
3. 如果有相关记忆或知识库内容，可以适当引用
4. 不要重复弹幕原文，直接给出回应"""

# ── 话术生成 User Message ─────────────────────────────────────────────

USER_MESSAGE_TEMPLATE = """弹幕内容：{danmaku_text}

相关记忆：
{memories_section}

相关知识库：
{knowledge_section}

当前上下文：
{context_section}

请生成回应："""


# ── 构建函数 ──────────────────────────────────────────────────────────

def build_system_prompt(
    danmaku_text: str,
    style: str,
    memories: list[str] | None = None,
    knowledge: list[str] | None = None,
    context: dict | None = None,
) -> str:
    """构建系统提示词"""
    memories = memories or []
    knowledge = knowledge or []
    context = context or {}

    memories_section = "\n".join(f"- {m}" for m in memories) if memories else "（无相关记忆）"
    knowledge_section = "\n".join(f"- {k}" for k in knowledge) if knowledge else "（无相关知识）"
    context_section = str(context) if context else "（无上下文）"

    import json
    if context:
        context_section = json.dumps(context, ensure_ascii=False)
    else:
        context_section = "（无上下文）"

    return SYSTEM_PROMPT_TEMPLATE.format(
        danmaku_text=danmaku_text,
        style_desc=STYLE_DESCRIPTIONS.get(style, "简洁"),
        memories_section=memories_section,
        knowledge_section=knowledge_section,
        context_section=context_section,
    )


def build_user_message(
    danmaku_text: str,
    memories: list[str] | None = None,
    knowledge: list[str] | None = None,
    context: dict | None = None,
) -> str:
    """构建用户消息"""
    memories = memories or []
    knowledge = knowledge or []
    context = context or {}

    memories_section = "\n".join(f"- {m}" for m in memories) if memories else "（无相关记忆）"
    knowledge_section = "\n".join(f"- {k}" for k in knowledge) if knowledge else "（无相关知识）"

    import json
    context_section = json.dumps(context, ensure_ascii=False) if context else "（无上下文）"

    return USER_MESSAGE_TEMPLATE.format(
        danmaku_text=danmaku_text,
        memories_section=memories_section,
        knowledge_section=knowledge_section,
        context_section=context_section,
    )