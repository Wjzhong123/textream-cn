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
    } catch (error) {
      console.error('Failed to load memories:', error);
    }
  };

  const handleAddMemory = async () => {
    if (!newContent.trim()) return;

    setLoading(true);
    try {
      const tags = newTags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t);
      await api.saveMemory(newContent, tags);
      setNewContent('');
      setNewTags('');
      setShowAddForm(false);
      await loadMemories();
    } catch (error) {
      console.error('Failed to add memory:', error);
      alert('添加记忆失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    if (!confirm('确定要删除这条记忆吗？')) return;

    try {
      await api.deleteMemory(id);
      removeMemory(id);
    } catch (error) {
      console.error('Failed to delete memory:', error);
      alert('删除记忆失败');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold">记忆管理</h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-3 py-1.5 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition text-sm"
          >
            + 添加
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="输入记忆内容..."
            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm mb-2"
            rows={3}
          />
          <input
            type="text"
            value={newTags}
            onChange={(e) => setNewTags(e.target.value)}
            placeholder="标签（用逗号分隔）"
            className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm mb-3"
          />
          <div className="flex gap-2">
            <button
              onClick={handleAddMemory}
              disabled={loading || !newContent.trim()}
              className="flex-1 px-3 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition disabled:opacity-50"
            >
              {loading ? '保存中...' : '保存'}
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="px-3 py-2 bg-gray-300 dark:bg-gray-700 rounded-lg hover:bg-gray-400 dark:hover:bg-gray-600"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Memory List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {memories.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            暂无记忆
          </div>
        ) : (
          memories.map((memory) => (
            <div
              key={memory.id}
              className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <p className="text-sm mb-2">{memory.content}</p>
              <div className="flex flex-wrap gap-1 mb-2">
                {memory.tags?.map((tag, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-0.5 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">
                  {new Date(memory.timestamp).toLocaleDateString('zh-CN')}
                </span>
                <button
                  onClick={() => handleDeleteMemory(memory.id)}
                  className="text-xs text-red-500 hover:text-red-600"
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
