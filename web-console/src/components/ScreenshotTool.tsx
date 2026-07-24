import { useEffect, useState } from 'react';

interface ScreenshotToolProps {
  onCapture?: (imageData: string) => void;
}

/**
 * 截图工具组件
 * 提供屏幕截图功能（使用 html2canvas 或浏览器原生 API）
 */
export function ScreenshotTool({ onCapture }: ScreenshotToolProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 加载 html2canvas 库
  useEffect(() => {
    if (isVisible) {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
      script.async = true;
      script.onload = () => console.log('html2canvas loaded');
      script.onerror = () => setError('Failed to load html2canvas');
      document.body.appendChild(script);

      return () => {
        document.body.removeChild(script);
      };
    }
  }, [isVisible]);

  // Extend Window interface
  useEffect(() => {
    (window as any).html2canvas = (window as any).html2canvas || null;
  }, []);

  // Declare html2canvas on window
  useEffect(() => {
    if (!(window as any).html2canvas) {
      (window as any).html2canvas = null;
    }
  }, []);

  const handleCapture = async () => {
    try {
      setError(null);

      // 检查是否有 html2canvas
      const html2canvas = (window as any).html2canvas;
      if (typeof html2canvas === 'function') {
        // 捕获整个窗口
        const canvas = await html2canvas(document.body, {
          useCORS: true,
          allowTaint: true,
          logging: false,
        });

        const imageData = canvas.toDataURL('image/png');
        setScreenshot(imageData);
        onCapture?.(imageData);
      } else {
        throw new Error('html2canvas not loaded');
      }
    } catch (err) {
      console.error('Screenshot failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to capture screenshot');
    }
  };

  const handleClear = () => {
    setScreenshot(null);
    setError(null);
    setIsVisible(false);
  };

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition"
      >
        📸 截图
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-auto shadow-2xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">截图工具</h3>
          <button
            onClick={handleClear}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <button
            onClick={handleCapture}
            className="w-full px-4 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition font-medium"
          >
            📸 捕获屏幕
          </button>

          {screenshot && (
            <div className="space-y-2">
              <p className="text-sm font-medium">截图预览</p>
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-auto max-h-[50vh]">
                <img
                  src={screenshot}
                  alt="Screenshot"
                  className="w-full h-auto"
                />
              </div>
              <div className="flex gap-2">
                <a
                  href={screenshot}
                  download={`screenshot-${Date.now()}.png`}
                  className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition text-center"
                >
                  ⬇️ 下载
                </a>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(screenshot);
                    alert('已复制到剪贴板');
                  }}
                  className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
                >
                  📋 复制 Base64
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
