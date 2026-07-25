#!/usr/bin/env python3
"""
简单的 OCR 测试 - 使用 macOS Vision 框架
"""

import subprocess
import tempfile
from pathlib import Path

def ocr_with_vision(image_path: str) -> list[str]:
    """使用 macOS Vision 框架进行 OCR"""

    script = f'''
    use framework "Foundation"
    use framework "Vision"

    set imagePath to "{image_path}"
    set imageURL to current application's NSURL's fileURLWithPath:imagePath

    set imageRef to current application's CIImage's imageWithContentsOfURL:imageURL
    set requestHandler to current application's VNImageRequestHandler's alloc()'s initWithCIImage:imageRef options:(current application's NSDictionary's dictionary())

    set ocrRequest to current application's VNRecognizeTextRequest's alloc()'s init()
    ocrRequest's setRecognitionLevel:(current application's VNRequestTextRecognitionLevelAccurate)
    ocrRequest's setRecognitionLanguages:{{"zh-Hans", "en"}}

    set textArray to current application's NSMutableArray's array()

    requestHandler's performRequests:{{ocrRequest}} |error|:(missing value)

    set results to ocrRequest's results()
    repeat with observation in results
        set topCandidate to (observation's topCandidates:1)'s firstObject()
        if topCandidate is not missing value then
            (textArray's addObject:(topCandidate's |string|() as text))
        end if
    end repeat

    set AppleScript's text item delimiters to linefeed
    set resultString to textArray's componentsJoinedByString:linefeed
    return resultString
    '''

    proc = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )

    if proc.returncode != 0:
        print(f"错误: {proc.stderr}")
        return []

    output = proc.stdout.strip()
    if not output:
        return []

    return [line.strip() for line in output.split('\n') if line.strip()]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 test_ocr.py <图片路径>")
        sys.exit(1)

    image_path = sys.argv[1]
    print(f"OCR 识别: {image_path}")
    texts = ocr_with_vision(image_path)

    if texts:
        print(f"\n识别到 {len(texts)} 条文本:")
        for i, text in enumerate(texts, 1):
            print(f"  {i}. {text}")
    else:
        print("\n未识别到任何文本")
