import { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAppStore } from '../stores/appStore';
import { ScreenshotTool } from './ScreenshotTool';
import { api } from '../utils/api';

interface ErrorEntry {
  time: number;
  module: string;
  level: string;
  message: string;
}

function timeAgo(ts: number): string {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return `${seconds}秒前`;
  const mins = Math.floor(seconds / 60);
  return `${mins}分钟前`;
}

function formatErrorTime(unixTs: number): string {
  const d = new Date(unixTs * 1000);
  const hh = d.getHours().toString().padStart(2, '0');
  const mm = d.getMinutes().toString().padStart(2, '0');
  const ss = d.getSeconds().toString().padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

export function DanmakuPanel() {
  const { danmaku, isCapturing, setIsCapturing, addResponse, selectedLevel, captureRegion } = useAppStore();
  const { connect, disconnect, isConnected } = useWebSocket();
  const [loading, setLoading] = useState(false);
  const [selectorLoading, setSelectorLoading] = useState(false);
  const [errorPanelOpen, setErrorPanelOpen] = useState(true);
  const [errors, setErrors] = useState<ErrorEntry[]>([]);
  const errorsRef = useRef(errors);
  errorsRef.current = errors;

  // 轮询错误总线（每 3 秒）
  useEffect(() => {
    const config = JSON.parse(localStorage.getItem('textream_config') || '{}');
    const baseUrl = config.url || 'http://localhost:9123';

    const fetchErrors = async () => {
      try {
        const res = await fetch(`${baseUrl}/api/errors`);
        const data = await res.json();
        if (data.errors && Array.isArray(data.errors)) {
          setErrors(data.errors as ErrorEntry[]);
        }
      } catch {
        // 后端离线时不更新
      }
    };

    fetchErrors();
    const interval = setInterval(fetchErrors, 3000);
    return () => clearInterval(interval);
  }, []);

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
    } catch {
      console.error('Failed to generate response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── 标题栏 ── */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <h2 className="text-sm font-semibold text-text-primary">弹幕监控</h2>
        <div className="flex items-center gap-2.5">
          {isCapturing && (
            <div className="flex items-center gap-1.5">
              <span className="status-dot status-dot-online" />
              <span className="text-xs text-text-muted">直播中 · {danmaku.length} 条</span>
            </div>
          )}
          {captureRegion && (
            <span className="text-[11px] text-text-muted font-mono">
              {Math.round(captureRegion.width)}×{Math.round(captureRegion.height)}
            </span>
          )}
        </div>
      </div>

      {/* ── 控制栏 ── */}
      <div className="flex items-center gap-2 px-5 py-3 border-b border-border-subtle">
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
                } catch {
                  console.error('Selector failed');
                } finally {
                  setSelectorLoading(false);
                }
              }}
              disabled={selectorLoading}
              className="flex items-center gap-2 px-4 py-2 text-xs text-text-secondary hover:text-text-primary hover:bg-white/5 rounded-full border border-border-subtle transition-all duration-150 disabled:opacity-50"
            >
              {selectorLoading ? '⏳' : '📐'} 选择区域
            </button>
            <ScreenshotTool onCapture={() => {}} />
          </>
        )}

        <div className="ml-auto">
          {!isCapturing ? (
            <button
              onClick={handleStartCapture}
              disabled={!captureRegion}
              className="btn-accent px-5 py-2 text-xs disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ▶ 开始捕获
            </button>
          ) : (
            <button
              onClick={handleStopCapture}
              className="flex items-center gap-2 px-5 py-2 text-xs text-danger bg-danger-bg rounded-full border border-danger/20 hover:bg-danger/20 transition-all duration-150"
            >
              ⏹ 停止捕获
            </button>
          )}
        </div>
      </div>

      {/* ── 弹幕列表 ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1.5">
        {danmaku.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <p className="text-sm mb-1">暂无弹幕</p>
            <p className="text-xs">选择截图区域 → 点击开始捕获</p>
          </div>
        ) : (
          danmaku.map((item) => (
            <div
              key={item.id}
              className="danmaku-item group hover:danmaku-item-hover fade-in"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <span className="text-[11px] text-text-muted shrink-0 font-mono">
                  {timeAgo(item.timestamp)}
                </span>
                <span className="text-xs text-text-secondary truncate selectable-text">
                  {item.text}
                </span>
              </div>
              <button
                onClick={() => handleGenerateResponse(item.text)}
                disabled={loading}
                className="shrink-0 w-7 h-7 flex items-center justify-center rounded-full text-xs text-text-muted hover:text-accent hover:bg-accent/10 transition-all duration-150 opacity-0 group-hover:opacity-100 disabled:opacity-30"
                title="生成回复"
              >
                💬
              </button>
            </div>
          ))
        )}
      </div>

      {/* ── 错误面板 ── */}
      {errors.length > 0 && (
        <div className="border-t border-border-subtle">
          <button
            onClick={() => setErrorPanelOpen(!errorPanelOpen)}
            className="flex items-center justify-between w-full px-5 py-2.5 text-xs text-text-muted hover:text-text-secondary transition"
          >
            <span>错误面板 ({errors.length})</span>
            <span className={`transform transition-transform ${errorPanelOpen ? 'rotate-180' : ''}`}>
              ▼
            </span>
          </button>
          {errorPanelOpen && (
            <div className="px-4 pb-3 space-y-1 max-h-[140px] overflow-y-auto">
              {errors.map((err, i) => (
                <div key={i} className={`error-item ${err.level === 'error' ? 'error-error' : 'error-warn'}`}>
                  <span>{err.level === 'error' ? '✕' : '⚠'}</span>
                  <span className="truncate">{err.module}: {err.message}</span>
                  <span className="ml-auto shrink-0 text-[10px] opacity-60">{formatErrorTime(err.time)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}