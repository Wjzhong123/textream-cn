"""
CaptiOCR 适配层

将 CaptiOCR 的实时屏幕捕获引擎桥接到 Textream 后端。
CaptiOCR 提供:
- 视觉区域选择（鼠标拖拽框选）
- 连续截图（mss，快于 PIL.ImageGrab）
- 智能去重（ROVER + TF-IDF 新颖度评分）

用法:
    from captiocr_adapter import CaptiOCRBridge
    bridge = CaptiOCRBridge()
    await bridge.start()  # 启动捕获
    await bridge.set_region(x, y, w, h)  # 或以编程方式设区域
"""

from .bridge import CaptiOCRBridge

__all__ = ["CaptiOCRBridge"]
