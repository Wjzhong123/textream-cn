import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../stores/appStore';

const WS_PATH = '/ws/danmaku';

export function useWebSocket() {
  const socketRef = useRef<WebSocket | null>(null);
  const { addDanmaku, setConnected, serverUrl } = useAppStore();

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