# Textream 智能提词器 → 直播 AI 军师
## 完整架构升级路线图

**项目**: `/Users/mac/Desktop/textream-cn-master`
**当前版本**: v1.0（中文本地化版）
**目标版本**: v2.0（智能提词器 + 弹幕 AI 军师）
**更新日期**: 2026-07-24

---

## 一、项目现状分析

### ✅ 已有基础

| 模块 | 状态 | 说明 |
|------|------|------|
| **Textream（Swift 客户端）** | ✅ 完整 | macOS 提词器，带 DirectorServer（端口 7575） |
| **DirectorServer** | ✅ 完整 | WebSocket + HTTP，前端控制台（含"智能体"标签页） |
| **Agent Server v1** | ⚠️ 基础版 | `agent/agent_server.py`，FastAPI，基础记忆+知识库+LLM |
| **One Memory（外部）** | ✅ 可用 | `/Users/mac/Desktop/oh-agent-panel`，成熟记忆系统 |
| **中文本地化** | ✅ 100% | 完整中文本地化 |

### ❌ 缺失的关键能力

| 能力 | 当前状态 | 目标 |
|------|---------|------|
| **弹幕捕获** | ❌ 无 | 屏幕 OCR / 平台 API |
| **记忆系统** | ⚠️ 简陋（JSON 文件） | 向量检索 + 记忆衰减 + 长期画像（One Memory） |
| **知识库** | ⚠️ 全文匹配 | 向量化 + RAG + 自动索引 |
| **LLM 配置** | ❌ 硬编码（环境变量） | 可视化配置 + 多提供商路由 |
| **Windows 支持** | ❌ 完全依赖 Swift（macOS 专属） | 跨平台 Web + 轻量客户端壳 |
| **实时弹幕应答** | ❌ 无 | 弹幕意图识别 → 知识库 RAG → 救场话术生成 |

---

## 二、三步走升级路线图

### Phase 1: 智能体内核重构（1-2 周） ✅ **已完成**
**目标**：模块化重构，为后续升级打基础

#### 已完成工作

- [x] 创建 `agent/agent_core/` 模块化架构
  ```
  agent_core/
  ├── __init__.py          # 包入口
  ├── config.py            # 统一配置管理
  ├── server.py            # FastAPI 主服务（11 个 API 端点）
  ├── memory/manager.py    # 记忆管理器（当前：JSON 文件）
  ├── knowledge/manager.py # 知识库管理器（当前：全文搜索）
  └── llm/
      ├── router.py        # 多 LLM 提供商路由
      └── prompts.py       # 提词器专用 Prompt 模板
  ```
- [x] 支持多 LLM 提供商（SiliconFlow / OpenAI / DeepSeek / Anthropic）
- [x] 标准化 API 接口（与 DirectorServer 兼容）
- [x] 创建 `run_agent_v2.py` 启动脚本

#### Phase 1 下一步

- [ ] **验证新服务运行**：
  ```bash
  cd /Users/mac/Desktop/textream-cn-master/agent
  pip install fastapi uvicorn openai pydantic
  export LLM_PROVIDER=siliconflow
  export SILICONFLOW_API_KEY=sk-xxxxx
  python run_agent_v2.py
  ```

- [ ] **测试 API 端点**：
  - http://localhost:9123/health
  - http://localhost:9123/api/status
  - http://localhost:9123/docs（Swagger UI）

---

### Phase 2: One Memory + 弹幕实时联动（2-3 周） 🔄 **待启动**

#### 2.1 集成 One Memory

**目标**：用 One Memory 替换简陋的 JSON 文件存储

**实施步骤**：

1. **封装 One Memory 客户端**：
   ```python
   # agent/agent_core/memory/manager.py
   from one import MemoryClient

   class MemoryManagerV2:
       def __init__(self):
           self.client = MemoryClient(
               project_path="/Users/mac/Desktop/oh-agent-panel"
           )

       def recall_relevant(self, query, limit=5):
           """基于向量相似度检索相关记忆"""
           return self.client.search_memories(query, limit=limit)
   ```

2. **迁移现有记忆**：
   ```bash
   # 将 JSON 文件中的记忆导入 One Memory
   python scripts/migrate_memories.py
   ```

3. **利用 One Memory 能力**：
   - ✅ 向量检索（自动语义搜索）
   - ✅ 跨会话记忆连续性
   - ✅ 记忆衰减机制（长期记忆管理）
   - ✅ 多用户隔离（未来支持多主播）

#### 2.2 知识库向量化 + RAG

**目标**：从全文匹配升级到语义检索

**技术栈**：
- **轻量方案**：ChromaDB（本地运行，无需外部服务）
- **企业级方案**：Pinecone / Weaviate（云服务）

**实施步骤**：

1. **添加向量化支持**：
   ```python
   # agent/agent_core/knowledge/vector_store.py
   import chromadb

   class VectorStore:
       def __init__(self):
           self.client = chromadb.PersistentClient(path="~/.textream/chroma")
           self.collection = self.client.get_or_create_collection("knowledge")

       def add_document(self, name, content):
           # 自动分块 + 向量化
           chunks = self.chunk_text(content)
           embeddings = self.embed(chunks)
           self.collection.add(documents=chunks, embeddings=embeddings, ids=[...])

       def search(self, query, top_k=3):
           query_embedding = self.embed([query])[0]
           return self.collection.query(query_embeddings=[query_embedding], n_results=top_k)
   ```

2. **实现 RAG 流水线**：
   ```python
   # agent/agent_core/knowledge/rag_engine.py
   class RAGEngine:
       async def generate_response(self, query):
           # 1. 向量检索相关文档
           docs = self.vector_store.search(query, top_k=3)

           # 2. 调取相关记忆
           memories = self.memory_manager.recall_relevant(query, limit=3)

           # 3. 构建增强 Prompt
           context = self.build_context(query, docs, memories)

           # 4. LLM 生成回复
           return await self.llm.chat_with_context(query, context)
   ```

#### 2.3 弹幕捕获 + 实时应答 🔥 **核心功能**

**方案选择**：鼠标框选 OCR（见下方详细方案）

**实施步骤**：

1. **屏幕 OCR 模块**：
   ```python
   # agent/agent_core/danmaku/scraper.py
   import mss
   import cv2
   import numpy as np

   class DanmakuCapture:
       """屏幕区域截图 + OCR 弹幕捕获"""
       def __init__(self):
           self.sct = mss.mss()
           self.region = None  # 用户框选的屏幕区域

       def set_region(self, x, y, w, h):
           self.region = {"top": y, "left": x, "width": w, "height": h}

       async def capture_and_parse(self):
           # 1. 截图
           screenshot = self.sct.grab(self.region)

           # 2. OCR 识别（macOS Vision 或 RapidOCR）
           text = await self.ocr_recognize(screenshot)

           # 3. 去重（对比历史缓存）
           new_danmaku = [t for t in text if t not in self.cache]

           return new_danmaku
   ```

2. **实时应答生成器**：
   ```python
   # agent/agent_core/danmaku/responder.py
   class LiveResponder:
       async def generate_response(self, danmaku):
           # 1. 弹幕意图分类
           intent = await self.classify_intent(danmaku)

           # 2. RAG 检索知识库
           kb_chunks = await self.rag_engine.retrieve(danmaku, top_k=3)

           # 3. 调取用户画像
           persona = self.memory_manager.get_persona()

           # 4. 生成救场话术
           response = await self.llm.chat_with_system(
               danmaku,
               system=f"""你是主播的 AI 军师。
               用户画像：{persona}
               知识库：{kb_chunks}

               请生成 3 档话术：
               - 🟢 保守版
               - 🟡 中性版
               - 🔴 高情商版
               """
           )

           # 5. 推送到提词器侧边栏（WebSocket）
           await self.push_to_teleprompter(response)

           return response
   ```

3. **WebSocket 实时推送**：
   ```python
   # 通过 DirectorServer 的 WebSocket 推送给前端
   # agent/agent_core/server.py
   from fastapi import WebSocket

   @app.websocket("/ws/danmaku")
   async def danmaku_ws(websocket: WebSocket):
       await websocket.accept()
       while True:
           response = await responder.generate_next()
           await websocket.send_json(response)
   ```

---

### Phase 3: 跨平台 + Windows 支持（2-3 周）⏳ **待规划**

#### 方案选择

| 方案 | 成本 | 优势 | 劣势 |
|------|------|------|------|
| **A. Electron 重构前端** | 高（2-3 周） | 跨平台完美 | 需要重写 SwiftUI |
| **B. Tauri 轻量跨平台** | 中（1-2 周） | 体积小、性能好 | 生态不如 Electron |
| **C. Web 控制台 + Windows 客户端** | 低（3-5 天） | 最快落地 | 体验割裂 |

**推荐路线**：
1. **短期（MVP）**：方案 C — 将 DirectorServer 改为独立 Web 服务，Windows 用轻量壳加载
2. **中期（完善）**：方案 B — Tauri 跨平台客户端
3. **长期（极致）**：方案 A — Electron 全功能跨平台

#### 打包方案（一键启动）

**macOS**：
```bash
# 1. PyInstaller 打包 Python 智能体
pyinstaller --onefile --add-data "knowledge:knowledge" run_agent_v2.py
# → dist/agent-core

# 2. Xcode 打包 Swift App + 内嵌 agent-core
# Textream.app/Contents/Resources/agent-core
```

**Windows**（方案 C）：
```
TextreamAgent/
├── TextreamAgent.exe          # Tauri/Electron 壳（仅加载 Web 控制台）
├── agent-core.exe             # 内嵌 Python 智能体
└── 启动.bat                    # 一键启动脚本
```

---

## 三、技术细节：弹幕捕获方案

### 方案：屏幕框选 OCR

**为什么选这个方案？**
- ✅ 全平台通用（无视平台 API 限制）
- ✅ 免授权（不用申请直播平台开发者权限）
- ✅ 所见即所得（鼠标框一下，自动捕获）

**技术实现**：

#### macOS
```python
# 使用 PyObjC 调用原生 Vision 框架（极快、离线）
import Vision
from AppKit import NSCIImageRep

def ocr_with_vision(image_np):
    """使用 macOS Vision 框架 OCR（最快、最准）"""
    # 转换 numpy 图像为 CGImage
    cg_image = ... # numpy → CGImage 转换

    # 创建 OCR 请求
    request = VNRecognizeTextRequest()
    request.recognitionLevel = VNRequestTextRecognitionLevelAccurate
    request.recognitionLanguages = ["zh-Hans", "en"]

    # 执行识别
    handler = VNImageRequestHandler(cgImage, options={})
    handler.performRequests([request], error=None)

    # 提取文本
    results = request.results or []
    return [obs.topCandidates(1)[0].string for obs in results]
```

#### Windows
```python
# 使用 RapidOCR（轻量、跨平台）
from rapidocr_onnxruntime import RapidOCR

def ocr_with_rapidocr(image_np):
    """使用 RapidOCR（支持中英文）"""
    engine = RapidOCR()
    result, _ = engine(image_np)
    return [line[1] for line in result] if result else []
```

#### 截图 + OCR 循环
```python
import time
import asyncio

class DanmakuCapture:
    def __init__(self):
        self.sct = mss.mss()
        self.region = None
        self.cache = set()

    async def capture_loop(self, interval=1.0):
        """高频截图循环"""
        while True:
            if not self.region:
                await asyncio.sleep(interval)
                continue

            # 1. 截图
            screenshot = self.sct.grab(self.region)
            img_np = np.array(screenshot)

            # 2. OCR
            text_lines = self.ocr_recognize(img_np)

            # 3. 去重
            new_lines = [t for t in text_lines if t not in self.cache]

            # 4. 返回新弹幕
            if new_lines:
                yield new_lines
                self.cache.update(new_lines)

            await asyncio.sleep(interval)
```

---

## 四、关键决策与架构原则

### 为什么坚持选 B 方案（DirectorServer 扩展）而非 A（Swift 重写）？

**选 B 的理由**：

1. **迭代速度**：Python 智能体需要高速迭代（Prompt 调优、记忆策略、知识库），Swift 编译太慢
2. **职责清晰**：Textream 做 UI，Python 做智能计算
3. **无缝升级**：DirectorServer 已有"智能体"标签页，只需后端替换

**不选 A 的理由**：

1. **编译地狱**：每次改 Prompt 都要重新编译 Swift App
2. **架构越权**：提词器不应该承载 LLM 状态机
3. **能力复用**：One Memory 是 Python，无法在 Swift 中直接调用

### Windows 支持策略

**短期（3 个月内）**：
- 专注 macOS 打磨，验证 PMF
- 不花精力做 Windows 移植

**中期（PMF 验证后）**：
- 将 Python 智能体改为独立服务
- 用 Tauri 做轻量跨平台壳

**长期（商业化后）**：
- Electron 全功能跨平台版
- OBS 插件形态（直接嵌入推流软件）

---

## 五、立即开始的行动清单

### ✅ Phase 1: 智能体内核重构（已完成 90%）

- [x] 创建 `agent_core/` 模块化架构
- [x] 实现 11 个标准化 API 端点
- [x] 多 LLM 提供商路由
- [x] Prompt 模板系统
- [ ] **下一步**：测试新服务运行

### 🔄 Phase 2: One Memory + 弹幕（下一步）

- [ ] 验证 Phase 1 服务运行
- [ ] 封装 One Memory 客户端
- [ ] 迁移现有记忆数据
- [ ] 实现知识库向量化（ChromaDB）
- [ ] 实现 RAG 引擎
- [ ] 实现屏幕 OCR 弹幕捕获
- [ ] 实现实时应答生成器
- [ ] WebSocket 实时推送到提词器

### ⏳ Phase 3: 跨平台（PMF 验证后）

- [ ] 评估用户反馈
- [ ] 决定 Windows 方案（C → B → A）
- [ ] 打包一体机（PyInstaller + Tauri/Electron）

---

## 六、资源与参考

### 项目位置
- **Textream**: `/Users/mac/Desktop/textream-cn-master`
- **One Memory**: `/Users/mac/Desktop/oh-agent-panel`
- **Moat**: `/Users/mac/Desktop/moat`（代码质量检查）

### 关键文件
- **DirectorServer.swift**: `Textream/Textream/DirectorServer.swift`（端口 7575）
- **新智能体内核**: `agent/agent_core/server.py`（端口 9123）
- **旧版服务**: `agent/agent_server.py`（向后兼容）

### LLM 推荐配置
- **SiliconFlow Qwen2.5-72B**：国内访问快，中文能力强
- **DeepSeek-V3**：成本低，推理强
- **OpenAI GPT-4o**：稳定，生态完善

### 下一步文档
- **快速启动指南**: `agent/README_v2.md`
- **完整架构设计**: 本文档
- **One Memory API 文档**: `/Users/mac/Desktop/oh-agent-panel/docs`

---

**架构设计**: Claude Code
**更新日期**: 2026-07-24
**项目状态**: Phase 1 完成，Phase 2 待启动
