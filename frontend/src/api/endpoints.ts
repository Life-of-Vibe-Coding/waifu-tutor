import { apiClient } from "./client";
import type {
  ChatMessage,
  ChatResponse,
  DocumentMeta,
  Flashcard,
  Reminder,
  StudyProgress,
  SummaryResponse,
} from "../types/domain";

export interface StreamEvent {
  type: "token" | "context" | "mood" | "done" | "error";
  payload: any;
}

export const listDocuments = async (): Promise<DocumentMeta[]> => {
  const { data } = await apiClient.get<DocumentMeta[]>("/api/documents/list");
  return data;
};

export const uploadDocument = async (file: File): Promise<DocumentMeta> => {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<DocumentMeta>("/api/documents/upload", form, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return data;
};

export const summarizeDocument = async (
  docId: string,
  detailLevel: "short" | "medium" | "detailed",
): Promise<SummaryResponse> => {
  const { data } = await apiClient.post<SummaryResponse>("/api/ai/summarize", {
    doc_id: docId,
    detail_level: detailLevel,
  });
  return data;
};

export const generateFlashcards = async (docId: string): Promise<Flashcard[]> => {
  const { data } = await apiClient.post<Flashcard[]>("/api/ai/generate-flashcards", {
    doc_id: docId,
    max_cards: 12,
  });
  return data;
};

export const listFlashcards = async (docId: string): Promise<Flashcard[]> => {
  const { data } = await apiClient.get<Flashcard[]>(`/api/flashcards/${docId}`);
  return data;
};

export const reviewFlashcard = async (cardId: string, quality: number, userAnswer?: string) => {
  const { data } = await apiClient.post<Flashcard>(`/api/flashcards/${cardId}/review`, {
    quality,
    user_answer: userAnswer,
  });
  return data;
};

export const getProgress = async (): Promise<StudyProgress> => {
  const { data } = await apiClient.get<StudyProgress>("/api/study/progress");
  return data;
};

export const listReminders = async (): Promise<Reminder[]> => {
  const { data } = await apiClient.get<Reminder[]>("/api/reminders/list");
  return data;
};

export const createReminder = async (title: string, note: string, scheduledFor: string): Promise<Reminder> => {
  const { data } = await apiClient.post<Reminder>("/api/reminders/create", {
    title,
    note,
    scheduled_for: scheduledFor,
  });
  return data;
};

export const updateReminder = async (
  reminderId: string,
  patch: Partial<Pick<Reminder, "title" | "note" | "completed">> & { scheduled_for?: string },
): Promise<Reminder> => {
  const { data } = await apiClient.put<Reminder>(`/api/reminders/${reminderId}`, patch);
  return data;
};

export const deleteReminder = async (reminderId: string): Promise<void> => {
  await apiClient.delete(`/api/reminders/${reminderId}`);
};

export const chat = async (
  message: string,
  history: ChatMessage[],
  docId: string | null,
): Promise<ChatResponse> => {
  const { data } = await apiClient.post<ChatResponse>("/api/ai/chat", {
    message,
    history,
    doc_id: docId,
  });
  return data;
};

export const streamChat = async (
  message: string,
  history: ChatMessage[],
  docId: string | null,
  onEvent: (event: StreamEvent) => void,
): Promise<void> => {
  const maxRetries = 3;
  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    try {
      const response = await fetch(`${apiClient.defaults.baseURL}/api/ai/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message, history, doc_id: docId }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Failed to open chat stream");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.replace("event: ", "").trim();
          }
          if (line.startsWith("data: ")) {
            const raw = line.replace("data: ", "").trim();
            try {
              const parsed = JSON.parse(raw);
              onEvent({ type: currentEvent as StreamEvent["type"], payload: parsed.data });
            } catch {
              onEvent({ type: "error", payload: { message: "Malformed stream event" } });
            }
          }
        }
      }

      return;
    } catch (error) {
      if (attempt >= maxRetries) {
        throw error;
      }
      const delayMs = 300 * 2 ** attempt;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
};
