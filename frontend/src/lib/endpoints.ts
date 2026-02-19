import { apiClient } from "./api-client";
import type {
  ChatMessage,
  ChatResponse,
  DocumentMeta,
  Flashcard,
  NoteFolder,
  StudyNote,
  StudyProgress,
  Subject,
  SummaryResponse,
} from "@/types/domain";

export interface ReminderPayload {
  reminder_id: string;
  due_at: string;
  minutes: number;
  kind?: "break" | "focus";
  stream_id?: string;
}

export interface StreamContextPayload {
  session_id?: string;
  stream_id?: string;
  [key: string]: unknown;
}

export interface StreamTokenPayload {
  token?: string;
  session_id?: string;
  stream_id?: string;
}

export interface StreamMoodPayload {
  mood?: string;
  stream_id?: string;
}

export interface StreamDonePayload {
  message?: string;
  session_id?: string;
  model_fallback?: boolean;
  reminder?: ReminderPayload;
  openviking_error?: string;
  stream_id?: string;
  hitl?: boolean;
}

export interface StreamHitlCheckpointPayload {
  checkpoint_id: string;
  session_id: string;
  checkpoint: string;
  summary: string;
  params?: Record<string, unknown>;
  options?: string[];
  allow_free_input?: boolean;
  stream_id?: string;
}

export interface StreamErrorPayload {
  message?: string;
  stream_id?: string;
}

export type StreamEvent =
  | { type: "token"; payload: StreamTokenPayload }
  | { type: "context"; payload: StreamContextPayload }
  | { type: "mood"; payload: StreamMoodPayload }
  | { type: "done"; payload: StreamDonePayload }
  | { type: "reminder"; payload: ReminderPayload }
  | { type: "hitl_checkpoint"; payload: StreamHitlCheckpointPayload }
  | { type: "error"; payload: StreamErrorPayload };

export const listDocuments = async (): Promise<DocumentMeta[]> => {
  const { data } = await apiClient.get<DocumentMeta[]>("/api/documents/list");
  return data;
};

export const listSubjects = async (): Promise<Subject[]> => {
  const { data } = await apiClient.get<Subject[]>("/api/subjects/list").catch(() => ({ data: [] }));
  return Array.isArray(data) ? data : [];
};

export const confirmDocumentSubject = async (docId: string, subjectId: string): Promise<DocumentMeta> => {
  const { data } = await apiClient.patch<DocumentMeta>(`/api/documents/${docId}`, { subject_id: subjectId });
  return data;
};

export const setDocumentSubject = async (docId: string, subjectId: string | null): Promise<DocumentMeta> => {
  const { data } = await apiClient.patch<DocumentMeta>(`/api/documents/${docId}`, { subject_id: subjectId });
  return data;
};

export const uploadDocument = async (
  file: File,
  folderName?: string | null
): Promise<DocumentMeta> => {
  const form = new FormData();
  form.append("file", file);
  if (folderName) form.append("folder_name", folderName);
  const { data } = await apiClient.post<DocumentMeta>("/api/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const summarizeDocument = async (
  docId: string,
  detailLevel: "short" | "medium" | "detailed"
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

export const listNoteFolders = async (): Promise<NoteFolder[]> => {
  const { data } = await apiClient.get<NoteFolder[]>("/api/notes/folders");
  return Array.isArray(data) ? data : [];
};

export const createNoteFolder = async (name: string, parentId?: string | null): Promise<NoteFolder> => {
  const { data } = await apiClient.post<NoteFolder>("/api/notes/folders", {
    name,
    parent_id: parentId ?? null,
  });
  return data;
};

export const updateNoteFolder = async (
  folderId: string,
  patch: Partial<Pick<NoteFolder, "name" | "sort_order">>
): Promise<NoteFolder> => {
  const { data } = await apiClient.patch<NoteFolder>(`/api/notes/folders/${folderId}`, patch);
  return data;
};

export const deleteNoteFolder = async (folderId: string): Promise<void> => {
  await apiClient.delete(`/api/notes/folders/${folderId}`);
};

export const listNotes = async (folderId?: string | null): Promise<StudyNote[]> => {
  const params =
    folderId === undefined
      ? ""
      : `?folder_id=${encodeURIComponent(folderId === null ? "" : folderId)}`;
  const { data } = await apiClient.get<StudyNote[]>(`/api/notes${params}`);
  return Array.isArray(data) ? data : [];
};

export const getNote = async (noteId: string): Promise<StudyNote> => {
  const { data } = await apiClient.get<StudyNote>(`/api/notes/${noteId}`);
  return data;
};

export const createNote = async (input: {
  title?: string;
  content?: string;
  folder_id?: string | null;
  subject_id?: string | null;
  doc_id?: string | null;
}): Promise<StudyNote> => {
  const { data } = await apiClient.post<StudyNote>("/api/notes", {
    title: input.title ?? "Untitled",
    content: input.content ?? "",
    folder_id: input.folder_id ?? null,
    subject_id: input.subject_id ?? null,
    doc_id: input.doc_id ?? null,
  });
  return data;
};

export const updateNote = async (
  noteId: string,
  patch: Partial<Pick<StudyNote, "title" | "content" | "folder_id" | "subject_id" | "doc_id">>
): Promise<StudyNote> => {
  const { data } = await apiClient.patch<StudyNote>(`/api/notes/${noteId}`, patch);
  return data;
};

export const deleteNote = async (noteId: string): Promise<void> => {
  await apiClient.delete(`/api/notes/${noteId}`);
};

export interface GmailStatus {
  configured: boolean;
  connected: boolean;
}

export const getGmailStatus = async (): Promise<GmailStatus> => {
  const { data } = await apiClient.get<GmailStatus>("/api/gmail/status");
  return data;
};

export const getGmailLoginUrl = async (): Promise<{ loginUrl: string }> => {
  const { data } = await apiClient.get<{ loginUrl: string }>("/api/gmail/auth");
  return data;
};

export const listGmailMail = async (
  maxResults = 25,
  q?: string
): Promise<{
  messages: Array<{ id: string; threadId: string }>;
  resultSizeEstimate?: number;
  nextPageToken?: string;
}> => {
  const params = new URLSearchParams({ maxResults: String(maxResults) });
  if (q) params.set("q", q);
  const { data } = await apiClient.get(`/api/gmail/mail?${params.toString()}`);
  return data;
};

export const sendGmailMail = async (params: {
  to: string | string[];
  subject: string;
  body: string;
  bodyIsHtml?: boolean;
}): Promise<void> => {
  await apiClient.post("/api/gmail/mail/send", params);
};

/** Recognized once at app load; never sent as a body parameter, only via X-User-Timezone header. */
const USER_TIMEZONE: string | null = (() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
})();

function chatHeaders(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (USER_TIMEZONE) h["X-User-Timezone"] = USER_TIMEZONE;
  return h;
}

export const chat = async (
  message: string,
  history: ChatMessage[],
  docId: string | null,
  sessionId: string | null
): Promise<ChatResponse> => {
  const { data } = await apiClient.post<ChatResponse>("/api/ai/chat", {
    message,
    history,
    doc_id: docId,
    session_id: sessionId,
  }, { headers: chatHeaders() });
  return data;
};

export type HitlResponsePayload =
  | { approved: true; overrides?: Record<string, unknown> }
  | { cancelled: true }
  | { selected: string }
  | { free_input: string };

export const submitHitlResponse = async (
  sessionId: string,
  checkpointId: string,
  response: HitlResponsePayload,
): Promise<ChatResponse> => {
  const { data } = await apiClient.post<ChatResponse>("/api/ai/chat/hitl-response", {
    session_id: sessionId,
    checkpoint_id: checkpointId,
    response,
  }, { headers: chatHeaders() });
  return data;
};

export interface InitialGreetingResponse {
  message: string | null;
  session_id: string | null;
}

export const getInitialGreeting = async (
  sessionId?: string | null
): Promise<InitialGreetingResponse> => {
  const { data } = await apiClient.post<InitialGreetingResponse>("/api/ai/initial-greeting", {
    session_id: sessionId ?? null,
  });
  return data;
};

export interface DueReminder {
  id: string;
  session_id: string;
  user_id: string;
  due_at: string;
  message: string;
  kind: string;
  status: string;
  created_at: string;
}

export const listDueReminders = async (sessionId: string): Promise<DueReminder[]> => {
  const { data } = await apiClient.get<DueReminder[]>("/api/ai/reminders", {
    params: { session_id: sessionId },
  });
  return Array.isArray(data) ? data : [];
};

export const ackReminder = async (reminderId: string): Promise<void> => {
  await apiClient.patch(`/api/ai/reminders/${reminderId}/ack`);
};

const STREAM_TIMEOUT_MS = 120000;

export const streamChat = async (
  message: string,
  history: ChatMessage[],
  docId: string | null,
  sessionId: string | null,
  onEvent: (event: StreamEvent) => void
): Promise<void> => {
  const base = apiClient.defaults.baseURL || "";
  const url = base ? `${base}/api/ai/chat/stream` : "/api/ai/chat/stream";
  for (let attempt = 0; attempt <= 3; attempt++) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: chatHeaders(),
        body: JSON.stringify({
          message,
          history,
          doc_id: docId,
          session_id: sessionId,
        }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const data = (await response.json().catch(() => ({
          detail: { code: "invalid_request", message: "Request failed" },
        }))) as { detail?: { code?: string; message?: string } | Array<{ msg?: string }> };
        const detailObj = data?.detail;
        const message =
          detailObj && typeof detailObj === "object" && !Array.isArray(detailObj) && typeof detailObj.message === "string"
            ? detailObj.message
            : Array.isArray(detailObj) && detailObj[0]?.msg
              ? String(detailObj[0].msg)
              : "Request failed";
        const err = Object.assign(new Error(message), {
          response: { status: response.status, data },
        });
        throw err;
      }
      if (!response.body) throw new Error("Failed to open chat stream");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("event: ")) currentEvent = line.replace("event: ", "").trim();
          if (line.startsWith("data: ")) {
            try {
              const parsed = JSON.parse(line.replace("data: ", "").trim()) as Record<string, unknown>;
              const eventType = currentEvent as StreamEvent["type"];
              const payload = ("data" in parsed ? parsed.data : parsed) as StreamEvent["payload"];
              onEvent({ type: eventType, payload } as StreamEvent);
            } catch {
              onEvent({ type: "error", payload: { message: "Malformed stream event" } });
            }
          }
        }
      }
      window.clearTimeout(timeoutId);
      return;
    } catch (err) {
      window.clearTimeout(timeoutId);
      if (attempt >= 3) throw err;
      await new Promise((r) => setTimeout(r, 300 * 2 ** attempt));
    }
  }
};
