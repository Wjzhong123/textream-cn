import axios from 'axios';
import type { AxiosInstance } from 'axios';

// Load server URL from localStorage
const getServerUrl = () => {
  try {
    const saved = localStorage.getItem('textream_config');
    if (saved) {
      const config = JSON.parse(saved);
      return config.url || 'http://localhost:9123';
    }
  } catch {
    // Ignore parsing errors
  }
  return 'http://localhost:9123';
};

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = getServerUrl();
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Update base URL (called when config changes)
  updateBaseURL(url: string) {
    this.baseURL = url;
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Danmaku API
  async startDanmakuCapture() {
    return this.client.post('/api/danmaku/start');
  }

  async stopDanmakuCapture() {
    return this.client.post('/api/danmaku/stop');
  }

  async setCaptureRegion(region: { x: number; y: number; width: number; height: number }) {
    return this.client.post('/api/danmaku/region', region);
  }

  async getDanmakuStatus() {
    return this.client.get('/api/danmaku/status');
  }

  async openRegionSelector() {
    return this.client.post('/api/danmaku/selector');
  }

  // Response API
  async generateResponse(danmakuText: string, level: 'simple' | 'deep' | 'humorous') {
    return this.client.post('/api/chat', {
      message: `弹幕: ${danmakuText}\n\n请用${level === 'simple' ? '简洁' : level === 'deep' ? '深入' : '幽默'}的方式回复这条弹幕。`,
    });
  }

  // Memory API
  async getMemories() {
    return this.client.get('/api/memory/list');
  }

  async saveMemory(content: string, tags: string[]) {
    return this.client.post('/api/memory/add', { content, tags });
  }

  async deleteMemory(id: string) {
    return this.client.delete(`/api/memory/delete/${id}`);
  }

  // Knowledge API
  async getKnowledgeBase() {
    return this.client.get('/api/knowledge/list');
  }

  async uploadKnowledge(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.client.post('/api/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }

  async deleteKnowledge(id: string) {
    return this.client.delete(`/api/knowledge/delete/${id}`);
  }

  // Health check
  async healthCheck() {
    return this.client.get('/api/health');
  }
}

export const api = new ApiClient();
