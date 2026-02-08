export type CharacterMood = "happy" | "encouraging" | "sad" | "neutral" | "excited";

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  profile: UserProfile;
}

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

export interface SummaryRequest {
  doc_id: string;
  detail_level: "short" | "medium" | "detailed";
  force_refresh?: boolean;
}

export interface SummaryResponse {
  doc_id: string;
  detail_level: SummaryRequest["detail_level"];
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

export interface ReviewUpdate {
  quality: 0 | 1 | 2 | 3 | 4 | 5;
  user_answer?: string;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface ChatContextChunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  source: "keyword" | "semantic";
  score: number;
}

export interface ChatRequest {
  doc_id?: string;
  message: string;
  history: ChatMessage[];
  tts_enabled?: boolean;
}

export interface ChatResponse {
  message: ChatMessage;
  context: ChatContextChunk[];
  mood: CharacterMood;
}

export interface QuizFeedbackRequest {
  question: string;
  expected_answer: string;
  user_answer: string;
}

export interface QuizFeedbackResponse {
  score: number;
  feedback: string;
  mood: CharacterMood;
}

export interface Reminder {
  id: string;
  title: string;
  note?: string | null;
  scheduled_for: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
  due_now?: boolean;
}

export interface StudyProgress {
  total_documents: number;
  total_flashcards: number;
  cards_due: number;
  cards_reviewed_today: number;
  average_score: number;
}

export interface SseEvent<T = unknown> {
  event_id: string;
  timestamp: string;
  data: T;
}
