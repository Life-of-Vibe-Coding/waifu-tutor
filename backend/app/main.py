from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import ai, auth, documents, flashcards, health, reminders, study, user
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.database import SessionLocal
from app.db.init_db import create_all, ensure_fts, seed_demo_user
from app.middleware.error_handler import ApiException, api_exception_handler, unhandled_exception_handler
from app.middleware.rate_limit import SimpleRateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.services.container import get_reminder_service, get_vector_service

logger = logging.getLogger(__name__)
settings = get_settings()


def _scheduler_job() -> None:
    db: Session = SessionLocal()
    try:
        reminder_service = get_reminder_service()
        notified = reminder_service.mark_due_notifications(db)
        if notified:
            logger.info("Reminder scheduler marked %s due reminders for notification", notified)
    except Exception:
        logger.exception("Reminder scheduler job failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    create_all()

    db: Session = SessionLocal()
    try:
        ensure_fts(db)
        seed_demo_user(db)
    finally:
        db.close()

    vector_service = get_vector_service()
    vector_service.ensure_collection()

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(_scheduler_job, trigger="interval", minutes=1, id="due-reminder-job")
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="Waifu Tutor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SimpleRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiException, api_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(flashcards.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")
