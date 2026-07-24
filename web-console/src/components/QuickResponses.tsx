import { useAppStore } from '../stores/appStore';
import { api } from '../utils/api';
import { useState } from 'react';

const QUICK_RESPONSES = {
  question: [
    '这是个好问题！让我想想...',
    '感谢提问！我的看法是...',
    '这个问题很有意思，我认为...',
  ],
  opinion: [
    '我同意你的观点！',
    '这是个有意思的角度...',
    '从另一个角度看，也许可以...',
  ],
  emotion: [
    '非常感谢你的支持！🙏',
    '很高兴听到你的反馈！',
    '你的理解让我很感动...',
  ],
};

export function QuickResponses() {
  const { addResponse, selectedLevel } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');

  const handleQuickResponse = async (type: keyof typeof QUICK_RESPONSES) => {
    const templates = QUICK_RESPONSES[type];
    const randomTemplate = templates[Math.floor(Math.random() * templates.length)];

    setLoading(true);
    try {
      // 使用模板或自定义提示词
      const prompt = customPrompt || randomTemplate;
      const response = await api.generateResponse(prompt, selectedLevel);

      addResponse({
        id: `${Date.now()}`,
        text: response.data.response || response.data.message,
        level: selectedLevel,
        danmaku: customPrompt || `[快速回复] ${type}`,
        timestamp: Date.now(),
        copied: false,
      });

      setCustomPrompt('');
    } catch (error) {
      console.error('Failed to generate response:', error);
      alert('生成回复失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
      <h3 className="text-sm font-bold mb-3">⚡ 快速回复</h3>

      {/* Custom prompt input */}
      <input
        type="text"
        value={customPrompt}
        onChange={(e) => setCustomPrompt(e.target.value)}
        placeholder="输入自定义提示词..."
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm mb-3"
      />

      {/* Quick response buttons */}
      <div className="grid grid-cols-3 gap-2">
        <button
          onClick={() => handleQuickResponse('question')}
          disabled={loading}
          className="px-2 py-2 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition text-xs disabled:opacity-50"
        >
          ❓ 回答问题
        </button>
        <button
          onClick={() => handleQuickResponse('opinion')}
          disabled={loading}
          className="px-2 py-2 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200 dark:hover:bg-purple-800 transition text-xs disabled:opacity-50"
        >
          💡 表达观点
        </button>
        <button
          onClick={() => handleQuickResponse('emotion')}
          disabled={loading}
          className="px-2 py-2 bg-pink-100 dark:bg-pink-900 text-pink-700 dark:text-pink-300 rounded hover:bg-pink-200 dark:hover:bg-pink-800 transition text-xs disabled:opacity-50"
        >
          ❤️ 情感回应
        </button>
      </div>
    </div>
  );
}
