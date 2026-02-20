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
    log_chat_agent_input,
    log_chat_final_response,
    log_chat_llm_round,
    log_chat_request,
)
from app.tool import CHAT_TOOLS, execute_tool
from app.context import (
    append_openviking_text_message,
    build_openviking_chat_context,
    get_agent_context_text,
    put_openviking_session,
    record_openviking_session_usage,
)
from app.hitl import set_pending, consume_pending

logger = logging.getLogger(__name__)

# Max tool rounds per turn (avoids runaway loops)
MAX_TOOL_ROUNDS = 20
# Retries for empty assistant turns (no content and no tool calls) before surfacing recovery text.
MAX_EMPTY_RESPONSE_RETRIES = 4
router = APIRouter()

_LOOP_OBJECTIVE_MARKER = "[loop_main_objective]"
_SKILL_EXECUTION_MARKER = "[skill_execution_mode]"


def _tools_for_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return tools list; exclude load_skill when already in skill execution mode."""
    for m in messages or []:
        if m.get("role") == "system" and _SKILL_EXECUTION_MARKER in str(m.get("content") or ""):
            return [t for t in CHAT_TOOLS if (t.get("function") or {}).get("name") != "load_skill"]
    return CHAT_TOOLS


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


def _extract_main_objective(messages: list[dict[str, Any]]) -> str:
    """Extract the latest user objective from the tool-loop messages."""
    for m in reversed(messages or []):
        if m.get("role") != "user":
            continue
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        marker = "User question:\n"
        if marker in content:
            tail = content.split(marker, 1)[1]
            objective = tail.split("\n\n", 1)[0].strip()
            if objective:
                return objective
        return content
    return ""


def _ensure_loop_objective_context(messages: list[dict[str, Any]]) -> None:
    """Pin one system instruction so tool-loop rounds stay aligned to one objective."""
    for m in messages:
        if m.get("role") == "system" and _LOOP_OBJECTIVE_MARKER in str(m.get("content") or ""):
            return
    objective = _extract_main_objective(messages) or "Complete the latest user request."
    messages.insert(
        0,
        {
            "role": "system",
            "content": (
                f"{_LOOP_OBJECTIVE_MARKER}\n"
                f"Main objective: {objective}\n"
                "During tool/skill execution, keep outputs internal and continue until the final user-ready response is complete. "
                "Do not return intermediate artifacts (for example: only outline, only plan, only partial draft) unless the user explicitly asks for intermediate output only."
            ),
        },
    )


def _extract_skill_content_from_load_skill_result(result: str) -> tuple[str, str] | None:
    """If result is a successful load_skill response, return (content, name)."""
    try:
        data = json.loads(result)
        if not isinstance(data, dict) or data.get("error"):
            return None
        content = data.get("content")
        name = data.get("name", "")
        if content and isinstance(content, str):
            return (content, name)
    except Exception:
        pass
    return None


def _format_skill_execution_system(
    skill_content: str, skill_name: str, objective: str = ""
) -> str:
    """Build merged system prompt: loop objective + skill execution instructions."""
    obj = objective or "Complete the user request."
    skill_block = (
        f"Executing the following skill: {skill_name}\n"
        f"{skill_content}\n\n"
        "You MUST call load_subskill(path) when the skill directs you to a subskill before proceeding to the next step. "
        "Do not skip subskills or fabricate their outputs. "
        "Call request_human_approval before consequential actions or after significant outputs when the skill or situation warrants it."
    )
    return (
        f"{_SKILL_EXECUTION_MARKER}\n"
        f"Main objective: {obj}\n"
        "During tool/skill execution, keep outputs internal and continue until the final user-ready response is complete. "
        "Do not return intermediate artifacts (for example: only outline, only plan, only partial draft) unless the user explicitly asks for intermediate output only.\n\n"
        f"You are in skill execution mode. The active skill instructions are:\n\n{skill_block}"
    )


def _ensure_skill_execution_context(
    messages: list[dict[str, Any]], skill_content: str, skill_name: str = ""
) -> None:
    """Inject or update merged system message (objective + skill content + load_subskill enforcement)."""
    objective = _extract_main_objective(messages) or "Complete the user request."
    content = _format_skill_execution_system(skill_content, skill_name, objective)
    merged = {"role": "system", "content": content}
    i = 0
    replaced = False
    while i < len(messages):
        m = messages[i]
        if m.get("role") == "system" and (
            _SKILL_EXECUTION_MARKER in str(m.get("content") or "")
            or _LOOP_OBJECTIVE_MARKER in str(m.get("content") or "")
        ):
            if not replaced:
                m["content"] = content
                replaced = True
                i += 1
            else:
                messages.pop(i)
            continue
        i += 1
    if not replaced:
        messages.insert(0, merged)
    _trim_messages_for_skill_execution(messages)


def _trim_messages_for_skill_execution(messages: list[dict[str, Any]]) -> None:
    """During skill execution, remove main system prompt, load_skill assistant+tool (redundant), and normalize user."""
    objective = _extract_main_objective(messages)
    if not objective:
        objective = "Complete the user request."
    # Remove system messages that contain the main agent context (tools, registry, instructions)
    i = 0
    while i < len(messages):
        m = messages[i]
        if m.get("role") != "system":
            i += 1
            continue
        content = str(m.get("content") or "")
        if "Available tools" in content and (
            _LOOP_OBJECTIVE_MARKER not in content and _SKILL_EXECUTION_MARKER not in content
        ):
            messages.pop(i)
            continue
        i += 1
    # Remove the assistant+tool pair for load_skill (skill content is already in system)
    while len(messages) >= 2:
        last = messages[-1]
        prev = messages[-2]
        if last.get("role") == "tool" and prev.get("role") == "assistant":
            tcs = prev.get("tool_calls") or []
            if len(tcs) == 1 and (tcs[0].get("function") or {}).get("name") == "load_skill":
                messages.pop()
                messages.pop()
                continue
        break
    # Replace first user message content with just the last user message
    for m in messages:
        if m.get("role") == "user":
            m["content"] = objective
            break




def _run_tool_loop(
    messages: list[dict[str, Any]],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str | None, bool, dict[str, Any] | None, dict[str, Any] | None]:
    """Run agentic tool loop. Returns (reply_text or None, used_fallback, reminder_payload, hitl_payload).
    When hitl_payload is set, reply_text is None and the chat layer must pause and surface the checkpoint.
    """
    _ensure_loop_objective_context(messages)
    reminder_payload: dict[str, Any] | None = None
    empty_round_retries = 0
    for round_index in range(MAX_TOOL_ROUNDS):
        content, tool_calls = complete_with_tools(messages, _tools_for_messages(messages))
        try:
            log_chat_llm_round(session_id, round_index + 1, messages, content, tool_calls)
        except Exception:
            pass
        if content and not tool_calls:
            try:
                log_chat_final_response(session_id, content, False, reminder_payload)
            except Exception:
                pass
            return content, False, reminder_payload, None
        if not tool_calls:
            # Some model responses are empty and contain no tool call.
            # Give the model a short retry nudge before falling back.
            if not (content or "").strip() and empty_round_retries < MAX_EMPTY_RESPONSE_RETRIES:
                empty_round_retries += 1
                # Escalate the instruction after repeated empty turns so we recover without
                # switching to a generic fallback completion that lacks tool-loop context.
                if empty_round_retries < MAX_EMPTY_RESPONSE_RETRIES:
                    retry_instruction = (
                        "You returned an empty response. Continue from the latest tool result while staying focused on the same main objective. "
                        "Either provide tool calls or the final assistant response."
                    )
                else:
                    retry_instruction = (
                        "You repeatedly returned an empty response. Continue from the latest tool result and provide the final assistant response "
                        "for the same main objective in this turn. Do not leave content empty."
                    )
                messages.append({
                    "role": "user",
                    "content": retry_instruction,
                })
                continue
            if not (content or "").strip():
                recovery_text = (
                    "I hit a temporary generation issue while finishing that request. "
                    "Please reply with \"continue\" and I will resume from the last step."
                )
                try:
                    log_chat_final_response(session_id, recovery_text, True, reminder_payload)
                except Exception:
                    pass
                return recovery_text, True, reminder_payload, None
            break
        empty_round_retries = 0
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        for execution_index, tc in enumerate(tool_calls, start=1):
            name = (tc.get("function") or {}).get("name", "")
            args = (tc.get("function") or {}).get("arguments", "{}")
            result, br, hitl_payload = execute_tool(
                name,
                args,
                session_id,
                user_id,
                user_timezone=user_timezone,
                loop_context={
                    "round_index": round_index + 1,
                    "max_rounds": MAX_TOOL_ROUNDS,
                    "execution_index": execution_index,
                    "execution_total": len(tool_calls),
                    "tool_call_id": tc.get("id", ""),
                },
            )
            success = True
            try:
                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict) and parsed_result.get("error"):
                    success = False
            except Exception:
                success = True
            record_openviking_session_usage(
                session_id,
                skill={
                    "uri": f"viking://agent/skills/{name}" if name else "",
                    "input": args if isinstance(args, str) else json.dumps(args),
                    "output": result,
                    "success": success,
                },
            )
            if hitl_payload:
                checkpoint_id = set_pending(
                    session_id=session_id,
                    user_id=user_id,
                    messages=messages,
                    tool_call_id=tc.get("id", ""),
                    hitl_input=hitl_payload,
                    user_timezone=user_timezone,
                )
                hitl_payload["checkpoint_id"] = checkpoint_id
                hitl_payload["session_id"] = session_id
                return None, False, reminder_payload, hitl_payload
            if br:
                reminder_payload = br
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result,
            })
            if name == "load_skill":
                extracted = _extract_skill_content_from_load_skill_result(result)
                if extracted:
                    skill_content, skill_name = extracted
                    _ensure_skill_execution_context(messages, skill_content, skill_name)
    # Loop ended without final content (e.g. API returned no content and no tool_calls): signal fallback
    return None, True, reminder_payload, None


def _complete_chat(
    msg: str,
    context_texts: list[str],
    attachment_title: str | None,
    history: list[dict[str, str]],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str | None, bool, dict[str, Any] | None, dict[str, Any] | None]:
    """Run chat completion (native tool loop). Returns (reply_text or None, used_fallback, reminder_payload, hitl_payload).
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
    text, used_fallback, reminder_payload, hitl_payload = _run_tool_loop(messages, session_id, user_id, user_timezone)
    if hitl_payload is not None:
        return None, False, reminder_payload, hitl_payload
    if text is not None:
        return text, used_fallback, reminder_payload, None
    # Fallback when loop ended without content
    fallback_history = _messages_to_conversation_history(messages)
    text, used_fallback = ai_chat(msg, context_texts, attachment_title, conversation_history=fallback_history or history)
    if not (text or "").strip():
        text = "I'm here! Something went wrong on my side—please try again or rephrase."
    try:
        log_chat_final_response(session_id, text, used_fallback, reminder_payload)
    except Exception:
        pass
    return text, used_fallback, reminder_payload, None


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
    text, used_fallback, reminder, hitl_payload = _complete_chat(
        msg, context_texts, attachment_title, effective_history, session_id, user_id,
        user_timezone=user_timezone,
    )
    if hitl_payload is not None:
        return {
            "hitl": hitl_payload,
            "session_id": session_id,
        }
    mood = mood_from_text(text or "")
    append_openviking_text_message(session_id, "assistant", text or "")
    _save_exchange(session_id, msg, text or "")

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
    messages: list[dict[str, Any]] = list(entry["messages"])
    tool_call_id = entry["tool_call_id"]
    # Build tool result from user response
    resp = body.response or {}
    if resp.get("cancelled"):
        tool_result = json.dumps({"approved": False, "cancelled": True})
    elif resp.get("approved") is not False:
        tool_result = json.dumps({
            "approved": True,
            "overrides": resp.get("overrides"),
            "selected": resp.get("selected"),
            "free_input": resp.get("free_input"),
        })
    else:
        tool_result = json.dumps({"approved": False})
    messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": tool_result})
    session_id = entry["session_id"]
    text, used_fallback, reminder, hitl_payload = _run_tool_loop(
        messages, session_id, user_id, user_timezone=user_timezone,
    )
    if hitl_payload is not None:
        return {"hitl": hitl_payload, "session_id": session_id}
    if text is None:
        text, _ = ai_chat(
            messages[0].get("content", "") if messages else "",
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
            text, used_fallback, reminder, hitl_payload = _complete_chat(
                msg, context_texts, attachment_title, effective_history, session_id, user_id,
                user_timezone=user_timezone,
            )
            if hitl_payload is not None:
                yield f"event: hitl_checkpoint\ndata: {json.dumps({**hitl_payload, 'stream_id': stream_id})}\n\n"
                yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'stream_id': stream_id, 'hitl': True})}\n\n"
                return
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
