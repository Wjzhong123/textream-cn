#!/bin/bash
# Moat AI 启动检测 — AI 工具进入项目时自动运行
# 由 moat init 安装到 .moat/startup_check.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR" || exit 0

# 检查 moat 是否安装
if ! command -v moat &> /dev/null; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🛡️  Moat 护城河未安装                                       ║"
    echo "║                                                              ║"
    echo "║  本项目使用 Moat 保护代码质量，请在修改代码前安装:           ║"
    echo "║    pip install moat-ai                                        ║"
    echo "║    moat init                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi

# 检查 moat 是否已初始化
if [ ! -f ".moat/moat.json" ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🛡️  Moat 未初始化                                           ║"
    echo "║  运行 moat init 初始化项目                                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    moat init
    exit 0
fi

# 显示项目记忆摘要
echo "🛡️  [Moat] 护城河已激活 | $(moat --version 2>/dev/null || echo '?')"
echo ""

# 同步 AI 上下文文件（供 AI 工具自动读取）
moat memory sync 2>/dev/null

# 检查是否有未读的踩坑记录
LESSONS_DIR=".moat/lessons"
if [ -d "$LESSONS_DIR" ]; then
    LESSON_COUNT=$(ls -1 "$LESSONS_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
    if [ "$LESSON_COUNT" -gt 0 ]; then
        echo "⚠️  项目有 $LESSON_COUNT 条踩坑记录，建议先查看:"
        echo "   moat memory list lessons"
        echo ""
    fi
fi

# 检查是否有红线
REDLINE_COUNT=$(moat memory list redlines 2>/dev/null | grep -c "^-" || echo "0")
if [ "$REDLINE_COUNT" -gt 0 ]; then
    echo "📋 项目有 $REDLINE_COUNT 条红线规则"
    echo "   查看: moat memory list redlines"
    echo ""
fi

echo "🔍 改代码前: moat check"
echo "✅ 改代码后: moat check"
echo "📊 Web 看板: moat dashboard"
echo ""
