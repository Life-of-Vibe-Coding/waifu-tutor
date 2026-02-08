export type CharacterMood = "happy" | "encouraging" | "sad" | "neutral" | "excited";

export interface DocumentMeta {
  id: string;
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

export interface Reminder {
  id: string;
  title: string;
  note?: string | null;
  scheduled_for: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
  due_now: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatContextChunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  source: "keyword" | "semantic";
  score: number;
}

export interface ChatResponse {
  message: ChatMessage;
  context: ChatContextChunk[];
  mood: CharacterMood;
}

export interface StudyProgress {
  total_documents: number;
  total_flashcards: number;
  cards_due: number;
  cards_reviewed_today: number;
  average_score: number;
}
