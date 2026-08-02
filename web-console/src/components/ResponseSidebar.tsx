import { useAppStore } from '../stores/appStore';
import { QuickResponses } from './QuickResponses';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const LEVELS = [
  { key: 'simple' as const, label: '简洁', icon: '○' },
  { key: 'deep' as const, label: '深入', icon: '◎' },
  { key: 'humorous' as const, label: '幽默', icon: '◐' },
];

interface ResponseSidebarProps {
  compact?: boolean;
}

export function ResponseSidebar({ compact }: ResponseSidebarProps) {
  const { responses, selectedLevel, setSelectedLevel, clearResponses } = useAppStore();

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── 紧凑标题栏 ── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
        <h2 className="text-sm font-semibold text-text-primary">救场话术</h2>
        <div className="flex-1" />
        <div className="flex gap-1">
          {LEVELS.map((level) => (
            <button
              key={level.key}
              onClick={() => setSelectedLevel(level.key)}
              className={`px-2.5 py-1 text-[11px] rounded-full transition-all ${
                selectedLevel === level.key
                  ? 'pill-active'
                  : 'pill-inactive hover:text-text-primary'
              }`}
            >
              {level.icon} {level.label}
            </button>
          ))}
        </div>
        <button
          onClick={clearResponses}
          className="text-[11px] text-text-muted hover:text-text-secondary px-2 py-1 rounded-full hover:bg-white/5"
        >
          清空
        </button>
      </div>

      {/* ── 话术列表 ── */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {responses.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <p className="text-sm mb-1">暂无救场话术</p>
            <p className="text-xs">在弹幕中点击 💬 生成</p>
          </div>
        ) : (
          responses.map((response) => (
            <div key={response.id} className="glass-card px-3 py-2.5 fade-in">
              {/* 原弹幕 + 话术等级 + 时间 */}
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                  {LEVELS.find(l => l.key === response.level)?.label}
                </span>
                <span className="text-[10px] text-text-muted">
                  {formatDistanceToNow(response.timestamp, { addSuffix: true, locale: zhCN })}
                </span>
              </div>
              <p className="text-[11px] text-text-muted mb-1 truncate">原弹幕: {response.danmaku}</p>
              <p className="text-sm text-text-primary leading-relaxed selectable-text mb-2">{response.text}</p>
              <button
                onClick={() => handleCopy(response.text)}
                className="text-[11px] text-accent hover:text-accent/80 transition"
              >
                📋 复制
              </button>
            </div>
          ))
        )}
      </div>

      <QuickResponses />
    </div>
  );
}