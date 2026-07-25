#!/bin/bash
# 启动 Textream Agent 后端（带权限持久化）
# 用 .app 壳启动 → macOS 记住屏幕录制权限 → 不再反复弹窗

DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$DIR/agent"

echo "🔄 启动 Textream Agent 后端..."
echo "  目录: $AGENT_DIR"
echo ""

# 启动后端（通过 .app 壳 → Python）
open -a TextreamAgent --args "$AGENT_DIR/run_agent_v2.py"

sleep 2
echo "✅ 后端启动中..."
echo "  API:      http://localhost:9123"
echo "  Swagger:  http://localhost:9123/docs"
echo ""
echo "📌 首次使用请在系统设置中授予「TextreamAgent」屏幕录制权限"
echo "  设置 → 隐私与安全性 → 屏幕录制 → 添加 TextreamAgent"
