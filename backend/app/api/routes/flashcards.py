from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.middleware.error_handler import ApiException
from app.models import Flashcard
from app.schemas.contracts import FlashcardResponse, ReviewUpdateRequest
from app.services.container import get_flashcard_service
from app.services.flashcard_service import FlashcardService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("/{doc_id}", response_model=list[FlashcardResponse])
def list_flashcards(
    doc_id: str,
    db: Session = Depends(get_db),
    service: FlashcardService = Depends(get_flashcard_service),
) -> list[FlashcardResponse]:
    cards = service.list_flashcards(db=db, doc_id=doc_id)
    return [FlashcardResponse.model_validate(card) for card in cards]


@router.post("/{card_id}/review", response_model=FlashcardResponse)
def review_flashcard(
    card_id: str,
    payload: ReviewUpdateRequest,
    db: Session = Depends(get_db),
    service: FlashcardService = Depends(get_flashcard_service),
) -> FlashcardResponse:
    card = db.get(Flashcard, card_id)
    if not card:
        raise ApiException(code="not_found", message="Flashcard not found", status_code=404)
    updated = service.review_flashcard(
        db=db,
        card=card,
        quality=payload.quality,
        user_answer=payload.user_answer,
    )
    return FlashcardResponse.model_validate(updated)
