"""Central scheduler for one-shot and recurring jobs (e.g. break/focus reminders)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.repositories import insert_reminder, set_reminder_due

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

DEFAULT_BREAK_MESSAGE = "Time to come back!"
DEFAULT_FOCUS_MESSAGE = "Focus session over! Consider a short break."


def _job_mark_reminder_due(reminder_id: str) -> None:
    try:
        set_reminder_due(reminder_id)
        logger.info("Reminder %s marked due", reminder_id)
    except Exception as e:
        logger.exception("Failed to mark reminder %s due: %s", reminder_id, e)


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
        logger.info("Scheduler started")
    return _scheduler


def schedule_reminder(
    session_id: str,
    user_id: str,
    minutes: int,
    message: str | None = None,
    kind: str = "break",
) -> tuple[str, str]:
    """Schedule a one-shot reminder. Returns (reminder_id, due_at_iso)."""
    minutes = max(1, min(120, minutes))
    due_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    due_at_iso = due_at.isoformat()
    reminder_id = str(uuid.uuid4())
    msg = (message or "").strip() or (DEFAULT_BREAK_MESSAGE if kind == "break" else DEFAULT_FOCUS_MESSAGE)
    insert_reminder(reminder_id, session_id, user_id, due_at_iso, msg, kind=kind)
    scheduler = get_scheduler()
    scheduler.add_job(
        _job_mark_reminder_due,
        "date",
        run_date=due_at,
        args=[reminder_id],
        id=reminder_id,
    )
    return reminder_id, due_at_iso


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
