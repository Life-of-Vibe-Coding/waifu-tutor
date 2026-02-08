from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    display_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    profile: UserProfile


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class DocumentMetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    word_count: int
    topic_hint: str | None = None
    difficulty_estimate: str | None = None
    created_at: datetime
    updated_at: datetime


class SummaryRequest(BaseModel):
    doc_id: str
    detail_level: Literal["short", "medium", "detailed"] = "medium"
    force_refresh: bool = False


class SummaryResponse(BaseModel):
    doc_id: str
    detail_level: Literal["short", "medium", "detailed"]
    summary_text: str
    cached: bool
    generated_at: datetime


class FlashcardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doc_id: str
    question: str
    answer: str
    explanation: str | None = None
    created_at: datetime
    repetitions: int
    interval_days: int
    ease_factor: float
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None


class ReviewUpdateRequest(BaseModel):
    quality: int = Field(ge=0, le=5)
    user_answer: str | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    created_at: datetime | None = None


class ChatContextChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    source: Literal["keyword", "semantic"]
    score: float


class ChatRequest(BaseModel):
    doc_id: str | None = None
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    tts_enabled: bool = False


class ChatResponse(BaseModel):
    message: ChatMessage
    context: list[ChatContextChunk]
    mood: Literal["happy", "encouraging", "sad", "neutral", "excited"]


class QuizFeedbackRequest(BaseModel):
    question: str
    expected_answer: str
    user_answer: str


class QuizFeedbackResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    feedback: str
    mood: Literal["happy", "encouraging", "sad", "neutral", "excited"]


class ReminderCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    note: str | None = None
    scheduled_for: datetime


class ReminderUpdateRequest(BaseModel):
    title: str | None = None
    note: str | None = None
    scheduled_for: datetime | None = None
    completed: bool | None = None


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    note: str | None = None
    scheduled_for: datetime
    completed: bool
    created_at: datetime
    updated_at: datetime
    due_now: bool


class StudyProgressResponse(BaseModel):
    total_documents: int
    total_flashcards: int
    cards_due: int
    cards_reviewed_today: int
    average_score: float


class GenerateFlashcardsRequest(BaseModel):
    doc_id: str
    max_cards: int = Field(default=12, ge=1, le=40)


class SSEPayload(BaseModel):
    event_id: str
    timestamp: datetime
    data: dict[str, Any]
