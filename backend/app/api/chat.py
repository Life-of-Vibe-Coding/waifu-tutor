"""Chat: non-stream and SSE stream with document chunk context."""
from __future__ import annotations

import json
import logging
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
from app.db.repositories import (
    get_document,
    insert_chat_message,
    list_due_reminders,
    mark_reminder_acknowledged,
    upsert_chat_session,
)
from app.services.ai import chat as ai_chat, complete_with_tools, mood_from_text
from app.core.chat_logging import (
    log_chat_context,
    log_chat_final_response,
    log_chat_llm_round,
    log_chat_request,
)
from app.tool import CHAT_TOOLS, execute_tool
from app.context import get_agent_context_text

logger = logging.getLogger(__name__)
router = APIRouter()


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
    """Run chat completion (native tool loop). Returns (reply_text, used_fallback, reminder_payload or None)."""
    agent_context = get_agent_context_text()
    context_block = "\n\n".join(context_texts[:14])
    user_content = (
        f"Context:\n{context_block}\n\nUser question:\n{msg}\n\n"
        "Reply in character: accurate, helpful, concise, and encouraging. Use tools when appropriate."
    )
    if agent_context:
        user_content = f"{agent_context}\n\n{user_content}"
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

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
    if not (text or "").strip():
        text = "I'm here! Something went wrong on my side—please try again or rephrase."
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
    session_id = body.session_id or str(uuid.uuid4())
    user_id = _demo_user_id()
    upsert_chat_session(session_id, user_id=user_id, title=msg[:80])

    context_texts: list[str] = []
    effective_history = history
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

    _save_exchange(session_id, msg, text)

    response: dict[str, Any] = {
        "message": {"role": "assistant", "content": text, "created_at": datetime.now(tz=timezone.utc).isoformat()},
        "mood": mood,
        "session_id": session_id,
        "model_fallback": used_fallback,
    }
    if reminder:
        response["reminder"] = reminder
    return response


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




def _build_chat_context(body: ChatBody) -> tuple[str, bool, str, list[str], str | None, list[dict[str, str]]]:
    """Build context and return (session_id, first_time, msg, context_texts, attachment_title, history)."""
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
    session_id = body.session_id or str(uuid.uuid4())
    user_id = _demo_user_id()
    upsert_chat_session(session_id, user_id=user_id, title=msg[:80])

    context_texts: list[str] = []
    attachment_title = _resolve_attachment_title(body.doc_id)
    return session_id, False, msg, context_texts, attachment_title, history


@router.post("/chat/stream")
def chat_stream(request: Request, body: ChatBody) -> StreamingResponse:
    user_timezone = _user_timezone_from_request(request)

    def event_stream():
        stream_id = str(uuid.uuid4())
        fallback_message = "I'm here! Something went wrong on my side—please try again."
        try:
            session_id, first_time, msg, context_texts, attachment_title, effective_history = _build_chat_context(body)
            try:
                log_chat_request(body.session_id or "(new)", msg, len(body.history or []), body.doc_id, body.debug_search_trace)
                log_chat_context(session_id, context_texts, attachment_title, "")
            except Exception:
                pass

            user_id = _demo_user_id()
            text, used_fallback, reminder = _complete_chat(
                msg, context_texts, attachment_title, effective_history, session_id, user_id,
                user_timezone=user_timezone,
            )
            if not (text or "").strip():
                text = fallback_message
            mood = mood_from_text(text)
            _save_exchange(session_id, msg, text)
        except Exception as e:
            logger.exception("Chat stream error: %s", e)
            session_id = body.session_id or str(uuid.uuid4())
            text = fallback_message
            used_fallback = True
            reminder = None
            mood = "neutral"

        for token in (text or "").split():
            yield f"event: token\ndata: {json.dumps({'token': token, 'session_id': session_id, 'stream_id': stream_id})}\n\n"
        if reminder:
            reminder = {**reminder, "stream_id": stream_id}
            yield f"event: reminder\ndata: {json.dumps(reminder)}\n\n"
        yield f"event: mood\ndata: {json.dumps({'mood': mood, 'stream_id': stream_id})}\n\n"
        done_event: dict[str, Any] = {
            "message": text,
            "session_id": session_id,
            "model_fallback": used_fallback,
            "stream_id": stream_id,
        }
        if reminder:
            done_event["reminder"] = reminder
        yield f"event: done\ndata: {json.dumps(done_event)}\n\n"

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
    return {"message": None, "session_id": None}
