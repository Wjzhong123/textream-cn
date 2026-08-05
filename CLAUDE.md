# Textream — 直播 AI 军师

## 接手任务前的铁律

**必须执行，不可跳过：**

1. 调用 `skill(name="architecture-first-dev")` 加载架构优先开发技能
2. 调用 `query_structure(query="开发流程 架构 注意事项")` 查询历史结构模板
3. 调用 `memory_read(room="Cognitive", hall="Lessons")` 读取历史教训
4. 跑 `moat check` 确认当前系统健康
5. 读 `git status` 和 `git log --oneline -5` 了解当前状态
6. 读下面这个架构图，理解全局后再动手

## 项目架构总览

```
                              ┌─────────────────────────────────┐
                              │      前端 Web Console            │
                              │  (React + Vite, port 9123)       │
                              │  弹幕面板 / 设置 / 状态           │
                              └──────────┬──────────────────────┘
                                         │ HTTP / WebSocket
                              ┌──────────▼──────────────────────┐
                              │     Agent Core (Python)          │
                              │     FastAPI 服务, port 9123      │
                              │                                  │
                              │  ┌──────────┐  ┌──────────────┐  │
                              │  │ 记忆系统  │  │  知识库      │  │
                              │  │ AI-memory │  │  RAG/向量    │  │
                              │  │ / JSON    │  │               │  │
                              │  └──────────┘  └──────────────┘  │
                              │                                  │
                              │  ┌────────────────────────┐      │
                              │  │  弹幕引擎 (Danmaku)     │      │
                              │  │  ├─ DanmakuCapture     │      │
                              │  │  │   (PIL.ImageGrab)   │      │
                              │  │  ├─ CaptiOCRBridge     │      │
                              │  │  │   (CaptiOCR 引擎)   │      │
                              │  │  └─ DirectorDanmaku    │      │
                              │  │      Capture (Director) │      │
                              │  └────────────────────────┘      │
                              └──────────┬──────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
         ┌──────────▼──────┐   ┌────────▼───────┐   ┌───────▼────────┐
         │  Textream.app   │   │  CaptiOCR      │   │   Director     │
         │  (Swift/macOS)  │   │  引擎 (Python)  │   │   Server       │
         │  DirectorServer │   │  SelectionWin  │   │   (Swift)      │
         │  port 7575      │   │  OCR 引擎      │   │   port 7575    │
         └─────────────────┘   └────────────────┘   └────────────────┘
```

## 截图引擎优先级

| 引擎 | 截图方式 | 优先级 | 状态 |
|------|---------|--------|------|
| **DanmakuCapture** | `PIL.ImageGrab.grab()` (Quartz CoreGraphics) | **主力** | ✅ 当前默认 |
| CaptiOCRBridge | CaptiOCR 内建 `ScreenCapture` (PIL.ImageGrab) | 可选 | ⚡ 启用 `CAPTIOCR_ENABLED=true` |
| DirectorDanmakuCapture | DirectorServer → `screencapture` | 禁用 | ❌ macOS 15+ TCC BUG |

**2026-08-04 决策：** DirectorServer 引擎已禁用。macOS 15+ 对未签名 App 的 `screencapture` 有 TCC 死循环 BUG（同意后仍无限弹窗）。改用 `PIL.ImageGrab.grab()`（Quartz CoreGraphics），间接使用 Textream.app 的录屏权限。

## 数据流

```
用户点击「📐 区域」
  → POST /api/danmaku/selector
  → `CaptiOCR_bridge.show_region_selector()` 或独立 `SelectionWindow`
  → 全屏遮罩 + 鼠标拖拽框选
  → 返回 (x, y, w, h)
  → `processor.set_region(x, y, w, h)`

用户点击「▶ 开始捕获」
  → POST /api/danmaku/start
  → `processor.start()` → `capture.start()`
  → 循环：截图 → OCR → 去重 → 回调
  → 新弹幕通过 WebSocket 推送到前端

用户点击「💬」
  → POST /api/chat
  → LLM 生成救场话术
  → 推送到前端
```

## 文件映射

### Agent Core (Python, `/agent/`)

| 文件 | 职责 | 关键约束 |
|------|------|---------|
| `agent_core/server.py` | FastAPI 主服务，路由，生命周期 | 全局单例 `memory_mgr`, `danmaku_processor` |
| `agent_core/danmaku/processor.py` | 弹幕处理流水线 | `launch()` 已禁用 DirectorServer 自动切换 |
| `agent_core/danmaku/scraper.py` | 截图 + OCR 引擎 | `DirectorDanmakuCapture` (screencapture) 有 TCC BUG |
| `agent_core/danmaku/responder.py` | LLM 应答生成 | 调用 `llm_router` |
| `agent_core/memory/manager.py` | 本地记忆 + 错题本 | JSON 文件存储 |
| `agent_core/memory/ai_memory.py` | AI-memory (MCP 子进程) | 语义搜索 |
| `agent_core/config.py` | 配置管理 | 环境变量 + `one_settings.json` |
| `agent_core/error_bus.py` | 错误总线 | 系统健康监控 |
| `captiocr_adapter/bridge.py` | CaptiOCR 桥接层 | 视觉框选 + 智能去重 |
| `run_agent_v2.py` | 启动脚本 | 含自动打开浏览器逻辑 |

### Textream.app (Swift, `/Textream/`)

| 文件 | 职责 |
|------|------|
| `Textream/TextreamApp.swift` | App 入口，菜单栏 |
| `Textream/AgentCoreManager.swift` | Python 后端进程管理 |
| `Textream/DirectorServer.swift` | DirectorServer HTTP API (port 7575) |
| `Textream/ContentView.swift` | 主视图 |
| `Textream/DictationManager.swift` | 听写功能 |
| `Textream/SpeechRecognizer.swift` | 语音识别 |

### 前端 (React + Vite, `/agent/web-console/`)

| 路径 | 说明 |
|------|------|
| `web-console/src/DanmakuPanel.tsx` | 弹幕捕获面板 |
| `web-console/src/App.tsx` | 主应用 |
| `web-console/src/api.ts` | API 调用封装 |
| `web-console/dist/` | 构建产物 (git 跟踪) |

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/danmaku/status` | GET | 弹幕捕获状态 |
| `/api/danmaku/start` | POST | 开始捕获 |
| `/api/danmaku/stop` | POST | 停止捕获 |
| `/api/danmaku/selector` | POST | 打开区域选择器 |
| `/api/danmaku/region` | POST | 手动设置区域 |
| `/api/danmaku/engine` | POST | 切换引擎 |
| `/api/chat` | POST | LLM 对话 |
| `/api/memory/*` | - | 记忆系统 |
| `/api/knowledge/*` | - | 知识库 |
| `/ws/danmaku` | WebSocket | 弹幕实时推送 |

## 关键红线

### 不要做的事
1. **不要重建 Textream.app 二进制** — 签名改变导致 TCC 授权失效。除非你知道自己在做什么。
2. **不要手动编辑 minified JS** — 总是通过 `pnpm build` 重建前端，然后复制到 `web-console-dist/`。
3. **不要改 `processor.py` 的 `launch()` 去启用 DirectorServer** — 除非 macOS TCC BUG 已修复。
4. **不要改 `vendor/captiocr/` 下的文件** — 这是上游引擎，通过 `captiocr_adapter` 桥接修改。
5. **不要在 `agent_core/danmaku/scraper.py` 里加新的截图方式** — 先讨论架构变更。

### 必须做的事
1. **改代码前跑 `moat check`，改代码后跑 `moat check`** — 两次都通过才能提交。
2. **改代码前读 `git status` 和 `git diff`** — 知道当前状态再动手。
3. **改代码前先看全局架构** — 这个文件就在这。
4. **每次修改只改一个功能点** — 不要同时改截图引擎 + 前端 JS + 重建 App。

## 已知问题

| 问题 | 说明 | 状态 |
|------|------|------|
| macOS 15+ TCC screencapture BUG | 未签名 App 的 screencapture 无限弹窗 | ⚠️ 通过禁用 DirectorServer 绕过 |
| 前端 JS 手动编辑 | 之前手动编辑 minified JS 导致黑屏 | ✅ 已恢复 git 版本 |
| Textream.app 签名 | 重建后 TCC 授权失效 | ⚠️ 不要重建，除非重签名 |
| PIL.ImageGrab 权限 | 需要 Python 进程有录屏权限 | ✅ 子进程继承 Textream.app 权限 |

## Moat 护城河

Moat 是 AI 编码护城河，防止 AI 改代码时搞坏系统。

### 铁律
1. 改代码**前**跑一次 `moat check`，改代码**后**再跑一次。两次都通过才能提交。
2. 任何 AI 工具接手项目，第一件事就是跑 `moat check`。
3. 如果 `moat check` 报错，修到通过为止，不许跳过。
4. **禁止使用 `git commit --no-verify` 绕过检查**。会被拦截。

### 项目记忆（moat-memory）
这个项目积累了一些记忆，改代码前先查看：
```bash
# 查看项目红线（架构规则、编码边界）
moat memory list redlines

# 查看踩坑记录（以前 MOAT 检查失败的地方）
moat memory list lessons

# 查看经验模版
moat memory list templates
```

**自动同步的文件**: `.moat/ai_context.md` 包含上述全部记忆，AI 工具可自动读取。

### 命令
```bash
# 改代码前/后检查（12秒）
moat check

# 实时监控日志错误
moat watch --log logs/backend.log

# Web 错误看板
moat dashboard

# 更新基线（允许的改动后）
moat baseline save
```

### 四层防线
| 层级 | 作用 |
|------|------|
| L1 存活 | 骨架完整、API 存活 |
| L2 结构 | API 返回字段符合契约 |
| L3 关联 | 改了 A B 还能用 |
| L4 基线 | 文件数/路由数不退化 |