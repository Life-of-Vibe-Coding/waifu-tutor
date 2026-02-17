import { apiClient } from "./api-client";
import type {
  ChatMessage,
  ChatResponse,
  DocumentMeta,
  Flashcard,
  NoteFolder,
  Reminder,
  StudyNote,
  StudyProgress,
  Subject,
  SummaryResponse,
} from "@/types/domain";

export interface StreamEvent {
  type: "token" | "context" | "mood" | "done" | "error";
  payload: unknown;
}

export const listDocuments = async (): Promise<DocumentMeta[]> => {
  const { data } = await apiClient.get<DocumentMeta[]>("/api/documents/list");
  return data;
};

export const listSubjects = async (): Promise<Subject[]> => {
  const { data } = await apiClient.get<Subject[]>("/api/subjects/list");
  return data;
};

export const confirmDocumentSubject = async (
  docId: string,
  subjectId: string
): Promise<DocumentMeta> => {
  const { data } = await apiClient.patch<DocumentMeta>(`/api/documents/${docId}`, {
    subject_id: subjectId,
  });
  return data;
};

export const setDocumentSubject = async (
  docId: string,
  subjectId: string | null
): Promise<DocumentMeta> => {
  const { data } = await apiClient.patch<DocumentMeta>(`/api/documents/${docId}`, {
    subject_id: subjectId,
  });
  return data;
};

export interface FetchCourseInput {
  url: string;
  mode?: "record" | "replay" | "qwen";
}

export interface FetchCourseRecordResponse {
  recorded: true;
  message: string;
}

export const fetchCourse = async (
  input: FetchCourseInput
): Promise<DocumentMeta | FetchCourseRecordResponse> => {
  const { data } = await apiClient.post<DocumentMeta | FetchCourseRecordResponse>(
    "/api/courses/fetch",
    input,
    { timeout: input.mode === "record" ? 360000 : 120000 }
  );
  return data;
};

export const uploadDocument = async (file: File): Promise<DocumentMeta> => {
  const form = new FormData();
  form.append("file", file);
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

export interface OrganizeMaterialsResponse {
  organization: string;
}

/** Ask agent to organize course materials (study order, topics, relations). Optional docIds; if omitted, uses all ready docs. */
export const organizeMaterials = async (
  docIds?: string[]
): Promise<OrganizeMaterialsResponse> => {
  const { data } = await apiClient.post<OrganizeMaterialsResponse>(
    "/api/ai/organize-materials",
    docIds?.length ? { doc_ids: docIds } : {}
  );
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
  patch: Partial<Pick<Reminder, "title" | "note" | "completed">> & { scheduled_for?: string }
): Promise<Reminder> => {
  const { data } = await apiClient.put<Reminder>(`/api/reminders/${reminderId}`, patch);
  return data;
};

export const deleteReminder = async (reminderId: string): Promise<void> => {
  await apiClient.delete(`/api/reminders/${reminderId}`);
};

// ─── Study notes ─────────────────────────────────────────────────────────────

export const listNoteFolders = async (): Promise<NoteFolder[]> => {
  const { data } = await apiClient.get<NoteFolder[]>("/api/notes/folders");
  return data;
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

/** Pass undefined for all notes, null or "" for unfiled only, or folder id for that folder. */
export const listNotes = async (folderId?: string | null): Promise<StudyNote[]> => {
  const params =
    folderId === undefined
      ? ""
      : `?folder_id=${encodeURIComponent(folderId === null ? "" : folderId)}`;
  const { data } = await apiClient.get<StudyNote[]>(`/api/notes${params}`);
  return data;
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

// ─── Gmail ──────────────────────────────────────────────────────────────────

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

export const chat = async (
  message: string,
  history: ChatMessage[],
  docId: string | null
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
  onEvent: (event: StreamEvent) => void
): Promise<void> => {
  const base = apiClient.defaults.baseURL || "";
  for (let attempt = 0; attempt <= 3; attempt++) {
    try {
      const response = await fetch(`${base}/api/ai/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history, doc_id: docId }),
      });
      if (!response.ok || !response.body) throw new Error("Failed to open chat stream");
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
              onEvent({
                type: currentEvent as StreamEvent["type"],
                payload: "data" in parsed ? parsed.data : parsed,
              });
            } catch {
              onEvent({ type: "error", payload: { message: "Malformed stream event" } });
            }
          }
        }
      }
      return;
    } catch (err) {
      if (attempt >= 3) throw err;
      await new Promise((r) => setTimeout(r, 300 * 2 ** attempt));
    }
  }
};
