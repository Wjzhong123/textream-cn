import { useState, useEffect } from 'react';
import { DanmakuPanel } from './DanmakuPanel';
import { ResponseSidebar } from './ResponseSidebar';
import { MemoryManager } from './MemoryManager';
import { KnowledgeBase } from './KnowledgeBase';
import { SettingsModal } from './SettingsModal';

type View = 'danmaku' | 'memory' | 'knowledge';

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

export function App() {
  const [connected, setConnected] = useState(false);
  const [currentView, setCurrentView] = useState<View>('danmaku');
  const [showSettings, setShowSettings] = useState(false);
  const [config, setConfig] = useState<ServerConfig>(() => {
    // Load from localStorage or use defaults
    const saved = localStorage.getItem('textream_config');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Invalid JSON, use defaults
      }
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

  // Health check function
  const checkHealth = async () => {
    try {
      const response = await fetch(`${config.url}/api/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        // Add cache busting
        cache: 'no-cache',
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'ok') {
          setConnected(true);
          return true;
        }
      }
      setConnected(false);
      return false;
    } catch (error) {
      console.error('Health check failed:', error);
      setConnected(false);
      return false;
    }
  };

  useEffect(() => {
    // Initial health check
    checkHealth();

    // Periodic health check every 5 seconds
    const interval = setInterval(checkHealth, 5000);

    return () => clearInterval(interval);
  }, [config.url]);

  const handleSaveConfig = async (newConfig: ServerConfig) => {
    setConfig(newConfig);
    localStorage.setItem('textream_config', JSON.stringify(newConfig));
    setShowSettings(false);
    // Re-check connection with new URL
    await checkHealth();

    // 同步 LLM 配置到后端 API（运行时生效，自动持久化）
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
    } catch (e) {
      console.warn('LLM config sync failed (backend may not support it yet):', e);
    }
  };

  const navItems = [
    { key: 'danmaku' as const, label: '弹幕监控', icon: '💬' },
    { key: 'memory' as const, label: '记忆管理', icon: '🧠' },
    { key: 'knowledge' as const, label: '知识库', icon: '📚' },
  ];

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      {/* Sidebar Navigation */}
      <nav className="w-16 md:w-56 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="text-2xl">🎙️</div>
            <div className="hidden md:block">
              <h1 className="text-lg font-bold">Textream</h1>
              <p className="text-xs text-gray-500">直播 AI 军师</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 p-2 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => setCurrentView(item.key)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition ${
                currentView === item.key
                  ? 'bg-primary-500 text-white'
                  : 'hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="hidden md:block text-sm">{item.label}</span>
            </button>
          ))}
        </div>

        {/* Bottom Actions */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
          {/* Settings Button */}
          <button
            onClick={() => setShowSettings(true)}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
            title="设置"
          >
            <span className="text-lg">⚙️</span>
            <span className="hidden md:block">设置</span>
          </button>

          {/* Connection Status */}
          <div className="flex items-center gap-2 text-xs">
            <div
              className={`w-2 h-2 rounded-full ${
                connected ? 'bg-success-500' : 'bg-gray-400'
              }`}
            />
            <span className="hidden md:block text-gray-600 dark:text-gray-400">
              {connected ? '服务已连接' : '服务未连接'}
            </span>
          </div>

          {/* Server URL (shortened) */}
          <div className="hidden md:block text-xs text-gray-500 truncate">
            {config.url.replace('http://', '')}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel (Danmaku / Memory / Knowledge) */}
        <div className="flex-1 overflow-hidden">
          {currentView === 'danmaku' && <DanmakuPanel />}
          {currentView === 'memory' && <MemoryManager />}
          {currentView === 'knowledge' && <KnowledgeBase />}
        </div>

        {/* Right Panel (Response Sidebar) - only show in danmaku mode */}
        {currentView === 'danmaku' && (
          <aside className="w-96 border-l border-gray-200 dark:border-gray-700">
            <ResponseSidebar />
          </aside>
        )}
      </main>

      {/* Settings Modal */}
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
