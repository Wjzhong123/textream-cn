import { useState, useEffect, useRef } from 'react';
import { api } from '../utils/api';
import { useAppStore } from '../stores/appStore';

export function KnowledgeBase() {
  const { knowledgeDocs, setKnowledgeDocs, removeKnowledgeDoc } = useAppStore();
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadKnowledgeBase();
  }, []);

  const loadKnowledgeBase = async () => {
    try {
      const response = await api.getKnowledgeBase();
      setKnowledgeDocs(response.data.items || []);
    } catch (error) {
      console.error('Failed to load knowledge base:', error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 验证文件类型
    const validTypes = ['.txt', '.md', '.json'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(fileExt)) {
      alert('只支持 .txt、.md、.json 文件');
      return;
    }

    setUploading(true);
    try {
      await api.uploadKnowledge(file);
      await loadKnowledgeBase();
      alert('上传成功！');
    } catch (error) {
      console.error('Failed to upload file:', error);
      alert('上传失败');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteDoc = async (id: string) => {
    if (!confirm('确定要删除这个文档吗？')) return;

    try {
      await api.deleteKnowledge(id);
      removeKnowledgeDoc(id);
    } catch (error) {
      console.error('Failed to delete document:', error);
      alert('删除失败');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold">知识库</h2>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="px-3 py-1.5 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition text-sm disabled:opacity-50"
          >
            {uploading ? '上传中...' : '+ 上传文档'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.json"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          支持 .txt、.md、.json 格式
        </p>
      </div>

      {/* Knowledge List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {knowledgeDocs.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <p className="mb-2">暂无文档</p>
            <p className="text-sm">点击"上传文档"添加知识</p>
          </div>
        ) : (
          knowledgeDocs.map((doc) => (
            <div
              key={doc.id}
              className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-500">
                    {doc.vectorCount || 0} 个向量块 ·{' '}
                    {new Date(doc.uploadedAt).toLocaleDateString('zh-CN')}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteDoc(doc.id)}
                  className="ml-2 text-xs text-red-500 hover:text-red-600"
                >
                  删除
                </button>
              </div>
              <details className="text-xs">
                <summary className="cursor-pointer text-primary-600 dark:text-primary-400 hover:underline">
                  查看内容
                </summary>
                <div className="mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-xs overflow-auto max-h-32">
                  {doc.content?.substring(0, 500)}
                  {(doc.content?.length || 0) > 500 && '...'}
                </div>
              </details>
            </div>
          ))
        )}
      </div>

      {/* Stats */}
      {knowledgeDocs.length > 0 && (
        <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-xs text-gray-600 dark:text-gray-400">
          共 {knowledgeDocs.length} 个文档，{knowledgeDocs.reduce((sum, doc) => sum + (doc.vectorCount || 0), 0)} 个向量块
        </div>
      )}
    </div>
  );
}
