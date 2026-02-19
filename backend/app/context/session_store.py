"""OpenViking session store and lifecycle helpers."""
from __future__ import annotations

from threading import RLock
from typing import Any

from app.core.config import get_settings
from app.context.openviking_client import get_openviking_client
from app.context.openviking_types import MemoryFallbackSession, SessionLike, TextPart

_STORE: dict[str, SessionLike] = {}
_LOCK = RLock()


def _session_runtime_config() -> dict[str, Any]:
    return get_settings().openviking_session_conf()


def _enforce_capacity(max_cached: int) -> None:
    while len(_STORE) > max_cached:
        oldest_session_id = next(iter(_STORE.keys()))
        _STORE.pop(oldest_session_id, None)


def _try_load_session(session: SessionLike) -> None:
    try:
        session.load()
    except Exception:
        return None


def _session_message_count(session: SessionLike) -> int:
    try:
        return len(getattr(session, "messages", []) or [])
    except Exception:
        return 0


def _new_session(session_id: str, user_id: str) -> SessionLike:
    client = get_openviking_client()
    if client is not None:
        try:
            session = client.session(session_id=session_id)
            _try_load_session(session)
            return session
        except Exception:
            pass
    return MemoryFallbackSession(session_id=session_id, user_id=user_id)


def _hydrate_from_history(session: SessionLike, history_messages: list[dict[str, Any]] | None) -> None:
    if _session_message_count(session) > 0:
        return
    for item in history_messages or []:
        role = str(item.get("role", "user") or "user")
        content = str(item.get("content", "") or "").strip()
        if not content:
            continue
        session.add_message(role, [TextPart(content)])


def put_openviking_session(session: SessionLike) -> SessionLike:
    """Insert or replace a cached OpenViking session."""
    with _LOCK:
        cfg = _session_runtime_config()
        _STORE[session.session_id] = session
        _enforce_capacity(int(cfg.get("max_cached", 1000)))
    return session


def get_openviking_session(session_id: str) -> SessionLike | None:
    """Fetch an OpenViking session by ID."""
    with _LOCK:
        return _STORE.get(session_id)


def ensure_openviking_session(
    *,
    session_id: str,
    user_id: str,
    history_messages: list[dict[str, Any]] | None = None,
) -> SessionLike:
    """Return existing session or hydrate one from message history."""
    with _LOCK:
        existing = _STORE.get(session_id)
        if existing is not None:
            return existing

        session = _new_session(session_id=session_id, user_id=user_id)
        _hydrate_from_history(session, history_messages)
        _STORE[session_id] = session
        _enforce_capacity(int(_session_runtime_config().get("max_cached", 1000)))
        return session


def append_openviking_text_message(session_id: str, role: str, content: str) -> bool:
    """Append a text message to an existing OpenViking session."""
    clean_content = (content or "").strip()
    if not clean_content:
        return False
    with _LOCK:
        session = _STORE.get(session_id)
        if session is None:
            session = _new_session(session_id=session_id, user_id=get_settings().demo_user_id)
            _STORE[session_id] = session
            _enforce_capacity(int(_session_runtime_config().get("max_cached", 1000)))
        session.add_message(role, [TextPart(clean_content)])
        return True


def record_openviking_session_usage(
    session_id: str,
    *,
    contexts: list[str] | None = None,
    skill: dict[str, Any] | None = None,
) -> bool:
    """Record contexts/skills usage for a cached session."""
    if not contexts and not skill:
        return False
    with _LOCK:
        session = _STORE.get(session_id)
        if session is None:
            return False
        try:
            session.used(contexts=contexts, skill=skill)
            return True
        except Exception:
            return False


def commit_openviking_session(
    *,
    session_id: str,
    user_id: str,
    history_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Commit an OpenViking session, hydrating from history if needed."""
    cfg = _session_runtime_config()
    backend = "openviking" if get_openviking_client() is not None else str(cfg.get("backend", "memory"))

    should_hydrate = bool(cfg.get("hydrate_on_commit", True))
    with _LOCK:
        session = _STORE.get(session_id)
        if session is None and should_hydrate:
            session = _new_session(session_id=session_id, user_id=user_id)
            _hydrate_from_history(session, history_messages)
            _STORE[session_id] = session
            _enforce_capacity(int(cfg.get("max_cached", 1000)))
        if session is None:
            session = _new_session(session_id=session_id, user_id=user_id)
            _STORE[session_id] = session
            _enforce_capacity(int(cfg.get("max_cached", 1000)))
        before_commit_messages = _session_message_count(session)
        out = session.commit()
        out["backend"] = backend
        out["session_messages"] = before_commit_messages
        return out
