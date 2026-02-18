"""Chat: non-stream and SSE stream with OpenViking-backed file search."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.errors import (
    CHAT_HISTORY_MAX_ITEMS,
    CHAT_MESSAGE_MAX_LENGTH,
    ChatErrorCode,
    raise_chat_validation,
)
from app.db.openviking_client import get_openviking_client, openviking_enabled
from app.db.repositories import (
    get_document,
    insert_chat_message,
    list_due_reminders,
    list_subjects,
    mark_reminder_acknowledged,
    mark_chat_session_committed,
    upsert_chat_session,
)
from app.services.ai import chat as ai_chat, complete_with_tools, mood_from_text
from app.services.file_search import ContextSearchService
from app.core.chat_logging import (
    log_chat_context,
    log_chat_final_response,
    log_chat_llm_round,
    log_chat_request,
)
from app.services.tools import CHAT_TOOLS, execute_tool
from app.services.user_profile import (
    is_first_time_user,
    parse_profile_line,
    read_user_profile,
    strip_profile_line,
    write_user_profile,
)

router = APIRouter()

FILE_SEARCH_TOP_N = 5


class ChatBody(BaseModel):
    message: str = Field(..., max_length=CHAT_MESSAGE_MAX_LENGTH)
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=CHAT_HISTORY_MAX_ITEMS)
    doc_id: str | None = None
    session_id: str | None = None
    debug_search_trace: bool = False


class AnalyzeFilesBody(BaseModel):
    filenames: list[str]
    session_id: str | None = None
    timezone: str | None = None  # IANA timezone (e.g. America/Los_Angeles) for get_current_time


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


def _build_context_texts(
    search_results: list[dict[str, Any]],
) -> list[str]:
    """Build context from file search results only."""
    blocks: list[str] = []
    search_texts = [str(c.get("text", "")).strip() for c in search_results if str(c.get("text", "")).strip()]
    if search_texts:
        blocks.append("Context file search results:\n" + "\n".join(f"- {t}" for t in search_texts[:8]))
    return blocks


def _to_plain(value: Any) -> dict[str, Any]:
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


def _load_openviking_stack(session_id: str | None) -> tuple[Any | None, ContextSearchService]:
    """Load OpenViking client/session and file search. Fallback to chunk search when unavailable."""
    if openviking_enabled():
        client = get_openviking_client()
        try:
            if session_id:
                return client.session(session_id=session_id), ContextSearchService(client)
            return client.session(), ContextSearchService(client)
        except Exception:
            return None, ContextSearchService(client)
    return None, ContextSearchService(None)


def _session_id(session: Any) -> str | None:
    sid = getattr(session, "session_id", None)
    if isinstance(sid, str) and sid.strip():
        return sid
    uri = str(getattr(session, "uri", "") or "")
    if uri.startswith("viking://session/"):
        return uri.rsplit("/", 1)[-1]
    return None


def _mark_used_contexts(session: Any, uris: list[str]) -> None:
    if session is None:
        return
    clean = [u for u in uris if isinstance(u, str) and u.strip()]
    if not clean:
        return
    try:
        session.used(contexts=clean)
    except Exception:
        pass


def _record_exchange(session: Any, user_msg: str, assistant_msg: str) -> None:
    if session is None:
        return
    user_text = (user_msg or "").strip()
    assistant_text = (assistant_msg or "").strip()
    if not user_text and not assistant_text:
        return
    try:
        text_part_mod = __import__("openviking.message", fromlist=["TextPart"])
        TextPart = getattr(text_part_mod, "TextPart")
    except Exception:
        return
    if user_text:
        session.add_message("user", [TextPart(text=user_text)])
    if assistant_text:
        session.add_message("assistant", [TextPart(text=assistant_text)])


def _commit_session(session: Any) -> dict[str, Any]:
    if session is None:
        return {"status": "ok"}
    try:
        return _to_plain(session.commit()) or {"status": "ok"}
    except Exception as e:
        return {"status": "failed", "message": str(e)}


def _maybe_auto_commit(session: Any, max_messages: int) -> dict[str, Any] | None:
    if session is None:
        return None
    msgs = getattr(session, "messages", []) or []
    if len(msgs) < max_messages:
        return None
    return _commit_session(session)


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




def _complete_chat(
    msg: str,
    context_texts: list[str],
    attachment_title: str | None,
    history: list[dict[str, str]],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, bool, dict[str, Any] | None]:
    """Run chat completion (native tool loop). Viking provides system prompt;.
    Returns (reply_text, used_fallback, reminder_payload or None)."""
    context_block = "\n\n".join(context_texts[:14])
    user_content = (
        f"Context:\n{context_block}\n\nUser question:\n{msg}\n\n"
        "Reply in character: accurate, helpful, concise, and encouraging. Use tools when appropriate."
    )

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_content}
    ]


    reminder_payload: dict[str, Any] | None = None
    max_rounds = 3
    for round_index in range(max_rounds):
        content, tool_calls = complete_with_tools(messages, CHAT_TOOLS)
        try:
            log_chat_llm_round(session_id, round_index + 1, messages, content, tool_calls)
        except Exception:
            pass
        if content and not tool_calls:
            try:
                log_chat_final_response(session_id, content, False, reminder_payload)
            except Exception:
                pass
            return content, False, reminder_payload
        if tool_calls:
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)
            for tc in tool_calls:
                name = (tc.get("function") or {}).get("name", "")
                args = (tc.get("function") or {}).get("arguments", "{}")
                result, br = execute_tool(name, args, session_id, user_id, user_timezone=user_timezone)
                if br:
                    reminder_payload = br
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })
            continue
        break
    text, used_fallback = ai_chat(
        msg, context_texts, attachment_title,
        conversation_history=history,
    )
    try:
        log_chat_final_response(session_id, text, used_fallback, reminder_payload)
    except Exception:
        pass
    return text, used_fallback, reminder_payload


def _run_chat(body: ChatBody, user_timezone: str | None = None) -> dict[str, Any]:
    msg = (body.message or "").strip()
    if not msg:
        raise_chat_validation(400, ChatErrorCode.MESSAGE_REQUIRED, "Please enter a message.")
    if len(msg) > CHAT_MESSAGE_MAX_LENGTH:
        raise_chat_validation(
            400,
            ChatErrorCode.MESSAGE_TOO_LONG,
            f"Message is too long (max {CHAT_MESSAGE_MAX_LENGTH:,} characters).",
        )

    history = _normalize_history(body.history)
    if len(history) > CHAT_HISTORY_MAX_ITEMS:
        raise_chat_validation(
            400,
            ChatErrorCode.HISTORY_TOO_LONG,
            f"Too many messages in history (max {CHAT_HISTORY_MAX_ITEMS}). Start a new chat.",
        )
    try:
        log_chat_request(
            body.session_id or "(new)",
            msg,
            len(history),
            body.doc_id,
            body.debug_search_trace,
        )
    except Exception:
        pass
    session, file_search = _load_openviking_stack(body.session_id)
    session_id = _session_id(session) or body.session_id or str(uuid.uuid4())
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
    search_trace = file_search.last_trace

    uris = [str(c.get("uri", "")).strip() for c in search_results if str(c.get("uri", "")).strip()]
    _mark_used_contexts(session, uris)

    effective_history = history
    context_texts = _build_context_texts(search_results)
    attachment_title = _resolve_attachment_title(body.doc_id)

    try:
        log_chat_context(session_id, context_texts, attachment_title, "")
    except Exception:
        pass
    text, used_fallback, reminder = _complete_chat(
        msg, context_texts, attachment_title, effective_history, session_id, user_id,
        user_timezone=user_timezone,
    )
    mood = mood_from_text(text)

    auto_commit_result: dict[str, Any] | None = None
    try:
        _record_exchange(session, msg, text)
        auto_commit_result = _maybe_auto_commit(session, max_messages=get_settings().openviking_auto_commit_turns)
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
    if reminder:
        payload["reminder"] = reminder
    if body.debug_search_trace:
        payload["search_trace"] = search_trace
        payload["auto_commit"] = auto_commit_result
    return payload


@router.get("/reminders")
def get_reminders(session_id: str) -> list[dict[str, Any]]:
    """List due reminders (break, focus, etc.) for the given session (for the demo user)."""
    user_id = _demo_user_id()
    return list_due_reminders(session_id, user_id)


@router.patch("/reminders/{reminder_id}/ack")
def ack_reminder(reminder_id: str) -> dict[str, str]:
    """Mark a reminder as acknowledged so it is no longer returned by GET."""
    mark_reminder_acknowledged(reminder_id)
    return {"status": "acknowledged", "reminder_id": reminder_id}


def _user_timezone_from_request(request: Request) -> str | None:
    """Timezone is set by the client at app startup via X-User-Timezone header (never from body)."""
    return request.headers.get("x-user-timezone") or None


@router.post("/chat")
def chat(request: Request, body: ChatBody) -> dict:
    return _run_chat(body, user_timezone=_user_timezone_from_request(request))




def _build_chat_context(body: ChatBody) -> tuple[dict[str, Any], str, list[str], str | None, list[dict[str, str]], Any]:
    """Build context and return (context_payload, msg, context_texts, attachment_title, history, session)."""
    msg = (body.message or "").strip()
    if not msg:
        raise_chat_validation(400, ChatErrorCode.MESSAGE_REQUIRED, "Please enter a message.")
    if len(msg) > CHAT_MESSAGE_MAX_LENGTH:
        raise_chat_validation(
            400,
            ChatErrorCode.MESSAGE_TOO_LONG,
            f"Message is too long (max {CHAT_MESSAGE_MAX_LENGTH:,} characters).",
        )

    history = _normalize_history(body.history)
    if len(history) > CHAT_HISTORY_MAX_ITEMS:
        raise_chat_validation(
            400,
            ChatErrorCode.HISTORY_TOO_LONG,
            f"Too many messages in history (max {CHAT_HISTORY_MAX_ITEMS}). Start a new chat.",
        )
    session, file_search = _load_openviking_stack(body.session_id)
    session_id = _session_id(session) or body.session_id or str(uuid.uuid4())
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
    search_trace = file_search.last_trace

    uris = [str(c.get("uri", "")).strip() for c in search_results if str(c.get("uri", "")).strip()]
    _mark_used_contexts(session, uris)

    effective_history = history
    context_texts = _build_context_texts(search_results)
    attachment_title = _resolve_attachment_title(body.doc_id)

    first_time = False
    try:
        first_time = is_first_time_user()
    except Exception:
        pass
    if first_time:
        context_texts.append(
            "First-time onboarding: You have no information about this student. "
            "First greet them warmly, then ask their name. After they answer, ask their age (or year of birth). "
            "Then ask their hobbies. Ask one thing at a time; keep replies short. "
            "When you have collected name, age, and hobbies in this conversation, end your reply with exactly one line: "
            "PROFILE:name=<name>|age=<age>|hobbies=<hobbies> (use the exact values they gave; no line break before it)."
        )
    else:
        profile_content = read_user_profile()
        if profile_content:
            context_texts.insert(0, "Student profile (viking L0 memory):\n" + profile_content)

    context_payload: dict[str, Any] = {"context": search_results, "session_id": session_id, "first_time": first_time}
    if search_trace is not None:
        context_payload["search_trace"] = search_trace

    return context_payload, msg, context_texts, attachment_title, effective_history, session


@router.post("/chat/stream")
def chat_stream(request: Request, body: ChatBody) -> StreamingResponse:
    user_timezone = _user_timezone_from_request(request)

    def event_stream():
        stream_id = str(uuid.uuid4())
        context_payload, msg, context_texts, attachment_title, effective_history, session = _build_chat_context(body)
        context_payload["stream_id"] = stream_id
        session_id = context_payload.get("session_id")
        try:
            log_chat_request(body.session_id or "(new)", msg, len(body.history or []), body.doc_id, body.debug_search_trace)
            log_chat_context(session_id, context_texts, attachment_title, "")
        except Exception:
            pass
        yield f"event: context\ndata: {json.dumps(context_payload)}\n\n"

        user_id = _demo_user_id()
        text, used_fallback, reminder = _complete_chat(
            msg, context_texts, attachment_title, effective_history, session_id, user_id,
            user_timezone=user_timezone,
        )
        if context_payload.get("first_time") and "PROFILE:" in text:
            parsed = parse_profile_line(text)
            if parsed:
                name, age, hobbies = parsed
                try:
                    write_user_profile(name, age, hobbies)
                except Exception:
                    pass
                text = strip_profile_line(text)
        mood = mood_from_text(text)

        session_id = context_payload.get("session_id")
        try:
            _record_exchange(session, msg, text)
            auto_commit_result = _maybe_auto_commit(session, max_messages=get_settings().openviking_auto_commit_turns)
            if auto_commit_result and str(auto_commit_result.get("status", "")).lower() == "committed":
                mark_chat_session_committed(session_id, _demo_user_id())
        except Exception:
            pass
        _save_exchange(session_id, msg, text)

        for token in text.split():
            yield f"event: token\ndata: {json.dumps({'token': token, 'session_id': session_id, 'stream_id': stream_id})}\n\n"
        if reminder:
            reminder = {**reminder, "stream_id": stream_id}
            yield f"event: reminder\ndata: {json.dumps(reminder)}\n\n"
        yield f"event: mood\ndata: {json.dumps({'mood': mood, 'stream_id': stream_id})}\n\n"
        done_payload: dict[str, Any] = {
            "message": text,
            "session_id": session_id,
            "model_fallback": used_fallback,
            "stream_id": stream_id,
        }
        if reminder:
            done_payload["reminder"] = reminder
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


class InitialGreetingBody(BaseModel):
    session_id: str | None = None


@router.post("/initial-greeting")
def initial_greeting(body: InitialGreetingBody | None = None) -> dict[str, Any]:
    """Return the tutor's first message for a first-ever chat (greet and ask name)."""
    try:
        if not is_first_time_user():
            return {"message": None, "session_id": None}
    except Exception:
        return {"message": None, "session_id": None}

    sid = (body.session_id if body else None) or None
    session, _file_search = _load_openviking_stack(sid)
    session_id = _session_id(session) or str(uuid.uuid4())
    onboarding = (
        "First-time onboarding: Greet the new student warmly and ask what their name is. "
        "One short message only; do not ask for age or hobbies yet."
    )
    context_texts = [onboarding]
    prompt = "Start the conversation."
    text, _ = ai_chat(
        prompt,
        context_texts,
        attachment_doc_title=None,
        conversation_history=[],
    )
    return {"message": (text or "").strip() or None, "session_id": session_id}
