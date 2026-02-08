from __future__ import annotations

from datetime import UTC, datetime
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import DEMO_USER_ID
from app.models import Reminder

logger = logging.getLogger(__name__)


class ReminderService:
    def create(self, db: Session, title: str, note: str | None, scheduled_for: datetime) -> Reminder:
        reminder = Reminder(
            user_id=DEMO_USER_ID,
            title=title,
            note=note,
            scheduled_for=scheduled_for,
            completed=False,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder

    def list(self, db: Session) -> list[Reminder]:
        return list(
            db.scalars(
                select(Reminder)
                .where(Reminder.user_id == DEMO_USER_ID)
                .order_by(Reminder.scheduled_for.asc())
            ).all()
        )

    def get(self, db: Session, reminder_id: str) -> Reminder | None:
        return db.scalar(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == DEMO_USER_ID)
        )

    def update(
        self,
        db: Session,
        reminder: Reminder,
        title: str | None,
        note: str | None,
        scheduled_for: datetime | None,
        completed: bool | None,
    ) -> Reminder:
        if title is not None:
            reminder.title = title
        if note is not None:
            reminder.note = note
        if scheduled_for is not None:
            reminder.scheduled_for = scheduled_for
        if completed is not None:
            reminder.completed = completed
        db.commit()
        db.refresh(reminder)
        return reminder

    def delete(self, db: Session, reminder: Reminder) -> None:
        db.delete(reminder)
        db.commit()

    def is_due(self, reminder: Reminder) -> bool:
        if reminder.completed:
            return False
        return reminder.scheduled_for <= datetime.now(UTC)

    def mark_due_notifications(self, db: Session) -> int:
        now = datetime.now(UTC)
        due = list(
            db.scalars(
                select(Reminder).where(
                    Reminder.user_id == DEMO_USER_ID,
                    Reminder.completed.is_(False),
                    Reminder.scheduled_for <= now,
                )
            ).all()
        )

        notified = 0
        for reminder in due:
            if (
                reminder.last_notified_at is None
                or (now - reminder.last_notified_at).total_seconds() > 3600
            ):
                reminder.last_notified_at = now
                notified += 1
        if notified:
            db.commit()
        return notified
