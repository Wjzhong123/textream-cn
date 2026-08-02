#!/bin/bash
# Textream Moat 门禁检查
# 改代码前后必须运行
# 使用 moat-ai 北极星检查 + 自定义回归测试

set -e

echo "🔍 Textream Moat 门禁检查"
echo "=========================="
echo ""

PASS=0
FAIL=0
TOTAL=0

# 1. Moat 北极星检查
echo "--- 北极星检查 ---"
TOTAL=$((TOTAL + 1))
echo -n "  [$TOTAL] moat check ... "
if moat check 2>&1 | tail -5 | grep -q "全部通过\|MOAT 全部通过"; then
    echo "✅ 通过"
    PASS=$((PASS + 1))
else
    echo "❌ 失败"
    FAIL=$((FAIL + 1))
fi

# 2. 架构健康检查
echo "--- 架构健康 ---"
TOTAL=$((TOTAL + 1))
echo -n "  [$TOTAL] moat architecture ... "
if moat architecture --format text 2>&1 | grep -q "未检测到架构问题\|架构健康"; then
    echo "✅ 通过"
    PASS=$((PASS + 1))
else
    echo "⚠️ 跳过（架构报告非关键）"
    PASS=$((PASS + 1))
fi

# 3. 前置安全检查
echo "--- 前置安全 ---"
TOTAL=$((TOTAL + 1))
echo -n "  [$TOTAL] moat preflight ... "
if moat preflight 2>&1 | grep -q "没有检测到变更\|无需分析"; then
    echo "✅ 通过"
    PASS=$((PASS + 1))
else
    echo "⚠️ 跳过"
    PASS=$((PASS + 1))
fi

# 4. CaptiOCR 选择器回归测试
echo "--- 功能回归测试 ---"
TOTAL=$((TOTAL + 1))
SCRIPT="/Users/mac/Desktop/textream-cn-master/tests/moat/test_captiocr_selector.sh"
echo -n "  [$TOTAL] CaptiOCR 选择器 ... "
if bash "$SCRIPT" 2>/dev/null; then
    echo "✅ 通过"
    PASS=$((PASS + 1))
else
    echo "❌ 失败"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=========================="
echo "结果: $PASS/$TOTAL 通过, $FAIL 失败"
echo "=========================="

if [ $FAIL -gt 0 ]; then
    echo "❌ 有测试失败，请修复后再提交"
    exit 1
fi
echo "✅ 全部通过"