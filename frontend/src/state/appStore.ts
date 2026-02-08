import { create } from "zustand";

import type { CharacterMood, ChatMessage } from "../types/domain";

interface AppState {
  activeDocId: string | null;
  mood: CharacterMood;
  ttsEnabled: boolean;
  messages: ChatMessage[];
  setActiveDocId: (docId: string | null) => void;
  setMood: (mood: CharacterMood) => void;
  toggleTts: () => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeDocId: null,
  mood: "neutral",
  ttsEnabled: false,
  messages: [],
  setActiveDocId: (docId) => set({ activeDocId: docId }),
  setMood: (mood) => set({ mood }),
  toggleTts: () => set((state) => ({ ttsEnabled: !state.ttsEnabled })),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
}));
