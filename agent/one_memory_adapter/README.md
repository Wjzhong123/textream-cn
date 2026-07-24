# One Memory Python 适配器

为 Textream 智能提词器提供 One Memory 能力。

## 架构

```
Textream 智能体（Python）
    ↓
One Memory Python 适配器（本库）
    ↓
MCP 协议
    ↓
One Memory（TypeScript/Node.js）
    ↓
SQLite + 向量索引
```

## 安装

```bash
pip install mcp
```

## 快速开始

```python
from one_memory_adapter import MemoryManager

# 异步使用
async with MemoryManager(user_id="user_123") as manager:
    # 写入记忆
    await manager.write(
        title="用户偏好",
        summary="喜欢幽默开场",
        tags=["演讲", "风格"],
        importance=5,
    )

    # 查询记忆
    results = await manager.query("演讲技巧", limit=10)
    for memory in results:
        print(memory.summary)
```

## 模块

- `MemoryManager` - 记忆管理器（读写查删）
- `MemoryBridge` - 内存桥接器（三层记忆：Working/Short-term/Long-term）
- `VectorStore` - 向量存储（知识库向量化）

## 状态

⚠️ **Phase 1（MCP 客户端）开发中** — 当前为 Mock 实现
