import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../utils/api';
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

/**
 * 区域选择器 Hook
 * 提供屏幕区域框选功能
 */
export function useRegionSelector() {
  const { setCaptureRegion } = useAppStore();
  const [isSelecting, setIsSelecting] = useState(false);
  const [region, setRegionState] = useState<Region | null>(null);
  const [startPoint, setStartPoint] = useState<Point | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const startSelection = useCallback((e: React.MouseEvent) => {
    const rect = overlayRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setStartPoint({ x, y });
    setIsSelecting(true);
    setRegionState(null);
  }, []);

  const updateSelection = useCallback((e: React.MouseEvent) => {
    if (!isSelecting || !startPoint || !overlayRef.current) return;

    const rect = overlayRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const x = Math.min(startPoint.x, currentX);
    const y = Math.min(startPoint.y, currentY);
    const width = Math.abs(currentX - startPoint.x);
    const height = Math.abs(currentY - startPoint.y);

    // 只更新预览，不发送 API 请求
    setRegionState({ x, y, width, height });
  }, [isSelecting, startPoint]);

  const endSelection = useCallback(async () => {
    if (!region) {
      // 没有有效区域，取消选择
      setIsSelecting(false);
      setStartPoint(null);
      setRegionState(null);
      return;
    }

    try {
      // 发送区域到后端并更新本地状态
      await api.setCaptureRegion(region);
      setCaptureRegion(region);
      console.log('Capture region set:', region);
    } catch (error) {
      console.error('Failed to set capture region:', error);
    }

    // 关闭选择模式
    setIsSelecting(false);
    setStartPoint(null);
    setRegionState(null);
  }, [region, setCaptureRegion]);

  const cancelSelection = useCallback(() => {
    setIsSelecting(false);
    setStartPoint(null);
    setRegionState(null);
  }, []);

  // 全局鼠标事件处理
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isSelecting && overlayRef.current) {
        const fakeEvent = {
          clientX: e.clientX,
          clientY: e.clientY,
        } as React.MouseEvent;
        updateSelection(fakeEvent);
      }
    };

    const handleMouseUp = () => {
      if (isSelecting) {
        endSelection();
      }
    };

    if (isSelecting) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isSelecting, updateSelection, endSelection]);

  // ESC 键取消选择
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isSelecting) {
        cancelSelection();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isSelecting, cancelSelection]);

  return {
    overlayRef,
    isSelecting,
    region,
    startSelection,
    updateSelection,
    cancelSelection,
  };
}
