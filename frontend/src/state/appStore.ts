import { create } from "zustand";
import type { CharacterMood, ChatMessage, CompanionStatus } from "@/types/domain";

interface AppState {
  activeDocId: string | null;
  sessionId: string | null;
  mood: CharacterMood;
  companionStatus: CompanionStatus;
  affection: number;
  sessionStreak: number;
  lastInteractionAt: string | null;
  ttsEnabled: boolean;
  isListening: boolean;
  messages: ChatMessage[];
  setActiveDocId: (docId: string | null) => void;
  setSessionId: (sessionId: string | null) => void;
  setMood: (mood: CharacterMood) => void;
  setCompanionStatus: (status: CompanionStatus) => void;
  toggleTts: () => void;
  bumpAffection: (delta: number) => void;
  incrementSessionStreak: () => void;
  resetSessionStreak: () => void;
  setListening: (value: boolean) => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearConversation: () => void;
}

const clampAffection = (value: number) => Math.max(0, Math.min(100, value));

export const useAppStore = create<AppState>((set) => ({
  activeDocId: null,
  sessionId: null,
  mood: "neutral",
  companionStatus: "idle",
  affection: 40,
  sessionStreak: 0,
  lastInteractionAt: null,
  ttsEnabled: false,
  isListening: false,
  messages: [],
  setActiveDocId: (docId) => set({ activeDocId: docId }),
  setSessionId: (sessionId) => set({ sessionId }),
  setMood: (mood) => set({ mood }),
  setCompanionStatus: (status) => set({ companionStatus: status }),
  toggleTts: () => set((state) => ({ ttsEnabled: !state.ttsEnabled })),
  bumpAffection: (delta) =>
    set((state) => ({
      affection: clampAffection(state.affection + delta),
      lastInteractionAt: new Date().toISOString(),
    })),
  incrementSessionStreak: () =>
    set((state) => ({
      sessionStreak: state.sessionStreak + 1,
      lastInteractionAt: new Date().toISOString(),
    })),
  resetSessionStreak: () => set({ sessionStreak: 0 }),
  setListening: (value) => set({ isListening: value }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  clearConversation: () => set({ messages: [], sessionId: null }),
}));
