interface DividerWithFoldProps {
  collapsed: boolean;
  onToggle: () => void;
  onMouseDown: (e: React.MouseEvent) => void;
  /** 按钮位置：'left' 在分割线左侧，'right' 在分割线右侧 */
  buttonPosition: 'left' | 'right';
  /** 折叠后是否禁用拖拽 */
  disableDragWhenCollapsed?: boolean;
  expandTitle: string;
  collapseTitle: string;
}

export function DividerWithFold({
  collapsed,
  onToggle,
  onMouseDown,
  buttonPosition,
  disableDragWhenCollapsed = true,
  expandTitle,
  collapseTitle,
}: DividerWithFoldProps) {
  return (
    <div className="relative flex items-center" style={{ width: 8 }}>
      <div
        className="divider h-full"
        style={{ cursor: disableDragWhenCollapsed && collapsed ? 'default' : 'col-resize' }}
        onMouseDown={disableDragWhenCollapsed && collapsed ? undefined : onMouseDown}
      />
      <button
        onClick={onToggle}
        title={collapsed ? expandTitle : collapseTitle}
        className={`
          absolute top-1/2 -translate-y-1/2 z-50
          w-6 h-6 rounded-full bg-bg-secondary border border-border-subtle
          flex items-center justify-center
          text-text-muted hover:text-accent hover:border-accent/40
          transition-all duration-150 shadow-md text-[10px]
          ${buttonPosition === 'right' ? 'left-full ml-1.5' : '-left-3'}
        `}
      >
        {collapsed
          ? (buttonPosition === 'right' ? '▶' : '◀')
          : (buttonPosition === 'right' ? '◀' : '▶')
        }
      </button>
    </div>
  );
}