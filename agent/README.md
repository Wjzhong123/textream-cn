# Textream Agent Core v2.0

新一代智能提词器 + AI 军师系统。

## 架构

```
agent_core/
├── config.py          # 配置管理
├── server.py          # FastAPI 主服务
├── memory/            # 记忆系统
│   └── manager.py     # JSON 文件（Phase 1）→ One Memory（Phase 2）
├── knowledge/         # 知识库
│   └── manager.py     # 全文搜索（Phase 1）→ 向量化 RAG（Phase 2）
├── llm/               # LLM 路由
│   ├── router.py      # 多提供商支持
│   └── prompts.py     # 提词器专用 Prompt
└── danmaku/           # 弹幕处理（Phase 2）
    ├── __init__.py
    └── scraper.py     # 屏幕 OCR + 意图识别
```

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn openai pydantic
```

### 2. 配置 LLM

```bash
# 推荐：SiliconFlow（国内访问快）
export LLM_PROVIDER=siliconflow
export SILICONFLOW_API_KEY=sk-xxxxx

# 或使用 OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-xxxxx
```

### 3. 启动服务

```bash
python -m agent.agent_core.server
# 或
uvicorn agent.agent_core.server:create_app --host 0.0.0.0 --port 9123 --reload
```

### 4. 访问

- **API 文档**: http://localhost:9123/docs
- **智能体面板**: http://localhost:7575/agent  （通过 Textream DirectorServer）

## API 端点

### 记忆

- `GET  /api/memory/list` - 列出记忆
- `POST /api/memory/add` - 添加记忆
- `GET  /api/memory/search?q=xxx` - 搜索记忆
- `GET  /api/memory/persona` - 获取用户画像
- `GET  /api/memory/error-book` - 获取错题本

### 知识库

- `GET  /api/knowledge/list` - 列出知识库文件
- `GET  /api/knowledge/search?q=xxx` - 搜索知识库
- `POST /api/knowledge/add` - 添加知识库文件

### LLM 聊天

- `POST /api/chat` - 智能对话（支持记忆 + 知识库增强）

## 升级计划

- ✅ **Phase 1** (当前): 模块化重构
- 🔄 **Phase 2**: One Memory 集成 + 弹幕实时联动
- ⏳ **Phase 3**: 跨平台 + Windows 支持
