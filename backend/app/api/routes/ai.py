from __future__ import annotations

from datetime import UTC, datetime
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.middleware.error_handler import ApiException
from app.models import Document, DocumentChunk, Flashcard, Summary
from app.schemas.contracts import (
    ChatContextChunk,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    FlashcardResponse,
    GenerateFlashcardsRequest,
    QuizFeedbackRequest,
    QuizFeedbackResponse,
    SummaryRequest,
    SummaryResponse,
)
from app.services.container import (
    get_ai_service,
    get_flashcard_service,
    get_search_service,
)
from app.services.ai_service import AIService
from app.services.flashcard_service import FlashcardService
from app.services.search_service import SearchService
from app.utils.mood import mood_from_score, mood_from_text
from app.utils.text import event_payload

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/summarize", response_model=SummaryResponse)
def summarize(
    payload: SummaryRequest,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
) -> SummaryResponse:
    document = db.get(Document, payload.doc_id)
    if not document:
        raise ApiException(code="not_found", message="Document not found", status_code=404)

    if not payload.force_refresh:
        cached = db.scalar(
            select(Summary).where(
                Summary.doc_id == payload.doc_id,
                Summary.detail_level == payload.detail_level,
            )
        )
        if cached:
            return SummaryResponse(
                doc_id=payload.doc_id,
                detail_level=payload.detail_level,
                summary_text=cached.summary_text,
                cached=True,
                generated_at=cached.generated_at,
            )

    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.doc_id == payload.doc_id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
    )
    full_text = "\n\n".join(chunk.chunk_text for chunk in chunks)
    if not full_text:
        raise ApiException(code="empty_document", message="No text available for summary", status_code=400)

    summary_text = ai_service.summarize(db=db, text=full_text, detail_level=payload.detail_level)
    summary = Summary(doc_id=payload.doc_id, detail_level=payload.detail_level, summary_text=summary_text)
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return SummaryResponse(
        doc_id=payload.doc_id,
        detail_level=payload.detail_level,
        summary_text=summary.summary_text,
        cached=False,
        generated_at=summary.generated_at,
    )


@router.post("/generate-flashcards", response_model=list[FlashcardResponse])
def generate_flashcards(
    payload: GenerateFlashcardsRequest,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
    flashcard_service: FlashcardService = Depends(get_flashcard_service),
) -> list[FlashcardResponse]:
    document = db.get(Document, payload.doc_id)
    if not document:
        raise ApiException(code="not_found", message="Document not found", status_code=404)

    existing = list(
        db.scalars(select(Flashcard).where(Flashcard.doc_id == payload.doc_id).limit(payload.max_cards)).all()
    )
    if existing:
        return [FlashcardResponse.model_validate(card) for card in existing]

    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.doc_id == payload.doc_id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
    )
    source_text = "\n".join(chunk.chunk_text for chunk in chunks)
    if not source_text:
        raise ApiException(code="empty_document", message="No text available for flashcards", status_code=400)

    cards = ai_service.generate_flashcards(db=db, text=source_text, max_cards=payload.max_cards)
    rows = flashcard_service.create_flashcards(db=db, doc_id=payload.doc_id, cards=cards)

    return [FlashcardResponse.model_validate(row) for row in rows]


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
    ai_service: AIService = Depends(get_ai_service),
) -> ChatResponse:
    context = search_service.hybrid_search(db=db, query=payload.message, doc_id=payload.doc_id, limit=6)
    message = ai_service.chat(db=db, prompt=payload.message, context=[item["text"] for item in context])
    mood = mood_from_text(message)

    return ChatResponse(
        message=ChatMessage(role="assistant", content=message, created_at=datetime.now(UTC)),
        context=[ChatContextChunk(**item) for item in context],
        mood=mood,
    )


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
    ai_service: AIService = Depends(get_ai_service),
):
    context = search_service.hybrid_search(db=db, query=payload.message, doc_id=payload.doc_id, limit=6)
    text = ai_service.chat(db=db, prompt=payload.message, context=[item["text"] for item in context])
    mood = mood_from_text(text)

    async def event_generator():
        yield f"event: context\ndata: {event_payload({'context': context})}\n\n"
        for token in text.split():
            yield f"event: token\ndata: {event_payload({'token': token})}\n\n"
        yield f"event: mood\ndata: {event_payload({'mood': mood})}\n\n"
        yield f"event: done\ndata: {event_payload({'message': text})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/quiz-feedback", response_model=QuizFeedbackResponse)
def quiz_feedback(
    payload: QuizFeedbackRequest,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
) -> QuizFeedbackResponse:
    _ = db
    ratio = SequenceMatcher(
        None,
        payload.expected_answer.lower().strip(),
        payload.user_answer.lower().strip(),
    ).ratio()
    score = int(ratio * 100)
    mood = mood_from_score(score)

    coaching_prompt = (
        "Give concise quiz feedback. Question, expected answer, student answer are below. "
        "Be constructive and encouraging.\n\n"
        f"Question: {payload.question}\n"
        f"Expected: {payload.expected_answer}\n"
        f"Student: {payload.user_answer}\n"
        f"Score: {score}"
    )
    feedback = ai_service.chat(db=db, prompt=coaching_prompt, context=[])

    return QuizFeedbackResponse(score=score, feedback=feedback, mood=mood)
