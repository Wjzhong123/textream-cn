import { useAppStore } from '../stores/appStore';
import { QuickResponses } from './QuickResponses';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

const LEVELS = [
  { key: 'simple' as const, label: '简洁', icon: '○' },
  { key: 'deep' as const, label: '深入', icon: '◎' },
  { key: 'humorous' as const, label: '幽默', icon: '◐' },
];

export function ResponseSidebar() {
  const { responses, selectedLevel, setSelectedLevel, clearResponses } = useAppStore();

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ── 标题栏 ── */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <h2 className="text-sm font-semibold text-text-primary">救场话术</h2>
        <button
          onClick={clearResponses}
          className="text-xs text-text-muted hover:text-text-secondary transition px-2 py-1 rounded-full hover:bg-white/5"
        >
          清空
        </button>
      </div>

      {/* ── 话术等级选择器 ── */}
      <div className="flex gap-1.5 px-5 py-3 border-b border-border-subtle">
        {LEVELS.map((level) => (
          <button
            key={level.key}
            onClick={() => setSelectedLevel(level.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded-full transition-all duration-150 ${
              selectedLevel === level.key
                ? 'pill-active'
                : 'pill-inactive hover:text-text-primary hover:bg-white/5'
            }`}
          >
            <span className="opacity-60">{level.icon}</span>
            {level.label}
          </button>
        ))}
      </div>

      {/* ── 话术列表 ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {responses.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <p className="text-sm mb-1">暂无救场话术</p>
            <p className="text-xs">在弹幕监控中点击 💬 生成回复</p>
          </div>
        ) : (
          responses.map((response) => (
            <div
              key={response.id}
              className="glass-card p-4 fade-in"
            >
              {/* 原弹幕 */}
              <div className="mb-3 pb-3 border-b border-border-subtle">
                <p className="text-[11px] text-text-muted mb-1">原弹幕</p>
                <p className="text-xs text-text-secondary selectable-text">{response.danmaku}</p>
              </div>

              {/* 生成的话术 */}
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                    {LEVELS.find(l => l.key === response.level)?.label}
                  </span>
                  <span className="text-[11px] text-text-muted">
                    {formatDistanceToNow(response.timestamp, { addSuffix: true, locale: zhCN })}
                  </span>
                </div>
                <p className="text-sm text-text-primary leading-relaxed selectable-text">{response.text}</p>
              </div>

              {/* 复制按钮 */}
              <button
                onClick={() => handleCopy(response.text)}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs btn-accent hover:btn-accent-hover"
              >
                <span>📋</span> 复制话术
              </button>
            </div>
          ))
        )}
      </div>

      {/* 快捷回复 */}
      <QuickResponses />
    </div>
  );
}