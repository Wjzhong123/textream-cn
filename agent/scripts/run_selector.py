#!/usr/bin/env python3
"""
CaptiOCR 区域选择器 — 独立子进程。
通过 stdout 输出 JSON 结果，不依赖父进程的 tkinter 状态。
"""
import json
import os
import sys
import tkinter as tk
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────────────
# 当前脚本位于 agent/scripts/run_selector.py
_agent_dir = Path(__file__).parent.parent

# 添加 CaptiOCR vendor 路径
_vendor_captiocr = str(_agent_dir / "vendor" / "captiocr")
if _vendor_captiocr not in sys.path:
    sys.path.insert(0, _vendor_captiocr)

# TCL/TK 环境
_tcl_path = "/usr/local/Cellar/tcl-tk/9.0.3/lib/tcl9.0"
if os.path.isdir(_tcl_path):
    os.environ.setdefault("TCL_LIBRARY", _tcl_path)

_system_tessdata = "/usr/local/share/tessdata"
if os.path.isdir(_system_tessdata):
    os.environ.setdefault("TESSDATA_PREFIX", _system_tessdata)

# ── 导入并运行选择器 ──────────────────────────────────────────────────
from captiocr.ui.selection_window import SelectionWindow

root = tk.Tk()
root.withdraw()
win = SelectionWindow(root)
area = win.select_area()
root.destroy()

if area:
    x1, y1, x2, y2 = area
    result = {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}
    print(json.dumps(result))
else:
    print(json.dumps(None))