import { useEffect, useState } from 'react';

interface ScreenshotToolProps {
  onCapture?: (imageData: string) => void;
}

export function ScreenshotTool({ onCapture }: ScreenshotToolProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isVisible) {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
      script.async = true;
      script.onerror = () => setError('html2canvas 加载失败');
      document.body.appendChild(script);
      return () => { document.body.removeChild(script); };
    }
  }, [isVisible]);

  useEffect(() => {
    (window as any).html2canvas = (window as any).html2canvas || null;
  }, []);

  const handleCapture = async () => {
    try {
      setError(null);
      const html2canvas = (window as any).html2canvas;
      if (typeof html2canvas === 'function') {
        const canvas = await html2canvas(document.body, { useCORS: true, allowTaint: true, logging: false });
        const imageData = canvas.toDataURL('image/png');
        setScreenshot(imageData);
        onCapture?.(imageData);
      } else {
        throw new Error('html2canvas not loaded');
      }
    } catch (err) {
      setError('截图失败: ' + (err instanceof Error ? err.message : '未知错误'));
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
        className="flex items-center gap-2 px-4 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/5 rounded-full border border-border-subtle transition-all duration-150"
      >
        📸 截图
      </button>
    );
  }

  return (
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="modal-content w-full max-w-2xl max-h-[85vh] overflow-auto fade-in">
        {/* Header */}
        <div className="sticky top-0 bg-bg-secondary border-b border-border-subtle px-6 py-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">📸 截图工具</h3>
          <button
            onClick={handleClear}
            className="w-7 h-7 flex items-center justify-center rounded-full text-text-muted hover:text-text-primary hover:bg-white/10 transition text-sm"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {error && (
            <div className="error-item error-error text-xs">
              <span>✕</span> {error}
            </div>
          )}

          <button
            onClick={handleCapture}
            className="w-full px-4 py-3 text-xs btn-accent hover:btn-accent-hover flex items-center justify-center gap-2"
          >
            📸 捕获屏幕
          </button>

          {screenshot && (
            <div className="glass-card overflow-hidden">
              <img src={screenshot} alt="截图预览" className="w-full" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}