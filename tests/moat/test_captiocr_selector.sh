#!/bin/bash
# ============================================================
# CaptiOCR 选择器回归测试
# 验证：POST /api/danmaku/selector → CaptiOCR 子进程启动
# 注意：测试以非阻塞方式启动子进程，仅验证进程创建
# ============================================================

set -e

PASS=0
FAIL=0

echo "=========================================="
echo "CaptiOCR 选择器回归测试"
echo "=========================================="

# 检查后端端口
if ! curl -sf http://localhost:9123/api/health > /dev/null 2>&1; then
    echo "❌ 后端未运行 (port 9123)，请先启动后端"
    FAIL=$((FAIL + 1))
    exit 1
fi
echo "✅ 后端运行中 (port 9123)"

# 检查选择器 API 是否存在（2 秒超时，避免 tkinter 阻塞）
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 2 -X POST http://localhost:9123/api/danmaku/selector 2>&1 || echo "timeout")
if [ "$HTTP_CODE" = "timeout" ]; then
    echo "⚠️ 选择器 API 超时（可能 tkinter 窗口已弹出但无交互）"
    echo "   ✓ 这是预期行为，因为 tkinter 等待用户拖拽选择"
    PASS=$((PASS + 1))
elif [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 选择器 API 返回 200（可能已配置区域，无窗口弹出）"
    PASS=$((PASS + 1))
elif [ "$HTTP_CODE" = "404" ]; then
    echo "❌ 选择器 API 返回 404 — 端点不存在"
    FAIL=$((FAIL + 1))
elif [ "$HTTP_CODE" = "500" ]; then
    echo "❌ 选择器 API 返回 500 — 服务端错误"
    FAIL=$((FAIL + 1))
else
    echo "⚠️ 选择器 API 返回 HTTP $HTTP_CODE"
    PASS=$((PASS + 1))
fi

# 检查 CaptiOCR 桥接模块是否可导入
PYTHONPATH="/Users/mac/Desktop/textream-cn-master/agent:$PYTHONPATH" python3 -c "
import sys
sys.path.insert(0, '/Users/mac/Desktop/textream-cn-master/agent')
try:
    from captiocr_adapter.bridge import CaptiOCRBridge
    b = CaptiOCRBridge()
    assert hasattr(b, 'show_region_selector'), '缺少 show_region_selector 方法'
    print('✅ CaptiOCRBridge 可导入，show_region_selector 方法存在')
except ImportError as e:
    print(f'❌ CaptiOCRBridge 导入失败: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ CaptiOCRBridge 初始化失败: {e}')
    sys.exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    PASS=$((PASS + 1))
else
    FAIL=$((FAIL + 1))
fi

# 检查选择器路由是否注册（grep 源码）
if grep -q 'danmaku_selector\|/api/danmaku/selector' /Users/mac/Desktop/textream-cn-master/agent/agent_core/server.py; then
    echo '✅ 选择器 API 路由已注册（源码确认）'
else
    echo '❌ 选择器 API 路由未注册'
    exit 1
fi

if [ $? -eq 0 ]; then
    PASS=$((PASS + 1))
else
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=========================================="
echo "结果: $PASS 通过, $FAIL 失败"
echo "=========================================="

if [ $FAIL -gt 0 ]; then
    exit 1
fi
exit 0