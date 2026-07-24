import { useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAppStore } from '../stores/appStore';

export function useWebSocket() {
  const socketRef = useRef<Socket | null>(null);
  const { addDanmaku, setConnected, serverUrl } = useAppStore();

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    const socket = io(serverUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    });

    socket.on('danmaku', (data: { text: string; timestamp: number; platform?: string }) => {
      addDanmaku({
        id: `${Date.now()}-${Math.random()}`,
        text: data.text,
        timestamp: data.timestamp,
        platform: data.platform,
      });
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
    });

    socketRef.current = socket;
  }, [serverUrl, addDanmaku, setConnected]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setConnected(false);
    }
  }, [setConnected]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect, isConnected: socketRef.current?.connected ?? false };
}
