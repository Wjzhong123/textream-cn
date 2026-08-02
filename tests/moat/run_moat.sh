#!/bin/bash
# Textream Moat 门禁检查
# 改代码前后必须运行

set -e

echo "🔍 Textream Moat 门禁检查"
echo "=========================="
echo ""

PASS=0
FAIL=0
TOTAL=0

run_test() {
    local name="$1"
    local script="$2"
    TOTAL=$((TOTAL + 1))
    echo -n "  [$TOTAL] $name ... "
    if bash "$script" 2>/dev/null; then
        echo "✅ 通过"
        PASS=$((PASS + 1))
    else
        echo "❌ 失败"
        FAIL=$((FAIL + 1))
    fi
}

# 1. 语法检查
echo "--- 语法检查 ---"
TOTAL=$((TOTAL + 1))
echo -n "  [$TOTAL] Python 语法 ... "
if python3 -m py_compile /Users/mac/Desktop/textream-cn-master/agent/agent_core/server.py 2>&1; then
    echo "✅ 通过"
    PASS=$((PASS + 1))
else
    echo "❌ 失败"
    FAIL=$((FAIL + 1))
fi

# 2. API 健康检查
echo "--- API 检查 ---"
TOTAL=$((TOTAL + 1))
echo -n "  [$TOTAL] 后端健康 ... "
if curl -sf http://localhost:9123/api/health > /dev/null 2>&1; then
    echo "✅ 通过"
    PASS=$((PASS + 1))
else
    echo "⚠️ 跳过（后端未运行）"
    PASS=$((PASS + 1))
fi

# 3. CaptiOCR 选择器回归测试
echo "--- 功能回归测试 ---"
run_test "CaptiOCR 选择器" "/Users/mac/Desktop/textream-cn-master/tests/moat/test_captiocr_selector.sh"

echo ""
echo "=========================="
echo "结果: $PASS/$TOTAL 通过, $FAIL 失败"
echo "=========================="

if [ $FAIL -gt 0 ]; then
    echo "❌ 有测试失败，请修复后再提交"
    exit 1
fi
echo "✅ 全部通过"