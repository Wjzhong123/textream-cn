import { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAppStore } from '../stores/appStore';
import { api } from '../utils/api';

export function DanmakuPanel() {
  const { danmaku, isCapturing, setIsCapturing, addResponse, selectedLevel, captureRegion, responses } = useAppStore();
  const { connect, disconnect } = useWebSocket();
  const [loading, setLoading] = useState<string | null>(null);
  const [selectorLoading, setSelectorLoading] = useState(false);

  const handleStartCapture = async () => {
    try {
      await api.startDanmakuCapture();
      setIsCapturing(true);
      connect();
    } catch {
      console.error('Failed to start capture');
    }
  };

  const handleStopCapture = async () => {
    try {
      await api.stopDanmakuCapture();
      setIsCapturing(false);
      disconnect();
    } catch { /* ignore */ }
  };

  const handleGenerateResponse = async (danmakuId: string, danmakuText: string) => {
    setLoading(danmakuId);
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
    } catch {
      console.error('Failed to generate response');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── 紧凑标题栏 ── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
        <h2 className="text-sm font-semibold text-text-primary shrink-0">弹幕监控</h2>
        <div className="flex items-center gap-1.5 text-xs">
          <span className={`status-dot ${isCapturing ? 'status-dot-online' : 'bg-text-muted'}`} />
          <span className="text-text-muted">{isCapturing ? '捕获中' : '未捕获'}</span>
        </div>
        <div className="flex-1" />
        {!isCapturing && (
          <>
            <button
              onClick={async () => {
                setSelectorLoading(true);
                try {
                  const res = await api.openRegionSelector();
                  if (res.data.status === 'ok' && res.data.region) {
                    useAppStore.getState().setCaptureRegion(res.data.region);
                  }
                } catch (err) {
                  console.error('CaptiOCR selector failed:', err);
                } finally {
                  setSelectorLoading(false);
                }
              }}
              disabled={selectorLoading}
              className="px-3 py-1.5 text-xs btn-accent hover:btn-accent-hover disabled:opacity-50 shrink-0"
              title="选择弹幕截图区域"
            >
              {selectorLoading ? '⏳' : '📐 区域'}
            </button>
            <button
              onClick={handleStartCapture}
              disabled={!captureRegion}
              className="px-3 py-1.5 text-xs btn-accent hover:btn-accent-hover disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
            >
              ▶ 开始
            </button>
          </>
        )}
        {isCapturing && (
          <button
            onClick={handleStopCapture}
            className="px-3 py-1.5 text-xs text-danger bg-danger-bg rounded-full border border-danger/20 hover:bg-danger/20 shrink-0"
          >
            ⏹ 停止
          </button>
        )}
        {captureRegion && (
          <span className="text-[10px] text-text-muted font-mono shrink-0">
            {Math.round(captureRegion.width)}×{Math.round(captureRegion.height)}
          </span>
        )}
        {captureRegion && !isCapturing && (
          <button
            onClick={() => useAppStore.getState().setCaptureRegion(null)}
            className="text-[10px] text-text-muted hover:text-danger shrink-0"
          >
            ✕
          </button>
        )}
      </div>

      {/* ── 弹幕列表 ── */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {danmaku.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <p className="text-sm mb-1">暂无弹幕</p>
            <p className="text-xs">📐 选择区域 → ▶ 开始捕获</p>
          </div>
        ) : (
          danmaku.map((item) => (
            <div
              key={item.id}
              className="glass-card px-3 py-2 hover:glass-card-hover transition"
            >
              <div className="flex items-start gap-2">
                <span className="text-[10px] text-text-muted mt-0.5 shrink-0">
                  {new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <p className="text-xs text-text-primary flex-1 leading-relaxed selectable-text">{item.text}</p>
                <button
                  onClick={() => handleGenerateResponse(item.id, item.text)}
                  disabled={loading === item.id}
                  className="px-2 py-1 text-[11px] btn-accent hover:btn-accent-hover disabled:opacity-50 shrink-0 rounded-full"
                  title="生成回复话术"
                >
                  {loading === item.id ? '⏳' : '💬'}
                </button>
              </div>
              {/* 已生成的回复 */}
              {responses.filter(r => r.danmaku === item.text).slice(-1).map(r => (
                <div key={r.id} className="mt-1.5 ml-8 pl-3 border-l-2 border-accent/30">
                  <p className="text-xs text-accent leading-relaxed">{r.text}</p>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}