import { useAppStore } from '../stores/appStore';
import { QuickResponses } from './QuickResponses';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export function ResponseSidebar() {
  const { responses, selectedLevel, setSelectedLevel, clearResponses } = useAppStore();

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('已复制到剪贴板！');
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const levelLabels = {
    simple: '简洁',
    deep: '深入',
    humorous: '幽默',
  };

  const levelColors = {
    simple: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    deep: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
    humorous: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  };

  return (
    <div className="flex flex-col h-full border-l border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-xl font-bold">救场话术</h2>
          <button
            onClick={clearResponses}
            className="text-sm px-3 py-1 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            清空
          </button>
        </div>

        {/* Level Selector */}
        <div className="flex gap-2">
          {(['simple', 'deep', 'humorous'] as const).map((level) => (
            <button
              key={level}
              onClick={() => setSelectedLevel(level)}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition ${
                selectedLevel === level
                  ? levelColors[level]
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
              }`}
            >
              {levelLabels[level]}
            </button>
          ))}
        </div>
      </div>

      {/* Responses List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {responses.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            暂无救场话术<br />
            <span className="text-sm">在弹幕监控中点击"生成回复"</span>
          </div>
        ) : (
          responses.map((response) => (
            <div
              key={response.id}
              className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              {/* Original Danmaku */}
              <div className="mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                <p className="text-xs text-gray-500 mb-1">原弹幕</p>
                <p className="text-sm text-gray-700 dark:text-gray-300">{response.danmaku}</p>
              </div>

              {/* Generated Response */}
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      levelColors[response.level]
                    }`}
                  >
                    {levelLabels[response.level]}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatDistanceToNow(response.timestamp, { addSuffix: true, locale: zhCN })}
                  </span>
                </div>
                <p className="text-sm">{response.text}</p>
              </div>

              {/* Actions */}
              <button
                onClick={() => handleCopy(response.text)}
                className="w-full px-3 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition text-sm"
              >
                📋 复制话术
              </button>
            </div>
          ))
        )}
      </div>

      {/* Quick Responses */}
      <QuickResponses />
    </div>
  );
}
