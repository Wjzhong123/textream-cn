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

interface RegionSelectorProps {
  onRegionSelected?: (region: Region) => void;
}

/**
 * 区域选择器组件
 * 提供可视化区域框选功能
 */
export function RegionSelector({ onRegionSelected }: RegionSelectorProps) {
  const { setCaptureRegion } = useAppStore();
  const [isSelecting, setIsSelecting] = useState(false);
  const [region, setRegionState] = useState<Region | null>(null);
  const [startPoint, setStartPoint] = useState<Point | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const startSelection = useCallback(() => {
    setStartPoint(null);
    setRegionState(null);
    setIsSelecting(true);
  }, []);

  const handleMouseDown = useCallback((e: MouseEvent) => {
    const rect = overlayRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setStartPoint({ x, y });
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isSelecting || !startPoint || !overlayRef.current) return;

    const rect = overlayRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const x = Math.min(startPoint.x, currentX);
    const y = Math.min(startPoint.y, currentY);
    const width = Math.abs(currentX - startPoint.x);
    const height = Math.abs(currentY - startPoint.y);

    setRegionState({ x, y, width, height });
  }, [isSelecting, startPoint]);

  const handleMouseUp = useCallback(() => {
    if (isSelecting && region) {
      onRegionSelected?.(region);
      setCaptureRegion(region);
    }
    setIsSelecting(false);
  }, [isSelecting, region, onRegionSelected, setCaptureRegion]);

  const cancelSelection = useCallback(() => {
    setIsSelecting(false);
    setStartPoint(null);
    setRegionState(null);
  }, []);

  // 全局鼠标事件处理
  useEffect(() => {
    if (!isSelecting) return;

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isSelecting, handleMouseMove, handleMouseUp]);

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

  return (
    <div className="relative">
      {/* Selection Button */}
      {!isSelecting && (
        <button
          onClick={startSelection}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          📐 选择截图区域
        </button>
      )}

      {/* Overlay for selection */}
      {isSelecting && (
        <div className="fixed inset-0 z-50 bg-blue-500/10">
          <div className="absolute inset-0 border-4 border-blue-500" />
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg">
            <p className="text-sm font-medium">拖动鼠标选择弹幕区域</p>
            <p className="text-xs mt-1 opacity-90">按 ESC 取消</p>
          </div>
          <div
            ref={overlayRef}
            className="w-full h-full cursor-crosshair"
            onMouseDown={(e) => handleMouseDown(e.nativeEvent)}
          />
        </div>
      )}

      {/* Region preview */}
      {region && !isSelecting && (
        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <p className="text-sm font-medium mb-2">已选择区域</p>
          <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400">
            <span>X: {Math.round(region.x)}px</span>
            <span>Y: {Math.round(region.y)}px</span>
            <span>宽: {Math.round(region.width)}px</span>
            <span>高: {Math.round(region.height)}px</span>
          </div>
          <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden relative">
            <div
              className="absolute h-full bg-blue-500/50 border-r border-blue-500"
              style={{
                left: `${(region.x / 1126) * 100}%`,
                width: `${(region.width / 1126) * 100}%`,
              }}
            />
          </div>
          <button
            onClick={cancelSelection}
            className="mt-2 text-xs text-red-500 hover:text-red-600"
          >
            清除区域
          </button>
        </div>
      )}
    </div>
  );
}
