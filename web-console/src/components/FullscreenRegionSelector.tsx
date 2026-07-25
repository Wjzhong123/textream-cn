import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../stores/appStore';

interface Point {
  x: number;
  y: number;
}

interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface FullscreenRegionSelectorProps {
  onRegionSelected?: (region: Region) => void;
}

/**
 * 全屏区域选择器组件
 * 支持在整个屏幕上选择截图区域（包括浏览器外的内容）
 *
 * 实现原理：
 * 1. 打开一个新的浏览器窗口，覆盖整个屏幕
 * 2. 在新窗口中拖拽选择区域
 * 3. 将区域坐标转换后发送到后端
 */
export function FullscreenRegionSelector({ onRegionSelected }: FullscreenRegionSelectorProps) {
  const { setCaptureRegion } = useAppStore();
  const [isSelecting, setIsSelecting] = useState(false);
  const [region, setRegionState] = useState<Region | null>(null);
  const [startPoint, setStartPoint] = useState<Point | null>(null);
  const selectionWindowRef = useRef<Window | null>(null);

  // 创建全屏选择窗口
  const startSelection = useCallback(() => {
    // 打开一个新的全屏窗口
    const selectionWindow = window.open(
      '',
      'RegionSelector',
      'width=9999,height=9999,left=0,top=0,menubar=no,toolbar=no,location=no,status=no,resizable=no'
    );

    if (!selectionWindow) {
      alert('请允许浏览器打开弹窗以使用全屏区域选择功能');
      return;
    }

    selectionWindowRef.current = selectionWindow;

    // 写入全屏选择页面
    selectionWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>选择弹幕区域</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            width: 100vw;
            height: 100vh;
            cursor: crosshair;
            position: relative;
          }
          .overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 100, 255, 0.15);
            z-index: 9999;
          }
          .selection-box {
            position: fixed;
            border: 2px dashed #0066ff;
            background: rgba(0, 102, 255, 0.2);
            pointer-events: none;
            z-index: 10000;
          }
          .hint {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 102, 255, 0.95);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10001;
          }
          .hint-sub {
            font-size: 12px;
            opacity: 0.85;
            margin-top: 4px;
          }
          .info {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            z-index: 10001;
          }
        </style>
      </head>
      <body>
        <div class="overlay"></div>
        <div class="hint">
          📐 拖动鼠标选择弹幕区域
          <div class="hint-sub">按 ESC 或点击此处取消</div>
        </div>
        <div id="selectionBox" class="selection-box" style="display: none;"></div>
        <div id="info" class="info" style="display: none;"></div>

        <script>
          let startX = 0, startY = 0;
          let isSelecting = false;
          const selectionBox = document.getElementById('selectionBox');
          const info = document.getElementById('info');

          // 点击提示条取消
          document.querySelector('.hint').addEventListener('click', () => {
            window.close();
          });

          document.addEventListener('mousedown', (e) => {
            if (e.target.closest('.hint')) return;

            isSelecting = true;
            startX = e.screenX;
            startY = e.screenY;

            selectionBox.style.display = 'block';
            selectionBox.style.left = startX + 'px';
            selectionBox.style.top = startY + 'px';
            selectionBox.style.width = '0px';
            selectionBox.style.height = '0px';
          });

          document.addEventListener('mousemove', (e) => {
            if (!isSelecting) return;

            const currentX = e.screenX;
            const currentY = e.screenY;

            const x = Math.min(startX, currentX);
            const y = Math.min(startY, currentY);
            const width = Math.abs(currentX - startX);
            const height = Math.abs(currentY - startY);

            selectionBox.style.left = x + 'px';
            selectionBox.style.top = y + 'px';
            selectionBox.style.width = width + 'px';
            selectionBox.style.height = height + 'px';

            info.style.display = 'block';
            info.textContent = \`X: \${Math.round(x)}px  Y: \${Math.round(y)}px  宽: \${Math.round(width)}px  高: \${Math.round(height)}px\`;
          });

          document.addEventListener('mouseup', (e) => {
            if (!isSelecting) return;
            isSelecting = false;

            const endX = e.screenX;
            const endY = e.screenY;

            const x = Math.min(startX, endX);
            const y = Math.min(startY, endY);
            const width = Math.abs(endX - startX);
            const height = Math.abs(endY - startY);

            // 只有当区域足够大时才发送
            if (width > 10 && height > 10) {
              // 发送区域到父窗口
              window.opener.postMessage({
                type: 'REGION_SELECTED',
                region: { x, y, width, height }
              }, '*');
            }

            // 关闭窗口
            setTimeout(() => window.close(), 100);
          });

          // ESC 键取消
          document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
              window.close();
            }
          });
        </script>
      </body>
      </html>
    `);

    selectionWindow.document.close();
    setIsSelecting(true);
    setRegionState(null);
    setStartPoint(null);

    // 监听来自选择窗口的消息
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'REGION_SELECTED') {
        const selectedRegion = event.data.region;
        setRegionState(selectedRegion);
        onRegionSelected?.(selectedRegion);
        setCaptureRegion(selectedRegion);
        setIsSelecting(false);
        selectionWindowRef.current = null;
        window.removeEventListener('message', handleMessage);
      }
    };

    window.addEventListener('message', handleMessage);

    // 监听窗口关闭
    const checkClosed = setInterval(() => {
      if (selectionWindow.closed) {
        clearInterval(checkClosed);
        setIsSelecting(false);
        selectionWindowRef.current = null;
        window.removeEventListener('message', handleMessage);
      }
    }, 100);
  }, [onRegionSelected, setCaptureRegion]);

  return (
    <div>
      {/* Selection Button */}
      {!isSelecting && (
        <button
          onClick={startSelection}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          📐 选择截图区域
        </button>
      )}

      {/* Loading indicator */}
      {isSelecting && (
        <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            ⏳ 正在选择区域...
          </p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
            在新窗口的屏幕上拖拽选择弹幕区域
          </p>
        </div>
      )}

      {/* Region preview */}
      {region && !isSelecting && (
        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <p className="text-sm font-medium mb-2">✅ 已选择区域</p>
          <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400 mb-2">
            <span>X: {Math.round(region.x)}px</span>
            <span>Y: {Math.round(region.y)}px</span>
            <span>宽: {Math.round(region.width)}px</span>
            <span>高: {Math.round(region.height)}px</span>
          </div>
          <button
            onClick={() => {
              setRegionState(null);
              setCaptureRegion(null);
            }}
            className="text-xs text-red-500 hover:text-red-600"
          >
            清除区域
          </button>
        </div>
      )}
    </div>
  );
}
