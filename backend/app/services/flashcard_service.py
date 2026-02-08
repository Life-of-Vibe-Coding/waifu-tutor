from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Flashcard, FlashcardReview, StudyProgress


class FlashcardService:
    def list_flashcards(self, db: Session, doc_id: str) -> list[Flashcard]:
        return list(
            db.scalars(
                select(Flashcard)
                .where(Flashcard.doc_id == doc_id)
                .order_by(Flashcard.created_at.asc())
            ).all()
        )

    def create_flashcards(self, db: Session, doc_id: str, cards: list[dict[str, str]]) -> list[Flashcard]:
        rows: list[Flashcard] = []
        for card in cards:
            row = Flashcard(
                doc_id=doc_id,
                question=card.get("question", ""),
                answer=card.get("answer", ""),
                explanation=card.get("explanation"),
                repetitions=0,
                interval_days=1,
                ease_factor=2.5,
            )
            rows.append(row)

        db.add_all(rows)
        db.commit()
        for row in rows:
            db.refresh(row)
        return rows

    def review_flashcard(
        self,
        db: Session,
        card: Flashcard,
        quality: int,
        user_answer: str | None = None,
    ) -> Flashcard:
        now = datetime.now(UTC)
        repetitions = card.repetitions
        interval = card.interval_days
        ease = card.ease_factor

        if quality < 3:
            repetitions = 0
            interval = 1
        else:
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = max(1, int(round(interval * ease)))
            repetitions += 1

        ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        card.repetitions = repetitions
        card.interval_days = interval
        card.ease_factor = ease
        card.last_reviewed_at = now
        card.next_review_at = now + timedelta(days=interval)

        db.add(
            FlashcardReview(
                card_id=card.id,
                quality=quality,
                repetitions=repetitions,
                interval_days=interval,
                ease_factor=ease,
                user_answer=user_answer,
            )
        )

        progress = db.scalar(select(StudyProgress).limit(1))
        if progress:
            total_reviews = progress.total_reviews + 1
            progress.cards_reviewed_today = progress.cards_reviewed_today + 1
            progress.average_score = ((progress.average_score * progress.total_reviews) + quality) / total_reviews
            progress.total_reviews = total_reviews

        db.commit()
        db.refresh(card)
        return card

    def cards_due(self, db: Session) -> int:
        now = datetime.now(UTC)
        due = db.scalar(
            select(func.count())
            .select_from(Flashcard)
            .where(Flashcard.next_review_at.is_not(None), Flashcard.next_review_at <= now)
        )
        return int(due or 0)
