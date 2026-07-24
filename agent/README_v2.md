# Textream Agent Core v2.0

新一代智能提词器 + AI 军师系统。

## 📁 架构

```
agent/
├── agent_core/              # 新智能体内核（Python）
│   ├── __init__.py
│   ├── config.py            # 配置管理
│   ├── server.py            # FastAPI 主服务
│   ├── memory/              # 记忆系统（当前：JSON 文件；未来：One Memory）
│   │   ├── __init__.py
│   │   └── manager.py       # 记忆 CRUD + 用户画像 + 错题本
│   ├── knowledge/           # 知识库（当前：全文搜索；未来：向量化 + RAG）
│   │   ├── __init__.py
│   │   └── manager.py       # 知识库管理 + 全文检索
│   ├── llm/                 # LLM 路由层
│   │   ├── __init__.py
│   │   ├── router.py        # 多 LLM 提供商路由
│   │   └── prompts.py       # 提词器专用 Prompt 模板
│   └── danmaku/             # 弹幕处理模块（Phase 2）
│       ├── __init__.py
│       └── (scraper.py, responder.py - 待实现)
├── agent_server.py          # 旧版服务（向后兼容）
├── run_agent_v2.py          # 新服务启动脚本
└── README.md                # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/mac/Desktop/textream-cn-master/agent
pip install fastapi uvicorn openai pydantic python-multipart
```

### 2. 配置 LLM

```bash
# 推荐：SiliconFlow（国内访问快，支持 Qwen2.5-72B）
export LLM_PROVIDER=siliconflow
export SILICONFLOW_API_KEY=sk-xxxxx

# 或使用 OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-xxxxx

# 或使用 DeepSeek
export LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-xxxxx
```

### 3. 启动服务

```bash
# 开发模式（支持热重载）
python run_agent_v2.py

# 或使用 uvicorn
uvicorn agent.agent_core.server:create_app --host 0.0.0.0 --port 9123 --reload
```

### 4. 访问

- **API 文档**: http://localhost:9123/docs
- **智能体面板**: http://localhost:7575/agent  （通过 Textream DirectorServer）
- **健康检查**: http://localhost:9123/api/health

## 📡 API 端点

### 记忆

- `GET  /api/memory/list?limit=50&offset=0&user_id=default&tag=` - 列出记忆
- `POST /api/memory/add` - 添加记忆
- `DELETE /api/memory/delete/{memory_id}` - 删除记忆
- `GET  /api/memory/search?q=关键词` - 搜索记忆
- `GET  /api/memory/persona?user_id=default` - 获取用户画像
- `GET  /api/memory/error-book?user_id=default` - 获取错题本

### 知识库

- `GET  /api/knowledge/list` - 列出知识库文件
- `GET  /api/knowledge/search?q=关键词` - 搜索知识库
- `POST /api/knowledge/add` - 添加知识库文件
- `DELETE /api/knowledge/delete/{name}` - 删除知识库文件

### LLM 聊天

- `POST /api/chat` - 智能对话（支持记忆 + 知识库增强）

### 状态

- `GET /api/health` - 健康检查
- `GET /api/status` - 详细状态

## 🔄 升级计划

- ✅ **Phase 1** (当前): 模块化重构
- 🔄 **Phase 2**: One Memory 集成 + 弹幕实时联动
- ⏳ **Phase 3**: 跨平台 + Windows 支持

## 💡 下一步

详见完整架构文档：`/Users/mac/Desktop/textream-cn-master/ARCHITECTURE_PLAN.md`（待生成）
