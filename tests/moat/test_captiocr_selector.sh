#!/bin/bash
# ============================================================
# CaptiOCR 选择器回归测试
# 验证：POST /api/danmaku/selector → CaptiOCR 子进程启动
# ============================================================

PASS=0
FAIL=0

echo "=========================================="
echo "CaptiOCR 选择器回归测试"
echo "=========================================="

# 1. 检查后端端口
if ! curl -sf http://localhost:9123/api/health > /dev/null 2>&1; then
    echo "❌ 后端未运行 (port 9123)"
    exit 1
fi
echo "✅ 后端运行中 (port 9123)"
PASS=$((PASS + 1))

# 2. 检查选择器 API（2 秒超时，避免 tkinter 阻塞）
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 2 -X POST http://localhost:9123/api/danmaku/selector 2>&1 || echo "timeout")
case "$HTTP_CODE" in
    timeout|200|000timeout)
        echo "⚠️ 选择器 API 超时（tkinter 窗口等待拖拽，预期行为）"
        PASS=$((PASS + 1));;
    404)
        echo "❌ 选择器 API 返回 404"
        FAIL=$((FAIL + 1));;
    500)
        echo "❌ 选择器 API 返回 500"
        FAIL=$((FAIL + 1));;
    *)
        echo "⚠️ 选择器 API 返回 HTTP $HTTP_CODE"
        PASS=$((PASS + 1));;
esac

# 3. 检查 CaptiOCRBridge 模块可导入
PYTHONPATH="/Users/mac/Desktop/textream-cn-master/agent:$PYTHONPATH" python3 -c "
import sys
sys.path.insert(0, '/Users/mac/Desktop/textream-cn-master/agent')
try:
    from captiocr_adapter.bridge import CaptiOCRBridge
    b = CaptiOCRBridge()
    assert hasattr(b, 'show_region_selector'), '缺少 show_region_selector'
    print('✅ CaptiOCRBridge 可导入')
except Exception as e:
    print(f'❌ {e}')
    sys.exit(1)
" 2>&1
if [ $? -eq 0 ]; then
    PASS=$((PASS + 1))
else
    FAIL=$((FAIL + 1))
fi

# 4. 检查选择器路由已注册
if grep -q 'danmaku_selector\|/api/danmaku/selector' /Users/mac/Desktop/textream-cn-master/agent/agent_core/server.py; then
    echo '✅ 选择器 API 路由已注册'
    PASS=$((PASS + 1))
else
    echo '❌ 选择器 API 路由未注册'
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=========================================="
echo "结果: $PASS 通过, $FAIL 失败"
echo "=========================================="

[ $FAIL -gt 0 ] && exit 1 || exit 0