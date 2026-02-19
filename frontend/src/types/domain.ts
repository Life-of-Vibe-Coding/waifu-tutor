export type CharacterMood = "happy" | "encouraging" | "sad" | "neutral" | "excited" | "gentle";
export type CompanionStatus = "idle" | "listening" | "thinking" | "celebrating" | "comforting";

export interface DocumentMeta {
  id: string;
  subject_id?: string | null;
  title: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: "processing" | "ready" | "failed";
  word_count: number;
  topic_hint?: string | null;
  difficulty_estimate?: string | null;
  created_at: string;
  updated_at: string;
  openviking_uri?: string | null;
  openviking_indexed?: boolean;
  openviking_error?: string | null;
  source_folder?: string | null;
  suggested_subject_id?: string | null;
  suggested_subject_name?: string | null;
  subject_needs_confirmation?: boolean;
}

export interface Subject {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
}

export interface SummaryResponse {
  doc_id: string;
  detail_level: "short" | "medium" | "detailed";
  summary_text: string;
  cached: boolean;
  generated_at: string;
}

export interface Flashcard {
  id: string;
  doc_id: string;
  question: string;
  answer: string;
  explanation?: string | null;
  created_at: string;
  repetitions: number;
  interval_days: number;
  ease_factor: number;
  last_reviewed_at?: string | null;
  next_review_at?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatContextChunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  source: "keyword" | "semantic" | "document";
  score: number;
  uri?: string;
}

export interface ReminderPayload {
  reminder_id: string;
  due_at: string;
  minutes: number;
  kind?: "break" | "focus";
}

export interface HitlCheckpointPayload {
  checkpoint_id: string;
  session_id: string;
  checkpoint: string;
  summary: string;
  params?: Record<string, unknown>;
  options?: string[];
  allow_free_input?: boolean;
}

export interface ChatResponse {
  message?: ChatMessage & { created_at?: string };
  context?: ChatContextChunk[];
  mood?: CharacterMood;
  session_id?: string;
  openviking_error?: string;
  rag_trace?: unknown;
  reminder?: ReminderPayload;
  /** When set, the client should show the checkpoint UI and call submitHitlResponse to resume. */
  hitl?: HitlCheckpointPayload;
}

export interface StudyProgress {
  total_documents: number;
  total_flashcards: number;
  cards_due: number;
  cards_reviewed_today: number;
  average_score: number;
}

export interface NoteFolder {
  id: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface StudyNote {
  id: string;
  folder_id: string | null;
  subject_id: string | null;
  doc_id: string | null;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}
