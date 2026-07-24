export interface Danmaku {
  id: string;
  text: string;
  timestamp: number;
  platform?: string;
  intent?: {
    type: 'question' | 'opinion' | 'emotion' | 'spam';
    confidence: number;
    needsResponse: boolean;
  };
}

export interface SavedResponse {
  id: string;
  text: string;
  level: 'simple' | 'deep' | 'humorous';
  danmaku: string;
  timestamp: number;
  copied: boolean;
}

export interface Memory {
  id: string;
  content: string;
  tags: string[];
  timestamp: number;
  importance: number;
}

export interface KnowledgeDoc {
  id: string;
  filename: string;
  content: string;
  vectorCount: number;
  uploadedAt: number;
}

export interface AppState {
  // Connection
  connected: boolean;
  serverUrl: string;

  // Danmaku
  danmaku: Danmaku[];
  isCapturing: boolean;
  captureRegion?: { x: number; y: number; width: number; height: number };

  // Responses
  responses: SavedResponse[];
  selectedLevel: 'simple' | 'deep' | 'humorous';
  generatedResponse?: string;

  // Memory
  memories: Memory[];
  selectedMemory?: Memory;

  // Knowledge
  knowledgeDocs: KnowledgeDoc[];
}
