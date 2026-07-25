#!/usr/bin/env python3
"""
直播弹幕 OCR 监听器（极简方案）

使用 Pillow ImageGrab + pytesseract
零外部依赖，纯本地运行

依赖：
- Pillow（已安装）
- pytesseract（已安装）
- numpy（已安装）
"""

import time
from PIL import ImageGrab
import pytesseract
import cv2
import numpy as np


class LiveScreenWatcher:
    def __init__(self, bbox=(100, 100, 400, 600)):
        """
        bbox: 屏幕截取的绝对坐标 (left, top, right, bottom)
              代表你用鼠标框选的直播弹幕区域
        """
        self.bbox = bbox
        self.seen_texts = set()  # 用于弹幕去重

    def capture_and_ocr(self):
        try:
            # 1. 使用 Pillow 替代 mss，直接截取屏幕指定区域
            screenshot = ImageGrab.grab(bbox=self.bbox)

            # 2. 转换成 OpenCV 格式
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

            # 3. 图像预处理：二值化放大，提高 OCR 识别率
            # 放大 2 倍
            frame = cv2.resize(frame, (0, 0), fx=2.0, fy=2.0)
            # 阈值处理，让文字更清晰
            _, thresh = cv2.threshold(frame, 150, 255, cv2.THRESH_BINARY)

            # 4. 调用本地 pytesseract 识别文字
            # 配置 --psm 6 假设是一个统一的文本块
            text = pytesseract.image_to_string(thresh, config="--psm 6")

            # 5. 清洗与去重输出
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            new_lines = []
            for line in lines:
                if line not in self.seen_texts:
                    self.seen_texts.add(line)
                    new_lines.append(line)
                    # 控制内存缓存大小
                    if len(self.seen_texts) > 500:
                        self.seen_texts.pop()

            return new_lines

        except Exception as e:
            print(f"OCR 捕捉出错: {e}")
            return []


if __name__ == "__main__":
    print("=== 直播弹幕 OCR 监听器启动 ===")
    print("请把直播弹幕窗口对准指定区域...")

    # 示例坐标
    watcher = LiveScreenWatcher(bbox=(50, 100, 400, 600))

    while True:
        new_msgs = watcher.capture_and_ocr()
        for msg in new_msgs:
            print(f"[捕获新弹幕] -> {msg}")
            # 👉 接下来，你可以直接把 msg 丢给你的 one-memory / 大模型 进行知识库检索和军师回复！

        time.sleep(1.0)  # 每秒扫描一次
