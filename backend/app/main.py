"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, documents, health, not_implemented, sessions
from app.db.openviking_client import close_openviking_client
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize DB and resources on startup."""
    init_db()
    yield
    close_openviking_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Waifu Tutor API",
        description="Backend for Waifu Tutor (auth, documents, chat, memory, OpenViking file search)",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Core routes
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    app.include_router(chat.router, prefix="/api/ai", tags=["chat"])
    app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])

    # Placeholder routers that return 501 (migrated later)
    app.include_router(not_implemented.router, prefix="/api/subjects", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/courses", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/ai/summarize", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/ai/generate-flashcards", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/flashcards", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/study", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/reminders", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/notes", tags=["not-implemented"])
    app.include_router(not_implemented.router, prefix="/api/gmail", tags=["not-implemented"])

    return app


app = create_app()
