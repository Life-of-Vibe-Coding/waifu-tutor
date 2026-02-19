"""FastAPI application entrypoint."""
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api import auth, chat, documents, health, not_implemented, sessions
from app.core.errors import ChatErrorCode, detail
from app.core.chat_logging import log_agent_context_startup
from app.core.text_logging import log_text
from app.db.session import init_db
from app.context import (
    get_agent_context_text,
    initialize_openviking_client,
    load_agent_context,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize DB and resources on startup."""
    initialize_openviking_client()
    init_db()
    load_agent_context()
    context_text = get_agent_context_text()
    log_agent_context_startup(context_text)
    log_text(context_text or "(empty)", section="AGENT CONTEXT (startup)")
    print("--- Agent context ---", flush=True)
    print(context_text if context_text else "(empty)", flush=True)
    print("---", flush=True)
    sys.stdout.flush()
    yield


def _validation_error_message(errors: list) -> str:
    """Turn FastAPI/Pydantic validation errors into a single user-facing message."""
    if not errors:
        return "Invalid request."
    first = errors[0]
    msg = first.get("msg", "Invalid request.")
    if isinstance(msg, str) and "ensure this value has at most" in msg:
        return "Message is too long. Please shorten it."
    if isinstance(msg, str) and "ensure this value has at least" in msg:
        return "Please enter a message."
    loc = first.get("loc", ())
    if loc and loc[-1] == "message":
        return msg if isinstance(msg, str) else "Invalid message."
    return msg if isinstance(msg, str) else "Invalid request."


def create_app() -> FastAPI:
    app = FastAPI(
        title="Waifu Tutor API",
        description="Backend for Waifu Tutor (auth, documents, chat, memory)",
        version="0.2.0",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request, exc: RequestValidationError):
        """Return structured { code, message } for 422 so the UI can show a single message."""
        errors = list(exc.errors()) if hasattr(exc, "errors") else []
        message = _validation_error_message(errors)
        return JSONResponse(
            status_code=400,
            content={"detail": detail(ChatErrorCode.INVALID_REQUEST, message)},
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
