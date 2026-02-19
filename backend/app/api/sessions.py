"""Conversation session APIs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.context import commit_openviking_session
from app.db.repositories import (
    get_chat_session,
    list_chat_messages,
    list_chat_sessions,
    mark_chat_session_committed,
)

router = APIRouter()


def _demo_user_id() -> str:
    return get_settings().demo_user_id


def _safe_limit(value: int, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


@router.get("")
def list_sessions(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    sessions = list_chat_sessions(_demo_user_id(), limit=_safe_limit(limit, 50))
    return {"sessions": sessions}


@router.get("/{session_id}")
def get_session(session_id: str, limit: int = Query(default=300, ge=1, le=1000)) -> dict:
    session = get_chat_session(session_id, _demo_user_id())
    if not session:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})
    messages = list_chat_messages(session_id, _demo_user_id(), limit=_safe_limit(limit, 300))
    return {"session": session, "messages": messages}


@router.post("/{session_id}/commit")
def commit_session(session_id: str) -> dict:
    user_id = _demo_user_id()
    session = get_chat_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})

    mark_chat_session_committed(session_id, user_id)
    messages = list_chat_messages(session_id, user_id, limit=1000)
    ov_commit = commit_openviking_session(
        session_id=session_id,
        user_id=user_id,
        history_messages=messages,
    )
    return {"session_id": session_id, "commit": {"status": "ok", "openviking": ov_commit}}
