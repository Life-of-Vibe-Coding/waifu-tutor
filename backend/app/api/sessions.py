"""Conversation session APIs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.db.openviking_client import get_openviking_client, openviking_enabled
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


def _to_plain(value) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return {k: v for k, v in vars(value).items() if not str(k).startswith("_")}
        except Exception:
            pass
    return {}


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
    session = get_chat_session(session_id, _demo_user_id())
    if not session:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Session not found"})

    try:
        if openviking_enabled():
            ov_session = get_openviking_client().session(session_id=session_id)
            commit_result = _to_plain(ov_session.commit()) or {"status": "ok"}
        else:
            commit_result = {"status": "ok", "message": "OpenViking not configured"}
    except Exception as e:
        commit_result = {"status": "failed", "message": str(e)}

    mark_chat_session_committed(session_id, _demo_user_id())
    return {"session_id": session_id, "commit": commit_result}
