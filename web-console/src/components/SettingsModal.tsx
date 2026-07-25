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

const LLM_PROVIDERS = {
  siliconflow: {
    name: 'SiliconFlow',
    baseUrl: 'https://api.siliconflow.cn/v1',
    defaultModel: 'Qwen/Qwen2.5-72B-Instruct',
    hint: '国内推荐，价格便宜',
  },
  openai: {
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    defaultModel: 'gpt-4o',
    hint: '国际推荐，质量最高',
  },
  deepseek: {
    name: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com/v1',
    defaultModel: 'deepseek-chat',
    hint: '性价比高，中文优秀',
  },
  anthropic: {
    name: 'Anthropic',
    baseUrl: 'https://api.anthropic.com/v1',
    defaultModel: 'claude-3-5-sonnet-20241022',
    hint: '推理能力强',
  },
  none: {
    name: '不使用',
    baseUrl: '',
    defaultModel: '',
    hint: '降级到模板模式',
  },
};

export function SettingsModal({ config, onSave, onClose }: SettingsModalProps) {
  const [formData, setFormData] = useState<ServerConfig>(config);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);

  const handleChange = (field: keyof ServerConfig, value: string | boolean) => {
    setFormData((prev) => {
      const newData = { ...prev, [field]: value };

      // 如果切换了提供商，自动更新 Base URL 和模型
      if (field === 'llmProvider') {
        const provider = LLM_PROVIDERS[value as keyof typeof LLM_PROVIDERS];
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
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-cache',
      });

      if (response.ok) {
        const data = await response.json();
        setTestResult(data.status === 'ok' ? 'success' : 'error');
      } else {
        setTestResult('error');
      }
    } catch (error) {
      console.error('Connection test failed:', error);
      setTestResult('error');
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    onSave(formData);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const currentProvider = LLM_PROVIDERS[formData.llmProvider as keyof typeof LLM_PROVIDERS];

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6 flex justify-between items-center">
          <h2 className="text-xl font-bold">⚙️ 设置</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Server Configuration */}
          <section>
            <h3 className="text-lg font-semibold mb-3">🌐 服务器设置</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  服务器地址
                </label>
                <input
                  type="text"
                  value={formData.url}
                  onChange={(e) => handleChange('url', e.target.value)}
                  placeholder="http://localhost:9123"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  后端服务的完整地址（包括 http://）
                </p>
              </div>

              <button
                onClick={handleTestConnection}
                disabled={testing}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testing ? '⏳ 测试中...' : '🔗 测试连接'}
              </button>

              {testResult === 'success' && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <p className="text-sm text-green-700 dark:text-green-300">
                    ✅ 连接成功！
                  </p>
                </div>
              )}

              {testResult === 'error' && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-sm text-red-700 dark:text-red-300">
                    ❌ 连接失败，请检查服务器地址是否正确
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* LLM Configuration */}
          <section>
            <h3 className="text-lg font-semibold mb-3">🤖 LLM 设置</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  LLM 提供商
                </label>
                <select
                  value={formData.llmProvider}
                  onChange={(e) => handleChange('llmProvider', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {Object.entries(LLM_PROVIDERS).map(([key, provider]) => (
                    <option key={key} value={key}>
                      {provider.name} - {provider.hint}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API 地址
                </label>
                <input
                  type="text"
                  value={formData.llmBaseUrl}
                  onChange={(e) => handleChange('llmBaseUrl', e.target.value)}
                  placeholder="https://api.siliconflow.cn/v1"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {currentProvider?.hint || '请选择提供商'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API Key
                </label>
                <input
                  type="password"
                  value={formData.llmApiKey}
                  onChange={(e) => handleChange('llmApiKey', e.target.value)}
                  placeholder="sk-xxxxx"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  仅在当前浏览器会话中保存
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  模型名称
                </label>
                <input
                  type="text"
                  value={formData.llmModel}
                  onChange={(e) => handleChange('llmModel', e.target.value)}
                  placeholder={currentProvider?.defaultModel || 'gpt-4o'}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  已自动填充默认模型，可以手动修改
                </p>
              </div>
            </div>
          </section>

          {/* One Memory Configuration */}
          <section>
            <h3 className="text-lg font-semibold mb-3">🧠 One Memory 设置</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="useOneMemory"
                  checked={formData.useOneMemory}
                  onChange={(e) => handleChange('useOneMemory', e.target.checked)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <label
                  htmlFor="useOneMemory"
                  className="text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  启用 One Memory 向量检索
                </label>
              </div>

              {formData.useOneMemory && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      One API Key
                    </label>
                    <input
                      type="password"
                      value={formData.oneApiKey}
                      onChange={(e) => handleChange('oneApiKey', e.target.value)}
                      placeholder="one_xxxxx"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      从 One OS 设置或 One Cloud 控制台获取 API 密钥
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      One Root
                    </label>
                    <input
                      type="text"
                      value={formData.oneRoot}
                      onChange={(e) => handleChange('oneRoot', e.target.value)}
                      placeholder="/Users/mac/Desktop/oh-agent-panel"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      One OS 项目的根目录路径
                    </p>
                  </div>
                </>
              )}
            </div>
          </section>

          {/* Info Box */}
          <section className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-200 mb-2">
              💡 提示
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
              <li>
                服务器设置会立即生效，无需重启
              </li>
              <li>
                LLM API Key 和 Base URL 仅在当前浏览器会话中保存
              </li>
              <li>
                One Memory 配置需要重启后端服务才能生效
              </li>
              <li>
                配置会自动保存到本地存储
              </li>
            </ul>
          </section>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 p-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition"
          >
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}
