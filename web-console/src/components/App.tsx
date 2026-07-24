import { useState, useEffect } from 'react';
import { DanmakuPanel } from './DanmakuPanel';
import { ResponseSidebar } from './ResponseSidebar';
import { MemoryManager } from './MemoryManager';
import { KnowledgeBase } from './KnowledgeBase';

type View = 'danmaku' | 'memory' | 'knowledge';

export function App() {
  const [connected, setConnected] = useState(false);
  const [currentView, setCurrentView] = useState<View>('danmaku');

  useEffect(() => {
    // Health check on mount
    fetch('http://localhost:9123/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'ok') {
          setConnected(true);
        }
      })
      .catch((error) => {
        console.error('Health check failed:', error);
        setConnected(false);
      });

    // 定期健康检查
    const interval = setInterval(() => {
      fetch('http://localhost:9123/health')
        .then((res) => res.json())
        .then((data) => setConnected(data.status === 'ok'))
        .catch(() => setConnected(false));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

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

        {/* Connection Status */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
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
    </div>
  );
}
