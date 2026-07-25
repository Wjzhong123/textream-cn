import { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAppStore } from '../stores/appStore';
import { FullscreenRegionSelector } from './FullscreenRegionSelector';
import { ScreenshotTool } from './ScreenshotTool';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { api } from '../utils/api';

export function DanmakuPanel() {
  const { danmaku, isCapturing, setIsCapturing, addResponse, selectedLevel, captureRegion } = useAppStore();
  const { connect, disconnect, isConnected } = useWebSocket();
  const [loading, setLoading] = useState(false);

  const handleStartCapture = async () => {
    try {
      await api.startDanmakuCapture();
      setIsCapturing(true);
      connect();
    } catch (error) {
      console.error('Failed to start capture:', error);
      alert('启动弹幕捕获失败，请检查服务是否运行');
    }
  };

  const handleStopCapture = async () => {
    try {
      await api.stopDanmakuCapture();
      setIsCapturing(false);
      disconnect();
    } catch (error) {
      console.error('Failed to stop capture:', error);
    }
  };

  const handleGenerateResponse = async (danmakuText: string) => {
    setLoading(true);
    try {
      const response = await api.generateResponse(danmakuText, selectedLevel);
      addResponse({
        id: `${Date.now()}`,
        text: response.data.response || response.data.message,
        level: selectedLevel,
        danmaku: danmakuText,
        timestamp: Date.now(),
        copied: false,
      });
    } catch (error) {
      console.error('Failed to generate response:', error);
      alert('生成回复失败');
    } finally {
      setLoading(false);
    }
  };

  const handleScreenshotCapture = (imageData: string) => {
    console.log('Screenshot captured:', imageData.substring(0, 50) + '...');
    // 这里可以将截图发送到后端进行分析
    // 未来可以集成 OCR 识别
  };

  return (
    <div className="flex flex-col h-full border-r border-gray-200 dark:border-gray-700 relative">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <h2 className="text-xl font-bold mb-3">弹幕监控</h2>

        {/* Region Selection */}
        {!isCapturing && (
          <div className="mb-3 space-y-2">
            <FullscreenRegionSelector />
            <button
              onClick={async () => {
                try {
                  const res = await api.openRegionSelector();
                  if (res.data.status === 'ok' && res.data.region) {
                    useAppStore.getState().setCaptureRegion(res.data.region);
                  }
                } catch (err) {
                  console.error('CaptiOCR selector failed:', err);
                }
              }}
              className="w-full px-3 py-1.5 text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-800 transition"
              title="使用 CaptiOCR 原生桌面区域选择器（全屏遮罩 + 鼠标拖拽）"
            >
              🖱️ CaptiOCR 视觉选择
            </button>
          </div>
        )}

        {/* Tools */}
        {!isCapturing && (
          <div className="mb-3">
            <ScreenshotTool onCapture={handleScreenshotCapture} />
          </div>
        )}

        {/* Start/Stop Button */}
        <div className="flex gap-2">
          {!isCapturing ? (
            <button
              onClick={handleStartCapture}
              disabled={!captureRegion}
              className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
              title={!captureRegion ? '请先选择截图区域' : ''}
            >
              ▶ 开始捕获
            </button>
          ) : (
            <button
              onClick={handleStopCapture}
              className="flex-1 px-4 py-2 bg-danger-500 text-white rounded-lg hover:bg-danger-600 transition"
            >
              ⏹ 停止捕获
            </button>
          )}
        </div>

        {/* Status */}
        <div className="mt-2 flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-500' : 'bg-gray-400'}`} />
            <span>{isConnected ? '已连接' : '未连接'}</span>
          </div>
          {captureRegion && (
            <span className="text-xs text-gray-500">
              {Math.round(captureRegion.width)}×{Math.round(captureRegion.height)} px
            </span>
          )}
        </div>
      </div>

      {/* Danmaku List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {danmaku.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <p className="mb-2">暂无弹幕</p>
            <p className="text-sm">选择截图区域 → 点击"开始捕获"</p>
          </div>
        ) : (
          danmaku.map((item) => (
            <div
              key={item.id}
              className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs text-gray-500">
                  {formatDistanceToNow(item.timestamp, { addSuffix: true, locale: zhCN })}
                </span>
                {item.platform && (
                  <span className="text-xs px-2 py-1 bg-primary-100 dark:bg-primary-900 rounded">
                    {item.platform}
                  </span>
                )}
              </div>
              <p className="text-sm mb-2">{item.text}</p>
              <button
                onClick={() => handleGenerateResponse(item.text)}
                disabled={loading}
                className="w-full px-3 py-1.5 text-sm bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-800 transition disabled:opacity-50"
              >
                💬 生成回复
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
