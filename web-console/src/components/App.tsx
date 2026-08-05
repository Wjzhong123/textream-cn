import { useState, useEffect, useRef } from 'react';
import { DividerWithFold } from './DividerWithFold';
import { DanmakuPanel } from './DanmakuPanel';
import { ResponseSidebar } from './ResponseSidebar';
import { MemoryManager } from './MemoryManager';
import { KnowledgeBase } from './KnowledgeBase';
import { SettingsModal } from './SettingsModal';

type View = 'danmaku' | 'response' | 'memory' | 'knowledge';
type Theme = 'dark' | 'light';
type FontSize = 'small' | 'medium' | 'large';

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

function loadFromStorage<T>(key: string, fallback: T, useSession = false): T {
  try {
    const storage = useSession ? sessionStorage : localStorage;
    const val = storage.getItem(key);
    return val ? JSON.parse(val) : fallback;
  } catch { return fallback; }
}

function saveToStorage(key: string, value: unknown, useSession = false): void {
  try {
    const storage = useSession ? sessionStorage : localStorage;
    storage.setItem(key, JSON.stringify(value));
  } catch { /* quota exceeded, ignore */ }
}

export function App() {
  const [connected, setConnected] = useState(false);
  const [currentView, setCurrentView] = useState<View>('danmaku');
  const [showSettings, setShowSettings] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => loadFromStorage('sidebar_collapsed', false));
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => loadFromStorage('theme', 'dark'));
  const [fontSize, setFontSize] = useState<FontSize>(() => loadFromStorage('font_size', 'medium'));
  const [sidebarWidth, setSidebarWidth] = useState(224);
  const [rightWidth, setRightWidth] = useState(280);
  const [config, setConfig] = useState<ServerConfig>(() => {
    // 非敏感配置持久化到 localStorage
    const saved = localStorage.getItem('textream_config');
    // API Key 放 sessionStorage（关闭页面即清除）
    const savedApiKey = sessionStorage.getItem('textream_llm_api_key') || '';
    const savedOneApiKey = sessionStorage.getItem('textream_one_api_key') || '';
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        parsed.llmApiKey = savedApiKey || parsed.llmApiKey || '';
        parsed.oneApiKey = savedOneApiKey || parsed.oneApiKey || '';
        return parsed;
      } catch { /* ignore */ }
    }
    return {
      url: 'http://localhost:9123',
      llmProvider: 'siliconflow',
      llmBaseUrl: 'https://api.siliconflow.cn/v1',
      llmApiKey: savedApiKey || '',
      llmModel: 'Qwen/Qwen2.5-72B-Instruct',
      useOneMemory: false,
      oneRoot: '/Users/mac/Desktop/oh-agent-panel',
      oneApiKey: savedOneApiKey || '',
    };
  });

  // ── 主题 / 字体 同步到 DOM ──
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', JSON.stringify(theme));
  }, [theme]);
  useEffect(() => {
    document.documentElement.setAttribute('data-font-size', fontSize);
    localStorage.setItem('font_size', JSON.stringify(fontSize));
  }, [fontSize]);
  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', JSON.stringify(sidebarCollapsed));
  }, [sidebarCollapsed]);

  // ── 健康检查 ──
  const checkHealth = async () => {
    try {
      const response = await fetch(`${config.url}/api/health`, {
        method: 'GET', headers: { 'Content-Type': 'application/json' }, cache: 'no-cache',
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
    // 非敏感配置持久化到 localStorage，API Key 放 sessionStorage（关闭页面即清除）
    const { llmApiKey, oneApiKey, ...safeConfig } = newConfig;
    localStorage.setItem('textream_config', JSON.stringify(safeConfig));
    saveToStorage('textream_llm_api_key', llmApiKey, true);
    saveToStorage('textream_one_api_key', oneApiKey, true);
    setShowSettings(false);
    await checkHealth();
    try {
      await fetch(`${config.url}/api/models/settings`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: newConfig.llmProvider,
          base_url: newConfig.llmBaseUrl,
          api_key: newConfig.llmApiKey,
          model: newConfig.llmModel,
        }),
      });
    } catch { /* sync best-effort */ }
  };

  // ── 分割线拖拽 ──
  const [dragging, setDragging] = useState<'sidebar' | 'right' | null>(null);
  const dragMeta = useRef({ startX: 0, startW: 0 }).current;

  const onSidebarMouseDown = (e: React.MouseEvent) => {
    if (sidebarCollapsed) return;
    const nav = (e.currentTarget as HTMLElement).parentElement?.previousElementSibling as HTMLElement | null;
    if (!nav) return;
    e.preventDefault();
    nav.classList.add('no-transition');
    dragMeta.startX = e.clientX;
    dragMeta.startW = nav.getBoundingClientRect().width;
    setDragging('sidebar');
    document.body.style.cursor = 'col-resize';
  };

  const onRightMouseDown = (e: React.MouseEvent) => {
    if (rightCollapsed) return;
    const wrapper = (e.currentTarget as HTMLElement).parentElement;
    const aside = wrapper?.nextElementSibling as HTMLElement | null;
    if (!aside) return;
    e.preventDefault();
    dragMeta.startX = e.clientX;
    dragMeta.startW = aside.getBoundingClientRect().width;
    setDragging('right');
    document.body.style.cursor = 'col-resize';
  };

  const onRootMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    const delta = e.clientX - dragMeta.startX;
    if (dragging === 'sidebar') {
      setSidebarWidth(Math.max(160, Math.min(600, dragMeta.startW + delta)));
    } else {
      setRightWidth(Math.max(200, Math.min(500, dragMeta.startW - delta)));
    }
  };

  const onRootMouseUp = () => {
    if (!dragging) return;
    if (dragging === 'sidebar') {
      document.querySelector('nav')?.classList.remove('no-transition');
    }
    setDragging(null);
    document.body.style.cursor = '';
  };

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');
  const cycleFontSize = () => setFontSize(f => f === 'small' ? 'medium' : f === 'medium' ? 'large' : 'small');

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden" style={{ fontSize: 'inherit' }} onMouseMove={onRootMouseMove} onMouseUp={onRootMouseUp}>
      {/* ── 侧边栏 ── */}
      <nav
        style={{ width: sidebarCollapsed ? 56 : sidebarWidth, minWidth: sidebarCollapsed ? 56 : 56 }}
        className={`flex flex-col border-r border-border-subtle bg-bg-secondary/50 transition-[width] duration-150 ${sidebarCollapsed ? 'items-center' : ''}`}
      >
        {/* Logo */}
        <div className={`${sidebarCollapsed ? 'px-0 pt-4 pb-2' : 'px-5 pt-5 pb-4'}`}>
          <div className={`flex ${sidebarCollapsed ? 'flex-col items-center' : 'items-center gap-3'}`}>
            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent text-sm font-semibold shrink-0">
              T
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-sm font-semibold text-text-primary">Textream</h1>
                <p className="text-[11px] text-text-muted">直播 AI 军师</p>
              </div>
            )}
          </div>
        </div>

        {/* 导航项 */}
        <div className={`flex-1 ${sidebarCollapsed ? 'px-2' : 'px-3'} space-y-1`}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => setCurrentView(item.key)}
              title={sidebarCollapsed ? item.label : undefined}
              className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3'} ${sidebarCollapsed ? 'px-0 py-2.5' : 'px-4 py-2.5'} text-sm rounded-full transition-all duration-150 ${
                currentView === item.key
                  ? 'bg-accent/15 text-accent border border-accent/25 shadow-[0_0_16px_rgba(192,132,252,0.1)]'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/5 border border-transparent'
              }`}
            >
              <span className="text-base opacity-70 shrink-0">{item.icon}</span>
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </button>
          ))}
        </div>

        {/* 底部控制 */}
        <div className={`${sidebarCollapsed ? 'px-1' : 'px-4'} pb-4 pt-3 border-t border-border-subtle space-y-2`}>
          {/* 设置 */}
          <button
            onClick={() => setShowSettings(true)}
            title="设置"
            className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-2.5'} px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-white/5 rounded-full transition-all duration-150`}
          >
            <span className="text-base shrink-0 opacity-50">⚙</span>
            {!sidebarCollapsed && <span>设置</span>}
          </button>

          {/* 主题切换 */}
          <button
            onClick={toggleTheme}
            title={theme === 'dark' ? '切换白天模式' : '切换夜间模式'}
            className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-2.5'} px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-white/5 rounded-full transition-all duration-150`}
          >
            <span className="text-base shrink-0">{theme === 'dark' ? '☀' : '☾'}</span>
            {!sidebarCollapsed && <span>{theme === 'dark' ? '白天模式' : '夜间模式'}</span>}
          </button>

          {/* 字体大小 */}
          <button
            onClick={cycleFontSize}
            title={`字体大小: ${fontSize === 'small' ? '小' : fontSize === 'medium' ? '中' : '大'}`}
            className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-2.5'} px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-white/5 rounded-full transition-all duration-150`}
          >
            <span className="text-base shrink-0">Aa</span>
            {!sidebarCollapsed && <span>字体 {fontSize === 'small' ? '小' : fontSize === 'medium' ? '中' : '大'}</span>}
          </button>

          {/* 连接状态 */}
          {!sidebarCollapsed && (
            <>
              <div className="flex items-center gap-2.5 px-4">
                <span className={`status-dot ${connected ? 'status-dot-online' : 'bg-text-muted'}`} />
                <span className="text-xs text-text-muted">{connected ? '已连接' : '未连接'}</span>
              </div>
              <div className="text-[11px] text-text-muted px-4 truncate">
                {config.url.replace('http://', '')}
              </div>
            </>
          )}
        </div>
      </nav>

      {/* 侧边栏 ↔ 主内容 分割线 + 折叠按钮 */}
      <DividerWithFold
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onMouseDown={onSidebarMouseDown}
        buttonPosition="right"
        expandTitle="展开侧边栏"
        collapseTitle="折叠侧边栏"
      />

      {/* ── 主内容区 ── */}
      <main className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-hidden">
          {currentView === 'danmaku' && <DanmakuPanel />}
          {currentView === 'response' && <ResponseSidebar />}
          {currentView === 'memory' && <MemoryManager />}
          {currentView === 'knowledge' && <KnowledgeBase />}
        </div>

        {/* 右侧面板分割线 + 折叠按钮 */}
        {currentView === 'danmaku' && (
          <DividerWithFold
            collapsed={rightCollapsed}
            onToggle={() => setRightCollapsed(!rightCollapsed)}
            onMouseDown={onRightMouseDown}
            buttonPosition="left"
            expandTitle="展开右侧面板"
            collapseTitle="折叠右侧面板"
          />
        )}

        {/* 右侧面板（救场话术 + 快速回复） */}
        {currentView === 'danmaku' && !rightCollapsed && (
          <aside style={{ width: rightWidth, minWidth: 200 }} className="border-l border-border-subtle bg-bg-primary">
            <ResponseSidebar compact />
          </aside>
        )}
      </main>

      {/* 设置弹窗 */}
      {showSettings && (
        <SettingsModal
          config={config}
          onSave={handleSaveConfig}
          onClose={() => setShowSettings(false)}
          theme={theme}
          fontSize={fontSize}
          onThemeChange={setTheme}
          onFontSizeChange={setFontSize}
        />
      )}
    </div>
  );
}