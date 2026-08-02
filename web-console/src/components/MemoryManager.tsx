import { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { useAppStore } from '../stores/appStore';

export function MemoryManager() {
  const { memories, setMemories, removeMemory } = useAppStore();
  const [showAddForm, setShowAddForm] = useState(false);
  const [newContent, setNewContent] = useState('');
  const [newTags, setNewTags] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMemories();
  }, []);

  const loadMemories = async () => {
    try {
      const response = await api.getMemories();
      setMemories(response.data.items || []);
    } catch { /* ignore */ }
  };

  const handleAddMemory = async () => {
    if (!newContent.trim()) return;
    setLoading(true);
    try {
      const tags = newTags.split(',').map((t) => t.trim()).filter((t) => t);
      await api.saveMemory(newContent, tags);
      setNewContent('');
      setNewTags('');
      setShowAddForm(false);
      await loadMemories();
    } catch {
      console.error('Failed to add memory');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await api.deleteMemory(id);
      removeMemory(id);
    } catch { /* ignore */ }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <h2 className="text-sm font-semibold text-text-primary">记忆管理</h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-accent px-4 py-1.5 text-xs"
        >
          {showAddForm ? '✕ 取消' : '+ 添加'}
        </button>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="px-5 py-4 border-b border-border-subtle glass space-y-3">
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="输入记忆内容..."
            className="input-glass text-xs resize-none"
            rows={3}
          />
          <input
            type="text"
            value={newTags}
            onChange={(e) => setNewTags(e.target.value)}
            placeholder="标签（用逗号分隔）"
            className="input-glass text-xs"
          />
          <div className="flex gap-2">
            <button
              onClick={handleAddMemory}
              disabled={loading || !newContent.trim()}
              className="flex-1 px-3 py-2 text-xs btn-accent hover:btn-accent-hover disabled:opacity-50"
            >
              {loading ? '保存中...' : '保存'}
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-3 py-2 text-xs text-text-secondary hover:text-text-primary rounded-full border border-border-subtle hover:bg-white/5 transition"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Memory List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {memories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <p className="text-sm">暂无记忆</p>
          </div>
        ) : (
          memories.map((memory) => (
            <div key={memory.id} className="glass-card p-3 fade-in">
              <p className="text-xs text-text-primary mb-2 leading-relaxed selectable-text">{memory.content}</p>
              {memory.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {memory.tags.map((tag: string, idx: number) => (
                    <span key={idx} className="text-[11px] px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-[11px] text-text-muted">
                  {new Date(memory.timestamp).toLocaleDateString('zh-CN')}
                </span>
                <button
                  onClick={() => handleDeleteMemory(memory.id)}
                  className="text-[11px] text-danger hover:text-danger/80 transition"
                >
                  删除
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}