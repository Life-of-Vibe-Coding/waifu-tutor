"""Structured API error codes and helpers for consistent error responses."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

# Chat-specific limits (also enforced in Pydantic where applicable)
CHAT_MESSAGE_MAX_LENGTH = 32_768
CHAT_HISTORY_MAX_ITEMS = 100

# Error codes the frontend can use for UI behavior (e.g. inline vs banner)
class ChatErrorCode:
    MESSAGE_REQUIRED = "message_required"
    MESSAGE_TOO_LONG = "message_too_long"
    INVALID_REQUEST = "invalid_request"
    HISTORY_TOO_LONG = "history_too_long"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UPSTREAM_ERROR = "upstream_error"


def detail(code: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build a consistent error detail dict for JSON responses."""
    out: dict[str, Any] = {"code": code, "message": message}
    out.update(extra)
    return out


def raise_chat_validation(status_code: int, code: str, message: str, **extra: Any) -> None:
    """Raise HTTPException with structured detail for chat/validation errors."""
    raise HTTPException(status_code=status_code, detail=detail(code, message, **extra))
