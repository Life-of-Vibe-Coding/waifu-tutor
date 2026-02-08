from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import DEMO_USER_ID
from app.models import AIUsageLog
from app.services.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = GeminiProvider()

    def summarize(self, db: Session, text: str, detail_level: str, endpoint: str = "summarize") -> str:
        started = time.perf_counter()
        result = self.provider.summarize(text=text, detail_level=detail_level)
        self._log_usage(db, endpoint=endpoint, latency_ms=int((time.perf_counter() - started) * 1000))
        return result

    def generate_flashcards(self, db: Session, text: str, max_cards: int) -> list[dict[str, str]]:
        started = time.perf_counter()
        cards = self.provider.generate_flashcards(text=text, max_cards=max_cards)
        self._log_usage(db, endpoint="generate-flashcards", latency_ms=int((time.perf_counter() - started) * 1000))
        return cards

    def chat(self, db: Session, prompt: str, context: list[str]) -> str:
        started = time.perf_counter()
        message = self.provider.chat(prompt=prompt, context=context)
        self._log_usage(db, endpoint="chat", latency_ms=int((time.perf_counter() - started) * 1000))
        return message

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.provider.embed(texts)

    def _log_usage(self, db: Session, endpoint: str, latency_ms: int) -> None:
        try:
            log = AIUsageLog(
                user_id=DEMO_USER_ID,
                endpoint=endpoint,
                model=self.settings.gemini_model,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=latency_ms,
                raw_response=None,
            )
            db.add(log)
            db.commit()
        except Exception as exc:  # pragma: no cover
            db.rollback()
            logger.warning("Failed to persist ai_usage_logs row: %s", exc)
