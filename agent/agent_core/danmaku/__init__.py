"""
弹幕捕获模块 - 屏幕 OCR + 弹幕识别

基于 DirectorServer（Textream.app）或 PIL.ImageGrab 实现屏幕弹幕实时捕获
"""

from .scraper import DanmakuCapture, DirectorDanmakuCapture, create_capture
from .responder import DanmakuResponder
from .processor import DanmakuProcessor

__all__ = ["DanmakuCapture", "DirectorDanmakuCapture", "create_capture", "DanmakuResponder", "DanmakuProcessor"]
