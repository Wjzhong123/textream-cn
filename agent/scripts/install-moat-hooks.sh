#!/bin/bash
# 安装 Moat 经验沉淀钩子（post-commit）
# 仓库 clone 后首次运行一次： bash agent/scripts/install-moat-hooks.sh
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cp "$ROOT/agent/scripts/moat-post-commit.sh" "$ROOT/.git/hooks/post-commit"
chmod +x "$ROOT/.git/hooks/post-commit"
echo "✅ Moat post-commit 钩子已安装 → .git/hooks/post-commit"
echo "   commit message 带 [经验] 标记时，自动沉淀到 .moat/memory.db"
