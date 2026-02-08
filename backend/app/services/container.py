from functools import lru_cache

from app.services.ai_service import AIService
from app.services.document_service import DocumentService
from app.services.flashcard_service import FlashcardService
from app.services.reminder_service import ReminderService
from app.services.search_service import SearchService
from app.services.study_service import StudyService
from app.services.vector_service import VectorService


@lru_cache
def get_ai_service() -> AIService:
    return AIService()


@lru_cache
def get_vector_service() -> VectorService:
    return VectorService()


@lru_cache
def get_document_service() -> DocumentService:
    return DocumentService(ai_service=get_ai_service(), vector_service=get_vector_service())


@lru_cache
def get_flashcard_service() -> FlashcardService:
    return FlashcardService()


@lru_cache
def get_reminder_service() -> ReminderService:
    return ReminderService()


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(ai_service=get_ai_service(), vector_service=get_vector_service())


@lru_cache
def get_study_service() -> StudyService:
    return StudyService(flashcard_service=get_flashcard_service())
