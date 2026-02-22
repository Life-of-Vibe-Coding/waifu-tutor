"""Chat: non-stream and SSE stream with document chunk context."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from agno.run.requirement import RunRequirement
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
from app.services.ai import chat as ai_chat, mood_from_text
from app.core.chat_logging import (
    log_chat_context,
    log_chat_agent_input,
    log_chat_final_response,
    log_chat_request,
)
from app.agent import AgentRunResult, get_default_agent
from app.context import (
    append_openviking_text_message,
    build_openviking_chat_context,
    get_agent_context_text,
    put_openviking_session,
)
from app.hitl import consume_pending

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


def _messages_to_conversation_history(
    messages: list[dict[str, Any]],
    max_items: int = 12,
    max_content_len: int = 2000,
) -> list[dict[str, str]]:
    """Build compact conversation history from tool-loop messages for fallback chat."""
    history: list[dict[str, str]] = []
    for m in messages or []:
        role = m.get("role")
        if role == "tool":
            continue
        if role not in ("user", "assistant"):
            continue
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if len(content) > max_content_len:
            content = content[:max_content_len] + "..."
        history.append({"role": role, "content": content})
    return history[-max_items:]


def _save_exchange(session_id: str, user_msg: str, assistant_msg: str) -> None:
    user_id = _demo_user_id()
    upsert_chat_session(session_id, user_id=user_id, title=user_msg[:80])
    insert_chat_message(str(uuid.uuid4()), session_id=session_id, user_id=user_id, role="user", content=user_msg)
    insert_chat_message(str(uuid.uuid4()), session_id=session_id, user_id=user_id, role="assistant", content=assistant_msg)


def _resolve_attachment(doc_id: str | None) -> tuple[str | None, str | None]:
    if not doc_id:
        return None, None
    doc = get_document(doc_id, _demo_user_id())
    if not doc:
        return None, None
    return doc.get("title"), doc.get("openviking_uri")


def _run_tool_loop(
    messages: list[dict[str, Any]],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> AgentRunResult:
    """Run agentic tool loop via harness.
    When hitl_payload is set, reply_text is None and the chat layer must pause and surface the checkpoint.
    """
    return get_default_agent().run(messages, session_id, user_id, user_timezone=user_timezone)


def _complete_chat(
    msg: str,
    context_texts: list[str],
    attachment_title: str | None,
    history: list[dict[str, str]],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> AgentRunResult:
    """Run chat completion (native tool loop).
    When hitl_payload is set, reply_text is None and the client must show the checkpoint and call hitl-response to resume.
    """
    agent_context = get_agent_context_text()
    context_block = "\n\n".join(context_texts[:14])
    user_content = (
        f"Context:\n{context_block}\n\nUser question:\n{msg}\n\n"
        "Reply in character: accurate, helpful, concise, and encouraging. Use tools when appropriate."
    )
    if agent_context:
        user_content = f"{agent_context}\n\n{user_content}"
    try:
        log_chat_agent_input(session_id, user_content)
    except Exception:
        pass
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]
    run_res = _run_tool_loop(messages, session_id, user_id, user_timezone)
    if run_res.hitl_payload is not None:
        return run_res
    if run_res.text is not None:
        return run_res
    # Fallback when loop ended without content
    fallback_history = _messages_to_conversation_history(messages)
    text, used_fallback = ai_chat(msg, context_texts, attachment_title, conversation_history=fallback_history or history)
    if not (text or "").strip():
        text = "I'm here! Something went wrong on my side—please try again or rephrase."
    try:
        log_chat_final_response(session_id, text, used_fallback, run_res.reminder_payload)
    except Exception:
        pass
    return AgentRunResult(
        text=text,
        used_fallback=used_fallback,
        reminder_payload=run_res.reminder_payload,
        hitl_payload=None,
    )


def _run_chat(body: ChatBody, user_timezone: str | None = None) -> dict[str, Any]:
    session_id, _first_time, msg, context_texts, attachment_title, effective_history, _ov_session = _build_chat_context(body)
    try:
        log_chat_request(
            session_id,
            msg,
            len(effective_history),
            body.doc_id,
            body.debug_search_trace,
        )
    except Exception:
        pass
    user_id = _demo_user_id()

    try:
        log_chat_context(session_id, context_texts, attachment_title, "")
    except Exception:
        pass
    run_res = _complete_chat(
        msg, context_texts, attachment_title, effective_history, session_id, user_id,
        user_timezone=user_timezone,
    )
    if run_res.hitl_payload is not None:
        return {
            "hitl": run_res.hitl_payload,
            "session_id": session_id,
        }
    text = run_res.text or ""
    mood = mood_from_text(text)
    append_openviking_text_message(session_id, "assistant", text)
    _save_exchange(session_id, msg, text)

    response: dict[str, Any] = {
        "message": {"role": "assistant", "content": text, "created_at": datetime.now(tz=timezone.utc).isoformat()},
        "mood": mood,
        "session_id": session_id,
        "model_fallback": run_res.used_fallback,
    }
    if run_res.reminder_payload:
        response["reminder"] = run_res.reminder_payload
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


class HitlResponseBody(BaseModel):
    """Body for resuming after a HITL checkpoint."""
    session_id: str
    checkpoint_id: str
    response: dict[str, Any] = Field(
        ...,
        description="Either { approved: true, overrides?: object }, { cancelled: true }, { selected: string }, or { free_input: string }",
    )


@router.post("/chat/hitl-response")
def hitl_response(request: Request, body: HitlResponseBody) -> dict[str, Any]:
    """Resume the agent loop after the user responds to a HITL checkpoint."""
    user_timezone = _user_timezone_from_request(request)
    user_id = _demo_user_id()
    entry = consume_pending(body.checkpoint_id)
    if not entry:
        raise_chat_validation(404, ChatErrorCode.INVALID_REQUEST, "Checkpoint expired or not found.")
    run_id = str(entry.get("run_id") or "")
    req_items = entry.get("requirements") or []
    requirements = [RunRequirement.from_dict(item) for item in req_items if isinstance(item, dict)]
    if not run_id or not requirements:
        raise_chat_validation(400, ChatErrorCode.INVALID_REQUEST, "Invalid checkpoint payload.")

    target = requirements[0]
    resp = body.response or {}
    if resp.get("cancelled"):
        target.reject(note="User cancelled")
    elif resp.get("approved") is not False:
        target.confirm()
        extras = {
            "selected": resp.get("selected"),
            "free_input": resp.get("free_input"),
            "overrides": resp.get("overrides"),
        }
        note = {k: v for k, v in extras.items() if v is not None}
        if note:
            target.confirmation_note = json.dumps(note)
            if target.tool_execution is not None:
                target.tool_execution.confirmation_note = target.confirmation_note
    else:
        target.reject(note="User rejected")

    session_id = entry["session_id"]
    run_res = get_default_agent().continue_run(
        run_id=run_id,
        requirements=requirements,
        session_id=session_id,
        user_id=user_id,
        user_timezone=user_timezone,
    )
    if run_res.hitl_payload is not None:
        return {"hitl": run_res.hitl_payload, "session_id": session_id}
    text = run_res.text
    used_fallback = run_res.used_fallback
    reminder = run_res.reminder_payload
    if text is None:
        text, _ = ai_chat(
            "",
            [], None, conversation_history=[],
        )
        if not (text or "").strip():
            text = "Done. Anything else?"
        used_fallback = True
    try:
        log_chat_final_response(session_id, text, used_fallback, reminder)
    except Exception:
        pass
    mood = mood_from_text(text)
    # Persist final assistant message (user side already has the checkpoint; we don't re-save user msg)
    append_openviking_text_message(session_id, "assistant", text)
    insert_chat_message(
        str(uuid.uuid4()), session_id, user_id, role="assistant", content=text,
    )
    out: dict[str, Any] = {
        "message": {"role": "assistant", "content": text, "created_at": datetime.now(tz=timezone.utc).isoformat()},
        "mood": mood,
        "session_id": session_id,
        "model_fallback": used_fallback,
    }
    if reminder:
        out["reminder"] = reminder
    return out


def _build_chat_context(
    body: ChatBody,
) -> tuple[str, bool, str, list[str], str | None, list[dict[str, str]], Any]:
    """Build context and return (session_id, first_time, msg, context_texts, attachment_title, history, ov_session)."""
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

    attachment_title, attachment_uri = _resolve_attachment(body.doc_id)
    context_texts, _ov_session = build_openviking_chat_context(
        session_id=session_id,
        user_id=user_id,
        user_message=msg,
        history=history,
        doc_id=body.doc_id,
        attachment_title=attachment_title,
        attachment_uri=attachment_uri,
    )
    put_openviking_session(_ov_session)
    return session_id, False, msg, context_texts, attachment_title, history, _ov_session


@router.post("/chat/stream")
def chat_stream(request: Request, body: ChatBody) -> StreamingResponse:
    user_timezone = _user_timezone_from_request(request)

    def event_stream():
        stream_id = str(uuid.uuid4())
        fallback_message = "I'm here! Something went wrong on my side—please try again."
        try:
            session_id, first_time, msg, context_texts, attachment_title, effective_history, _ov_session = _build_chat_context(body)
            try:
                log_chat_request(body.session_id or "(new)", msg, len(body.history or []), body.doc_id, body.debug_search_trace)
                log_chat_context(session_id, context_texts, attachment_title, "")
            except Exception:
                pass

            user_id = _demo_user_id()
            run_res = _complete_chat(
                msg, context_texts, attachment_title, effective_history, session_id, user_id,
                user_timezone=user_timezone,
            )
            if run_res.hitl_payload is not None:
                yield f"event: hitl_checkpoint\ndata: {json.dumps({**run_res.hitl_payload, 'stream_id': stream_id})}\n\n"
                yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'stream_id': stream_id, 'hitl': True})}\n\n"
                return
            text = run_res.text
            used_fallback = run_res.used_fallback
            reminder = run_res.reminder_payload
            if not (text or "").strip():
                text = fallback_message
            mood = mood_from_text(text or "")
            append_openviking_text_message(session_id, "assistant", text or "")
            _save_exchange(session_id, msg, text or "")
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
