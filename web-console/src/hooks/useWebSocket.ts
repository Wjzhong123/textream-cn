import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../stores/appStore';

const WS_PATH = '/ws/danmaku';

// 前端兜底去重：与最近 N 条弹幕做相似度比较，相似度过高视为同一条。
// 后端已有相似度去重，这里防止后端漏网 + 双端保障。
function isDuplicateText(text: string, recent: string[], threshold = 0.85): boolean {
  for (const r of recent) {
    let sim = 0;
    if (text === r) {
      sim = 1;
    } else {
      const a = text;
      const b = r;
      const longer = Math.max(a.length, b.length);
      if (longer === 0) continue;
      // 简单字符级相似度：最长公共子序列的近似（按位置逐字符比较）
      let match = 0;
      const len = Math.min(a.length, b.length);
      for (let i = 0; i < len; i++) {
        if (a[i] === b[i]) match++;
      }
      sim = match / longer;
    }
    if (sim >= threshold) return true;
  }
  return false;
}

export function useWebSocket() {
  const socketRef = useRef<WebSocket | null>(null);
  const { addDanmaku, setConnected, serverUrl } = useAppStore();
  const recentTextsRef = useRef<string[]>([]);

  const connect = useCallback(() => {
    // 关闭旧连接（防止 serverUrl 变化时泄漏）
    if (socketRef.current) {
      socketRef.current.onclose = null; // 阻止自动重连
      socketRef.current.close();
      socketRef.current = null;
    }

    // 将 http:// 协议转换为 ws:// 协议
    const wsBase = serverUrl.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}${WS_PATH}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      // 自动重连
      setTimeout(() => {
        if (socketRef.current?.readyState === WebSocket.CLOSED) {
          connect();
        }
      }, 3000);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.text) {
          // 前端兜底去重：与最近 20 条弹幕比较，相似就跳过
          if (isDuplicateText(data.text, recentTextsRef.current)) {
            console.log('[dedup] 忽略重复弹幕:', data.text);
            return;
          }
          recentTextsRef.current = [data.text, ...recentTextsRef.current].slice(0, 20);
          addDanmaku({
            id: `${Date.now()}-${Math.random()}`,
            text: data.text,
            timestamp: data.timestamp || Date.now(),
            platform: data.platform,
          });
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    socketRef.current = socket;
  }, [serverUrl, addDanmaku, setConnected]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onclose = null; // 阻止自动重连
      socketRef.current.close();
      socketRef.current = null;
      setConnected(false);
    }
  }, [setConnected]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect, isConnected: socketRef.current?.readyState === WebSocket.OPEN ?? false };
}