import { useState } from 'react';

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

interface SettingsModalProps {
  config: ServerConfig;
  onSave: (config: ServerConfig) => void;
  onClose: () => void;
}

const LLM_PROVIDERS: Record<string, { name: string; baseUrl: string; defaultModel: string; hint: string }> = {
  siliconflow: { name: 'SiliconFlow', baseUrl: 'https://api.siliconflow.cn/v1', defaultModel: 'Qwen/Qwen2.5-72B-Instruct', hint: '国内推荐，价格便宜' },
  openai: { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', defaultModel: 'gpt-4o', hint: '国际推荐，质量最高' },
  deepseek: { name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat', hint: '性价比高，中文优秀' },
  anthropic: { name: 'Anthropic', baseUrl: 'https://api.anthropic.com/v1', defaultModel: 'claude-3-5-sonnet-20241022', hint: '推理能力强' },
  none: { name: '不使用', baseUrl: '', defaultModel: '', hint: '降级到模板模式' },
};

export function SettingsModal({ config, onSave, onClose }: SettingsModalProps) {
  const [formData, setFormData] = useState<ServerConfig>(config);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);

  const handleChange = (field: keyof ServerConfig, value: string | boolean) => {
    setFormData((prev) => {
      const newData = { ...prev, [field]: value };
      if (field === 'llmProvider') {
        const provider = LLM_PROVIDERS[value as string];
        if (provider && value !== 'none') {
          newData.llmBaseUrl = provider.baseUrl;
          newData.llmModel = provider.defaultModel;
        }
      }
      return newData;
    });
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const response = await fetch(`${formData.url}/api/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-cache',
      });
      if (response.ok) {
        const data = await response.json();
        setTestResult(data.status === 'ok' ? 'success' : 'error');
      } else {
        setTestResult('error');
      }
    } catch {
      setTestResult('error');
    } finally {
      setTesting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  const currentProvider = LLM_PROVIDERS[formData.llmProvider];

  return (
    <div
      className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="modal-content w-full max-w-lg max-h-[85vh] overflow-y-auto fade-in">
        {/* Header */}
        <div className="sticky top-0 bg-bg-secondary border-b border-border-subtle px-6 py-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">⚙ 设置</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-full text-text-muted hover:text-text-primary hover:bg-white/10 transition text-sm"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* 服务器设置 */}
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">🌐 服务器设置</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-text-muted mb-1.5">服务器地址</label>
                <input
                  type="text"
                  value={formData.url}
                  onChange={(e) => handleChange('url', e.target.value)}
                  placeholder="http://localhost:9123"
                  className="input-glass text-xs"
                />
                <p className="text-[11px] text-text-muted mt-1">后端服务的完整地址（包括 http://）</p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="flex items-center gap-2 px-4 py-2 text-xs btn-accent hover:btn-accent-hover disabled:opacity-50"
                >
                  {testing ? '⏳ 测试中...' : '🔗 测试连接'}
                </button>
                {testResult === 'success' && (
                  <span className="text-xs text-success">✅ 连接成功</span>
                )}
                {testResult === 'error' && (
                  <span className="text-xs text-danger">❌ 连接失败</span>
                )}
              </div>
            </div>
          </section>

          {/* LLM 设置 */}
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">🤖 LLM 设置</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-text-muted mb-1.5">LLM 提供商</label>
                <select
                  value={formData.llmProvider}
                  onChange={(e) => handleChange('llmProvider', e.target.value)}
                  className="select-glass text-xs"
                >
                  {Object.entries(LLM_PROVIDERS).map(([key, provider]) => (
                    <option key={key} value={key}>{provider.name} — {provider.hint}</option>
                  ))}
                </select>
              </div>
              {formData.llmProvider !== 'none' && (
                <>
                  <div>
                    <label className="block text-xs text-text-muted mb-1.5">API Base URL</label>
                    <input
                      type="text"
                      value={formData.llmBaseUrl}
                      onChange={(e) => handleChange('llmBaseUrl', e.target.value)}
                      className="input-glass text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-text-muted mb-1.5">API Key</label>
                    <input
                      type="password"
                      value={formData.llmApiKey}
                      onChange={(e) => handleChange('llmApiKey', e.target.value)}
                      placeholder="sk-..."
                      className="input-glass text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-text-muted mb-1.5">模型</label>
                    <input
                      type="text"
                      value={formData.llmModel}
                      onChange={(e) => handleChange('llmModel', e.target.value)}
                      className="input-glass text-xs"
                    />
                  </div>
                </>
              )}
            </div>
          </section>

          {/* One Memory 设置 */}
          <section>
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">🧠 记忆系统</h3>
            <div className="space-y-3">
              <label className="flex items-center gap-2.5 cursor-pointer">
                <div
                  className={`w-8 h-4 rounded-full transition-colors duration-150 relative ${
                    formData.useOneMemory ? 'bg-accent/40' : 'bg-white/10'
                  }`}
                  onClick={() => handleChange('useOneMemory', !formData.useOneMemory)}
                >
                  <div
                    className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform duration-150 ${
                      formData.useOneMemory ? 'translate-x-[18px]' : 'translate-x-0.5'
                    }`}
                  />
                </div>
                <span className="text-xs text-text-secondary">启用 One Memory</span>
              </label>
              {formData.useOneMemory && (
                <>
                  <div>
                    <label className="block text-xs text-text-muted mb-1.5">One 项目根路径</label>
                    <input
                      type="text"
                      value={formData.oneRoot}
                      onChange={(e) => handleChange('oneRoot', e.target.value)}
                      className="input-glass text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-text-muted mb-1.5">API Key</label>
                    <input
                      type="password"
                      value={formData.oneApiKey}
                      onChange={(e) => handleChange('oneApiKey', e.target.value)}
                      className="input-glass text-xs font-mono"
                    />
                  </div>
                </>
              )}
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-bg-secondary border-t border-border-subtle px-6 py-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs text-text-secondary hover:text-text-primary rounded-full border border-border-subtle hover:bg-white/5 transition"
          >
            取消
          </button>
          <button
            onClick={() => onSave(formData)}
            className="px-5 py-2 text-xs btn-accent hover:btn-accent-hover"
          >
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}