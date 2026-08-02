import { useAppStore } from '../stores/appStore';
import { api } from '../utils/api';
import { useState } from 'react';

const QUICK_RESPONSES = {
  question: ['这是个好问题！让我想想...', '感谢提问！我的看法是...', '这个问题很有意思，我认为...'],
  opinion: ['我同意你的观点！', '这是个有意思的角度...', '从另一个角度看，也许可以...'],
  emotion: ['非常感谢你的支持！🙏', '很高兴听到你的反馈！', '你的理解让我很感动...'],
};

export function QuickResponses() {
  const { addResponse, selectedLevel } = useAppStore();
  const [loading, setLoading] = useState<string | false>(false);
  const [error, setError] = useState<string | null>(null);
  const [customPrompt, setCustomPrompt] = useState('');

  const handleQuickResponse = async (type: keyof typeof QUICK_RESPONSES) => {
    const templates = QUICK_RESPONSES[type];
    const randomTemplate = templates[Math.floor(Math.random() * templates.length)];
    setLoading(type);
    setError(null);
    try {
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
    } catch (err) {
      setError('生成失败，请检查 LLM 配置');
      console.error('Failed to generate response:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="px-4 py-3 border-t border-border-subtle">
      <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-2.5">⚡ 快速回复</h3>

      <input
        type="text"
        value={customPrompt}
        onChange={(e) => setCustomPrompt(e.target.value)}
        placeholder="输入自定义提示词..."
        className="input-glass text-xs mb-2.5"
      />

      <div className="grid grid-cols-3 gap-1.5">
        <button
          onClick={() => handleQuickResponse('question')}
          disabled={loading === 'question'}
          className="px-2 py-2 text-xs rounded-full bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition disabled:opacity-50"
        >
          {loading === 'question' ? '⏳' : '❓'} 回答问题
        </button>
        <button
          onClick={() => handleQuickResponse('opinion')}
          disabled={loading === 'opinion'}
          className="px-2 py-2 text-xs rounded-full bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition disabled:opacity-50"
        >
          {loading === 'opinion' ? '⏳' : '💡'} 表达观点
        </button>
        <button
          onClick={() => handleQuickResponse('emotion')}
          disabled={loading === 'emotion'}
          className="px-2 py-2 text-xs rounded-full bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition disabled:opacity-50"
        >
          {loading === 'emotion' ? '⏳' : '❤️'} 情感回应
        </button>
      </div>
      {error && <p className="text-[10px] text-danger mt-2 text-center">{error}</p>}
    </div>
  );
}