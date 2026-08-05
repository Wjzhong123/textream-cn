# textream-cn-master 架构真理文档

## 项目概述
textream-cn-master 是一个多平台弹幕应用，包括 iOS 客户端、Python 后端和 Web 控制台。

## 架构分层

### 1. API 层 (agent/agent_core)
FastAPI 后端路由，提供服务入口。包含配置管理、错误总线。

### 2. 业务层 (agent/agent_core/danmaku, agent/agent_core/knowledge)
弹幕业务逻辑：抓取、处理、响应。知识库管理与检索。

### 3. 基础设施层 (agent/agent_core/llm, agent/agent_core/memory, agent/one_memory_adapter, agent/captiocr_adapter)
LLM 路由、记忆管理、外部适配器。

### 4. 展示层 (web-console/)
React/TypeScript 前端控制台，通过 HTTP API 与后端通信。

### 5. 工具层 (agent/agent_core/danmaku/ocr_scripts, agent/scripts)
OCR 脚本、辅助工具。

### 6. 测试层 (tests/)
自动化测试。

## 分层规则
1. 展示层不得直接调用后端模块
2. API 层不得直接调用适配层（需通过依赖注入）
3. 基础设施层不得依赖业务层
4. 适配层不能反向依赖 API 层
