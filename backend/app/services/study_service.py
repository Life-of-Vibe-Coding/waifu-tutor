from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Document, Flashcard, StudyProgress
from app.services.flashcard_service import FlashcardService


class StudyService:
    def __init__(self, flashcard_service: FlashcardService) -> None:
        self.flashcard_service = flashcard_service

    def get_progress(self, db: Session) -> dict:
        total_documents = db.scalar(select(func.count()).select_from(Document)) or 0
        total_flashcards = db.scalar(select(func.count()).select_from(Flashcard)) or 0
        cards_due = self.flashcard_service.cards_due(db)

        progress = db.scalar(select(StudyProgress).limit(1))
        cards_reviewed_today = progress.cards_reviewed_today if progress else 0
        average_score = progress.average_score if progress else 0.0

        return {
            "total_documents": int(total_documents),
            "total_flashcards": int(total_flashcards),
            "cards_due": int(cards_due),
            "cards_reviewed_today": int(cards_reviewed_today),
            "average_score": float(average_score),
        }
