#!/bin/bash
# Moat post-commit hook — 提交后自动沉淀调试经验
#
# 使用方法：在 commit message 中按以下格式写经验块，提交后自动写入 .moat/memory.db
#
#   [经验] 一句话标题
#   问题: 遇到的问题描述
#   根因: 根因分析
#   修复: 解决方案（可以多行）
#
# 示例：
#   git commit -m "修复 OCR 长弹幕拆分
#
#   [经验] OCR 弹幕长评论换行被拆开
#   问题: 超过2行的长弹幕被拆成多条显示
#   根因: 水平投影用"非白像素"比例阈值，短行亮像素占比低被当噪声丢弃
#   修复: 阈值改双条件（绝对像素>=8 或占比>=0.5%）+ 行距聚类 gap<20px 合并换行"
set -e

# 仅在有 .moat 目录时执行
ROOT="$(git rev-parse --show-toplevel)"
if [ ! -d "$ROOT/.moat" ]; then
    exit 0
fi

# 获取最近一次 commit 的 message
MSG="$(git log -1 --pretty=%B)"

# 没有 [经验] 标记则跳过
if ! echo "$MSG" | grep -q '\[经验\]'; then
    exit 0
fi

# 解析经验块
TITLE="$(echo "$MSG" | grep '\[经验\]' | head -1 | sed 's/.*\[经验\]\s*//' | sed 's/^\[经验\]//' | xargs)"
PROBLEM="$(echo "$MSG" | grep '^问题:' | head -1 | sed 's/^问题:\s*//')"
ROOTCAUSE="$(echo "$MSG" | grep '^根因:' | head -1 | sed 's/^根因:\s*//')"
FIX="$(echo "$MSG" | grep '^修复:' | head -1 | sed 's/^修复:\s*//')"

if [ -z "$TITLE" ]; then
    echo "⚠️  [Moat] 检测到 [经验] 标记但未找到标题，跳过沉淀"
    exit 0
fi

# 需要 python3 + sqlite3 写入（兼容 .moat/memory.db 的 lessons / fix_patterns 表）
if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

python3 - "$ROOT" "$TITLE" "$PROBLEM" "$ROOTCAUSE" "$FIX" << 'PYEOF'
import json
import sqlite3
import sys
import time
from pathlib import Path

root, title, problem, rootcause, fix = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
db_path = Path(root) / ".moat" / "memory.db"

if not db_path.exists():
    sys.exit(0)

now = time.strftime("%Y-%m-%d %H:%M:%S")
content_hash = f"commit-{title}"

try:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 1. 写入 lessons（经验教训）
    lid = f"lsn_{int(time.time() * 1000)}"
    principles = []
    if rootcause:
        principles.append(f"根因: {rootcause}")
    if fix:
        principles.append(f"修复: {fix}")

    cursor = conn.execute(
        "SELECT id FROM lessons WHERE content_hash=? LIMIT 1", (content_hash,)
    )
    row = cursor.fetchone()
    if row:
        # 已存在则更新，不重复
        pass
    else:
        conn.execute(
            "INSERT OR IGNORE INTO lessons "
            "(id, title, failed_tests, error_summary, failure_count, principles, negative_examples, content_hash, captured_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                lid,
                title,
                json.dumps([problem] if problem else []),
                f"💡 [经验] {title}" + (f"\n问题: {problem}" if problem else "") + (f"\n根因: {rootcause}" if rootcause else "") + (f"\n修复: {fix}" if fix else ""),
                1,
                json.dumps(principles, ensure_ascii=False),
                json.dumps([], ensure_ascii=False),
                content_hash,
                now,
            ),
        )

    # 2. 写入 fix_patterns（修复模式，key 用标题）
    signature = title
    cursor = conn.execute(
        "SELECT id FROM fix_patterns WHERE error_signature=? LIMIT 1", (signature,)
    )
    row = cursor.fetchone()
    if row:
        conn.execute(
            "UPDATE fix_patterns SET fix_template=?, last_used=?, usage_count=usage_count+1 WHERE id=?",
            (fix, now, row["id"]),
        )
    else:
        conn.execute(
            "INSERT OR IGNORE INTO fix_patterns (id, error_signature, fix_template, success_rate, usage_count, last_used, created_at) "
            "VALUES (?, ?, ?, 1.0, 1, ?, ?)",
            (
                f"fp_{int(time.time() * 1000)}",
                signature,
                fix or "",
                now,
                now,
            ),
        )

    conn.commit()
    conn.close()
    print(f"📝 [Moat] 调试经验已沉淀: {title}")
    if rootcause:
        print(f"   根因: {rootcause}")
    if fix:
        print(f"   修复: {fix}")
except Exception as e:
    # 沉淀失败不影响提交
    print(f"⚠️  [Moat] 经验沉淀失败(不阻塞): {e}")
    sys.exit(0)
PYEOF
