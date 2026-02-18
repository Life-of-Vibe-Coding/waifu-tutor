"""Memory manager built on top of OpenViking sessions/search."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        out: dict[str, Any] = {}
        for f in fields(value):
            try:
                out[f.name] = _to_plain(getattr(value, f.name))
            except Exception:
                out[f.name] = None
        return out
    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump())
        except Exception:
            pass
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if hasattr(value, "__dict__") and not isinstance(value, (str, bytes, int, float, bool)):
        out: dict[str, Any] = {}
        for k, v in value.__dict__.items():
            if k.startswith("_"):
                continue
            try:
                out[k] = _to_plain(v)
            except Exception:
                continue
        if out:
            return out
    return value


def _message_text(msg: Any) -> str:
    content = getattr(msg, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    parts = getattr(msg, "parts", []) or []
    chunks: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())
    return "\n".join(chunks).strip()


class MemoryManager:
    """High-level memory operations around OpenViking session primitives."""

    def __init__(self, ov_client: Any):
        self.client = ov_client

    def get_or_create_session(self, session_id: str | None):
        if session_id:
            return self.client.session(session_id=session_id)
        return self.client.session()

    def session_id(self, session: Any) -> str | None:
        sid = getattr(session, "session_id", None)
        if isinstance(sid, str) and sid.strip():
            return sid
        uri = str(getattr(session, "uri", "") or "")
        if uri.startswith("viking://session/"):
            return uri.rsplit("/", 1)[-1]
        return None

    def get_short_term_context(self, session: Any, limit: int = 10) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for msg in (getattr(session, "messages", []) or [])[-limit:]:
            text = _message_text(msg)
            if not text:
                continue
            role = str(getattr(msg, "role", "assistant") or "assistant")
            out.append({"role": role, "content": text})
        return out

    def get_session_context(self, session: Any, query: str, max_archives: int = 3, max_messages: int = 20) -> dict[str, Any]:
        try:
            raw = session.get_context_for_search(query, max_archives=max_archives, max_messages=max_messages)
        except Exception:
            return {"summaries": [], "recent_messages": []}
        summaries = raw.get("summaries") if isinstance(raw, dict) else []
        recent_raw = raw.get("recent_messages") if isinstance(raw, dict) else []
        recent: list[dict[str, str]] = []
        for msg in recent_raw or []:
            text = _message_text(msg)
            if not text:
                continue
            role = str(getattr(msg, "role", "assistant") or "assistant")
            recent.append({"role": role, "content": text})
        return {"summaries": summaries or [], "recent_messages": recent}

    def get_long_term_memories(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            result = self.client.search(query, limit=limit)
        except Exception:
            return []
        memories = getattr(result, "memories", []) or []
        return [_to_plain(m) for m in memories]

    def add_message(self, session: Any, role: str, text: str) -> None:
        payload = (text or "").strip()
        if not payload:
            return
        from openviking.message import TextPart

        session.add_message(role, [TextPart(text=payload)])

    def record_exchange(self, session: Any, user_msg: str, assistant_msg: str) -> None:
        self.add_message(session, "user", user_msg)
        self.add_message(session, "assistant", assistant_msg)

    def mark_used_contexts(self, session: Any, uris: list[str]) -> None:
        clean = [u for u in uris if isinstance(u, str) and u.strip()]
        if not clean:
            return
        try:
            session.used(contexts=clean)
        except Exception:
            pass

    def maybe_auto_commit(self, session: Any, max_messages: int) -> dict[str, Any] | None:
        """Auto-commit session when pending messages exceed threshold."""
        msgs = getattr(session, "messages", []) or []
        if len(msgs) < max_messages:
            return None
        return self.commit_session(session)

    def commit_session(self, session: Any) -> dict[str, Any]:
        try:
            return _to_plain(session.commit()) or {}
        except Exception as e:
            return {"status": "failed", "message": str(e)}
