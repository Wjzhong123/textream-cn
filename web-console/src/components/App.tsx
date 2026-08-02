import { useState, useEffect } from 'react';
import { DanmakuPanel } from './DanmakuPanel';
import { ResponseSidebar } from './ResponseSidebar';
import { MemoryManager } from './MemoryManager';
import { KnowledgeBase } from './KnowledgeBase';
import { SettingsModal } from './SettingsModal';

type View = 'danmaku' | 'response' | 'memory' | 'knowledge';

interface ServerConfig {
  url: string;
  llmProvider: string;
  llmBaseUrl: string;
  llmApiKey: string;
  llmModel: string;
  useOneMemory: boolean;
  oneRoot: string;
  oneApiKey: string;
}

const NAV_ITEMS: { key: View; label: string; icon: string }[] = [
  { key: 'danmaku', label: '弹幕监控', icon: '◉' },
  { key: 'response', label: '救场话术', icon: '◇' },
  { key: 'memory', label: '记忆管理', icon: '⊞' },
  { key: 'knowledge', label: '知识库', icon: '⊡' },
];

export function App() {
  const [connected, setConnected] = useState(false);
  const [currentView, setCurrentView] = useState<View>('danmaku');
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState<ServerConfig>(() => {
    const saved = localStorage.getItem('textream_config');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch { /* ignore */ }
    }
    return {
      url: 'http://localhost:9123',
      llmProvider: 'siliconflow',
      llmBaseUrl: 'https://api.siliconflow.cn/v1',
      llmApiKey: '',
      llmModel: 'Qwen/Qwen2.5-72B-Instruct',
      useOneMemory: false,
      oneRoot: '/Users/mac/Desktop/oh-agent-panel',
      oneApiKey: '',
    };
  });

  const checkHealth = async () => {
    try {
      const response = await fetch(`${config.url}/api/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-cache',
      });
      if (response.ok) {
        const data = await response.json();
        setConnected(data.status === 'ok');
        return;
      }
    } catch { /* offline */ }
    setConnected(false);
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, [config.url]);

  const handleSaveConfig = async (newConfig: ServerConfig) => {
    setConfig(newConfig);
    localStorage.setItem('textream_config', JSON.stringify(newConfig));
    setShowSettings(false);
    await checkHealth();
    try {
      await fetch(`${config.url}/api/models/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: newConfig.llmProvider,
          base_url: newConfig.llmBaseUrl,
          api_key: newConfig.llmApiKey,
          model: newConfig.llmModel,
        }),
      });
    } catch { /* sync best-effort */ }
  };

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      {/* ── 侧边栏 ── */}
      <nav className="w-56 flex flex-col border-r border-border-subtle bg-bg-secondary/50">
        {/* Logo 区域 */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent text-sm font-semibold">
              T
            </div>
            <div>
              <h1 className="text-sm font-semibold text-text-primary">Textream</h1>
              <p className="text-[11px] text-text-muted">直播 AI 军师</p>
            </div>
          </div>
        </div>

        {/* 导航项 */}
        <div className="flex-1 px-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => setCurrentView(item.key)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm rounded-full transition-all duration-150 ${
                currentView === item.key
                  ? 'bg-accent/15 text-accent border border-accent/25 shadow-[0_0_16px_rgba(192,132,252,0.1)]'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/5 border border-transparent'
              }`}
            >
              <span className="text-base opacity-70">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        {/* 底部状态 */}
        <div className="px-4 pb-4 pt-3 border-t border-border-subtle space-y-2.5">
          {/* 设置按钮 */}
          <button
            onClick={() => setShowSettings(true)}
            className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-white/5 rounded-full transition-all duration-150"
          >
            <span className="text-base opacity-50">⚙</span>
            <span>设置</span>
          </button>

          {/* 连接状态 */}
          <div className="flex items-center gap-2.5 px-4">
            <span className={`status-dot ${connected ? 'status-dot-online' : 'bg-text-muted'}`} />
            <span className="text-xs text-text-muted">
              {connected ? '服务已连接' : '服务未连接'}
            </span>
          </div>

          <div className="text-[11px] text-text-muted px-4 truncate">
            {config.url.replace('http://', '')}
          </div>
        </div>
      </nav>

      {/* ── 主内容区 ── */}
      <main className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-hidden">
          {currentView === 'danmaku' && <DanmakuPanel />}
          {currentView === 'response' && <ResponseSidebar />}
          {currentView === 'memory' && <MemoryManager />}
          {currentView === 'knowledge' && <KnowledgeBase />}
        </div>

        {/* 弹幕模式右侧面板 */}
        {currentView === 'danmaku' && (
          <aside className="w-[380px] border-l border-border-subtle bg-bg-primary">
            <ResponseSidebar />
          </aside>
        )}
      </main>

      {/* 设置弹窗 */}
      {showSettings && (
        <SettingsModal
          config={config}
          onSave={handleSaveConfig}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}