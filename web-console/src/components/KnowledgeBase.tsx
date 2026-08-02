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
      const docs = (response.data.items || []).map((item: any) => ({
        id: item.id || item.name || `${Date.now()}`,
        filename: item.name || item.filename || '未知文档',
        content: item.content || item.summary || '',
        vectorCount: item.vectorCount || 0,
        uploadedAt: item.uploadedAt || item.timestamp || new Date().toISOString(),
      }));
      setKnowledgeDocs(docs);
    } catch { /* ignore */ }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ['.txt', '.md', '.json', '.docx', '.doc'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(fileExt)) {
      return;
    }

    setUploading(true);
    try {
      await api.uploadKnowledge(file);
      await loadKnowledgeBase();
    } catch {
      console.error('Failed to upload');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDoc = async (id: string) => {
    try {
      await api.deleteKnowledge(id);
      removeKnowledgeDoc(id);
    } catch { /* ignore */ }
  };

  const totalVectors = knowledgeDocs.reduce((sum, doc) => sum + (doc.vectorCount || 0), 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <h2 className="text-sm font-semibold text-text-primary">知识库</h2>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="btn-accent px-4 py-1.5 text-xs disabled:opacity-50"
        >
          {uploading ? '上传中...' : '+ 上传文档'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.json,.docx,.doc"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>

      {/* Knowledge List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {knowledgeDocs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-text-muted">
            <p className="text-sm mb-1">暂无文档</p>
            <p className="text-xs">点击上传文档添加知识</p>
          </div>
        ) : (
          knowledgeDocs.map((doc) => (
            <div key={doc.id} className="glass-card p-3 fade-in">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-text-primary font-medium truncate">{doc.filename}</p>
                  <p className="text-[11px] text-text-muted">
                    {doc.vectorCount || 0} 个向量块 · {new Date(doc.uploadedAt).toLocaleDateString('zh-CN')}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteDoc(doc.id)}
                  className="ml-2 text-[11px] text-danger hover:text-danger/80 transition shrink-0"
                >
                  删除
                </button>
              </div>
              <details className="text-xs">
                <summary className="cursor-pointer text-accent hover:text-accent/80 transition">
                  查看内容
                </summary>
                <div className="mt-2 p-2 glass rounded-lg text-xs overflow-auto max-h-[300px] whitespace-pre-wrap selectable-text text-text-secondary">
                  {doc.content || '（无内容）'}
                </div>
              </details>
            </div>
          ))
        )}
      </div>

      {/* Stats */}
      {knowledgeDocs.length > 0 && (
        <div className="px-5 py-3 border-t border-border-subtle text-[11px] text-text-muted">
          共 {knowledgeDocs.length} 个文档，{totalVectors} 个向量块
        </div>
      )}
    </div>
  );
}