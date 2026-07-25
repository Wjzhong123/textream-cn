"""
CaptiOCR 适配配置
"""

import os
from pathlib import Path

# CaptiOCR 引擎路径
CAPTIOCR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "captiocr"
CAPTIOCR_PKG = CAPTIOCR_DIR / "captiocr"

# OCR 语言（默认中英文）
OCR_LANG = os.environ.get("OCR_LANG", "chi_sim+eng")

# 捕获间隔（秒）
CAPTURE_INTERVAL = float(os.environ.get("CAPTURE_INTERVAL", "1.0"))
