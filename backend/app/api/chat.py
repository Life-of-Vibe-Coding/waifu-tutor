"""Chat: non-stream and SSE stream with OpenViking memory + file search."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.db.openviking_client import get_openviking_client, openviking_enabled
from app.db.repositories import get_document, insert_chat_message, mark_chat_session_committed, upsert_chat_session
from app.services.ai import DEFAULT_PERSONA, chat as ai_chat, mood_from_text
from app.services.file_search import ContextSearchService
from app.services.memory import MemoryManager

router = APIRouter()

FILE_SEARCH_TOP_N = 5


class ChatBody(BaseModel):
    message: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    doc_id: str | None = None
    session_id: str | None = None
    debug_search_trace: bool = False


def _demo_user_id() -> str:
    return get_settings().demo_user_id


def _normalize_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in history or []:
        role = str(item.get("role", "user") or "user").strip()
        content = str(item.get("content", "") or "").strip()
        if not content:
            continue
        if role not in ("user", "assistant", "system"):
            role = "user"
        out.append({"role": role, "content": content})
    return out


def _format_memory_item(mem: dict[str, Any]) -> str:
    return (
        str(mem.get("overview", "") or "").strip()
        or str(mem.get("abstract", "") or "").strip()
        or str(mem.get("match_reason", "") or "").strip()
        or str(mem.get("uri", "") or "").strip()
    )


def _build_context_texts(
    search_results: list[dict[str, Any]],
    long_term_memories: list[dict[str, Any]],
    session_ctx: dict[str, Any],
    short_term_ctx: list[dict[str, str]],
    request_history: list[dict[str, str]],
) -> list[str]:
    blocks: list[str] = []

    search_texts = [str(c.get("text", "")).strip() for c in search_results if str(c.get("text", "")).strip()]
    if search_texts:
        blocks.append("Context file search results:\n" + "\n".join(f"- {t}" for t in search_texts[:8]))

    memory_lines = [_format_memory_item(m) for m in long_term_memories]
    memory_lines = [m for m in memory_lines if m]
    if memory_lines:
        blocks.append("Long-term memory:\n" + "\n".join(f"- {m}" for m in memory_lines[:4]))

    summaries = [str(s).strip() for s in (session_ctx.get("summaries") or []) if str(s).strip()]
    if summaries:
        blocks.append("Session archive summaries:\n" + "\n".join(f"- {s}" for s in summaries[:3]))

    short_lines = [f"[{m['role']}] {m['content']}" for m in short_term_ctx[-10:] if m.get("content")]
    if short_lines:
        blocks.append("Recent live session turns:\n" + "\n".join(short_lines))

    req_lines = [f"[{m['role']}] {m['content']}" for m in request_history[-10:] if m.get("content")]
    if req_lines:
        blocks.append("Recent request history from client:\n" + "\n".join(req_lines))

    if not blocks:
        blocks.append("No additional memory context available.")
    return blocks


def _load_openviking_stack(session_id: str | None) -> tuple[MemoryManager | None, Any | None, ContextSearchService, str | None]:
    if not openviking_enabled():
        return None, None, ContextSearchService(None), "openviking_not_configured"
    try:
        client = get_openviking_client()
        memory = MemoryManager(client)
        session = memory.get_or_create_session(session_id)
        return memory, session, ContextSearchService(client), None
    except Exception as e:
        return None, None, ContextSearchService(None), str(e)


def _save_exchange(session_id: str, user_msg: str, assistant_msg: str) -> None:
    user_id = _demo_user_id()
    upsert_chat_session(session_id, user_id=user_id, title=user_msg[:80])
    insert_chat_message(str(uuid.uuid4()), session_id=session_id, user_id=user_id, role="user", content=user_msg)
    insert_chat_message(str(uuid.uuid4()), session_id=session_id, user_id=user_id, role="assistant", content=assistant_msg)


def _resolve_attachment_title(doc_id: str | None) -> str | None:
    if not doc_id:
        return None
    doc = get_document(doc_id, _demo_user_id())
    return doc.get("title") if doc else None


def _run_chat(body: ChatBody) -> dict[str, Any]:
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "Message required"})

    history = _normalize_history(body.history)
    memory, session, file_search, ov_error = _load_openviking_stack(body.session_id)
    session_id = body.session_id
    if memory is not None and session is not None:
        session_id = memory.session_id(session) or body.session_id or str(uuid.uuid4())
    if not session_id:
        session_id = str(uuid.uuid4())

    user_id = _demo_user_id()
    upsert_chat_session(session_id, user_id=user_id, title=msg[:80])

    search_results = file_search.search(
        msg,
        user_id=user_id,
        doc_id=body.doc_id,
        limit=FILE_SEARCH_TOP_N,
        session=session,
        include_trace=body.debug_search_trace,
    )
    search_error = file_search.last_error
    search_trace = file_search.last_trace

    if memory is not None and session is not None:
        uris = [str(c.get("uri", "")).strip() for c in search_results if str(c.get("uri", "")).strip()]
        memory.mark_used_contexts(session, uris)

    long_term = memory.get_long_term_memories(msg, limit=5) if memory is not None else []
    session_ctx = (
        memory.get_session_context(session, msg, max_archives=3, max_messages=20)
        if (memory is not None and session is not None)
        else {"summaries": [], "recent_messages": []}
    )
    short_term = (
        memory.get_short_term_context(session, limit=12)
        if (memory is not None and session is not None)
        else []
    )

    context_texts = _build_context_texts(
        search_results=search_results,
        long_term_memories=long_term,
        session_ctx=session_ctx,
        short_term_ctx=short_term,
        request_history=history,
    )
    attachment_title = _resolve_attachment_title(body.doc_id)

    # Persona from Viking agent instructions when available (viking://agent/instructions .abstract)
    persona: str | None = None
    if memory is not None:
        try:
            persona = (memory.client.abstract("viking://agent/instructions") or "").strip() or None
        except Exception:
            pass
    if not persona:
        persona = DEFAULT_PERSONA

    text, used_fallback = ai_chat(msg, context_texts, attachment_title, conversation_history=history, system_persona=persona)
    mood = mood_from_text(text)

    auto_commit_result: dict[str, Any] | None = None
    if memory is not None and session is not None:
        try:
            memory.record_exchange(session, msg, text)
            auto_commit_result = memory.maybe_auto_commit(session, max_messages=get_settings().openviking_auto_commit_turns)
        except Exception:
            pass
    _save_exchange(session_id, msg, text)

    if auto_commit_result and str(auto_commit_result.get("status", "")).lower() == "committed":
        mark_chat_session_committed(session_id, user_id)

    payload: dict[str, Any] = {
        "message": {"role": "assistant", "content": text, "created_at": datetime.now(tz=timezone.utc).isoformat()},
        "context": search_results,
        "mood": mood,
        "session_id": session_id,
        "model_fallback": used_fallback,
    }
    effective_ov_error = ov_error or search_error
    if effective_ov_error:
        payload["openviking_error"] = effective_ov_error
    if body.debug_search_trace:
        payload["search_trace"] = search_trace
        payload["auto_commit"] = auto_commit_result
    return payload


@router.post("/chat")
def chat(body: ChatBody) -> dict:
    return _run_chat(body)


def _build_chat_context(body: ChatBody) -> tuple[dict[str, Any], str, list[str], str | None, str, Any | None, Any | None]:
    """Build context (search, memory). Returns (context_payload, msg, context_texts, attachment_title, persona, memory, session)."""
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": "Message required"})

    history = _normalize_history(body.history)
    memory, session, file_search, ov_error = _load_openviking_stack(body.session_id)
    session_id = body.session_id
    if memory is not None and session is not None:
        session_id = memory.session_id(session) or body.session_id or str(uuid.uuid4())
    if not session_id:
        session_id = str(uuid.uuid4())

    user_id = _demo_user_id()
    upsert_chat_session(session_id, user_id=user_id, title=msg[:80])

    search_results = file_search.search(
        msg,
        user_id=user_id,
        doc_id=body.doc_id,
        limit=FILE_SEARCH_TOP_N,
        session=session,
        include_trace=body.debug_search_trace,
    )
    search_error = file_search.last_error
    search_trace = file_search.last_trace

    if memory is not None and session is not None:
        uris = [str(c.get("uri", "")).strip() for c in search_results if str(c.get("uri", "")).strip()]
        memory.mark_used_contexts(session, uris)

    long_term = memory.get_long_term_memories(msg, limit=5) if memory is not None else []
    session_ctx = (
        memory.get_session_context(session, msg, max_archives=3, max_messages=20)
        if (memory is not None and session is not None)
        else {"summaries": [], "recent_messages": []}
    )
    short_term = (
        memory.get_short_term_context(session, limit=12)
        if (memory is not None and session is not None)
        else []
    )

    context_texts = _build_context_texts(
        search_results=search_results,
        long_term_memories=long_term,
        session_ctx=session_ctx,
        short_term_ctx=short_term,
        request_history=history,
    )
    attachment_title = _resolve_attachment_title(body.doc_id)

    persona: str | None = None
    if memory is not None:
        try:
            persona = (memory.client.abstract("viking://agent/instructions") or "").strip() or None
        except Exception:
            pass
    if not persona:
        persona = DEFAULT_PERSONA

    effective_ov_error = ov_error or search_error
    context_payload: dict[str, Any] = {"context": search_results, "session_id": session_id}
    if effective_ov_error:
        context_payload["openviking_error"] = effective_ov_error
    if search_trace is not None:
        context_payload["search_trace"] = search_trace

    return context_payload, msg, context_texts, attachment_title, persona, memory, session


@router.post("/chat/stream")
def chat_stream(body: ChatBody) -> StreamingResponse:
    def event_stream():
        context_payload, msg, context_texts, attachment_title, persona, memory, session = _build_chat_context(body)
        yield f"event: context\ndata: {json.dumps(context_payload)}\n\n"

        history = _normalize_history(body.history)
        text, used_fallback = ai_chat(
            msg,
            context_texts,
            attachment_doc_title=attachment_title,
            conversation_history=history,
            system_persona=persona,
        )
        mood = mood_from_text(text)

        session_id = context_payload.get("session_id")
        effective_ov_error = context_payload.get("openviking_error")

        try:
            if memory is not None and session is not None:
                memory.record_exchange(session, msg, text)
                auto_commit_result = memory.maybe_auto_commit(session, max_messages=get_settings().openviking_auto_commit_turns)
                if auto_commit_result and str(auto_commit_result.get("status", "")).lower() == "committed":
                    mark_chat_session_committed(session_id, _demo_user_id())
        except Exception:
            pass
        _save_exchange(session_id, msg, text)

        for token in text.split():
            yield f"event: token\ndata: {json.dumps({'token': token, 'session_id': session_id})}\n\n"
        yield f"event: mood\ndata: {json.dumps({'mood': mood})}\n\n"
        done_payload: dict[str, Any] = {"message": text, "session_id": session_id, "model_fallback": used_fallback}
        if effective_ov_error:
            done_payload["openviking_error"] = effective_ov_error
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
