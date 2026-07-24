import { create } from 'zustand';
import type { AppState, Danmaku, SavedResponse, Memory, KnowledgeDoc } from '../types';

interface AppStore extends AppState {
  // Actions
  setConnected: (connected: boolean) => void;
  setServerUrl: (url: string) => void;

  // Danmaku
  addDanmaku: (danmaku: Danmaku) => void;
  clearDanmaku: () => void;
  setIsCapturing: (capturing: boolean) => void;
  setCaptureRegion: (region: { x: number; y: number; width: number; height: number }) => void;

  // Responses
  addResponse: (response: SavedResponse) => void;
  clearResponses: () => void;
  setSelectedLevel: (level: 'simple' | 'deep' | 'humorous') => void;
  setGeneratedResponse: (text: string) => void;

  // Memory
  setMemories: (memories: Memory[]) => void;
  addMemory: (memory: Memory) => void;
  removeMemory: (id: string) => void;
  setSelectedMemory: (memory?: Memory) => void;

  // Knowledge
  setKnowledgeDocs: (docs: KnowledgeDoc[]) => void;
  addKnowledgeDoc: (doc: KnowledgeDoc) => void;
  removeKnowledgeDoc: (id: string) => void;
}

const MAX_DANMAKU = 100;
const MAX_RESPONSES = 50;

export const useAppStore = create<AppStore>((set) => ({
  // Initial state
  connected: false,
  serverUrl: 'http://localhost:9123',
  danmaku: [],
  isCapturing: false,
  responses: [],
  selectedLevel: 'simple',
  memories: [],
  knowledgeDocs: [],

  // Connection
  setConnected: (connected) => set({ connected }),
  setServerUrl: (serverUrl) => set({ serverUrl }),

  // Danmaku
  addDanmaku: (danmaku) =>
    set((state) => ({
      danmaku: [danmaku, ...state.danmaku].slice(0, MAX_DANMAKU),
    })),
  clearDanmaku: () => set({ danmaku: [] }),
  setIsCapturing: (isCapturing) => set({ isCapturing }),
  setCaptureRegion: (captureRegion) => set({ captureRegion }),

  // Responses
  addResponse: (response) =>
    set((state) => ({
      responses: [response, ...state.responses].slice(0, MAX_RESPONSES),
    })),
  clearResponses: () => set({ responses: [] }),
  setSelectedLevel: (selectedLevel) => set({ selectedLevel }),
  setGeneratedResponse: (generatedResponse) => set({ generatedResponse }),

  // Memory
  setMemories: (memories) => set({ memories }),
  addMemory: (memory) => set((state) => ({ memories: [memory, ...state.memories] })),
  removeMemory: (id) => set((state) => ({ memories: state.memories.filter((m) => m.id !== id) })),
  setSelectedMemory: (selectedMemory) => set({ selectedMemory }),

  // Knowledge
  setKnowledgeDocs: (knowledgeDocs) => set({ knowledgeDocs }),
  addKnowledgeDoc: (doc) => set((state) => ({ knowledgeDocs: [doc, ...state.knowledgeDocs] })),
  removeKnowledgeDoc: (id) =>
    set((state) => ({ knowledgeDocs: state.knowledgeDocs.filter((d) => d.id !== id) })),
}));
