"""OpenAI-style tool definitions and execution for the chat agent."""
from __future__ import annotations

import json
from typing import Any

from app.core.chat_logging import log_tool_call

from . import (
    create_subject,
    get_current_time,
    list_recent_uploads,
    list_subjects,
    load_skill,
    read_file,
    request_human_approval,
    set_break_reminder,
    set_focus_timer,
)

_TOOL_MODULES = [
    set_break_reminder,
    set_focus_timer,
    get_current_time,
    list_recent_uploads,
    list_subjects,
    create_subject,
    load_skill,
    read_file,
    request_human_approval,
]

CHAT_TOOLS: list[dict[str, Any]] = [m.TOOL_SCHEMA for m in _TOOL_MODULES]

_NAME_TO_MODULE = {m.TOOL_SCHEMA["function"]["name"]: m for m in _TOOL_MODULES}

# When request_human_approval runs, we return this and a hitl_payload so the chat layer pauses.
HITL_SENTINEL = getattr(request_human_approval, "HITL_SENTINEL", "__HITL_PAUSE__")


def execute_tool(
    name: str,
    arguments: str,
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
    loop_context: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """Execute a tool by name. Returns (result_string, reminder_payload or None, hitl_payload or None).
    When the tool is request_human_approval, hitl_payload is set and the chat layer must pause.
    """
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
    except json.JSONDecodeError as e:
        result = json.dumps({"error": f"Invalid arguments: {e}"})
        try:
            log_tool_call(session_id, name, arguments, result, None, loop_context=loop_context)
        except Exception:
            pass
        return result, None, None

    module = _NAME_TO_MODULE.get(name)
    if module is None:
        result = json.dumps({"error": f"Unknown tool: {name}"})
        try:
            log_tool_call(session_id, name, args, result, None, loop_context=loop_context)
        except Exception:
            pass
        return result, None, None

    result, break_payload = module.run(args, session_id, user_id, user_timezone=user_timezone)
    hitl_payload: dict[str, Any] | None = None
    if result == HITL_SENTINEL and isinstance(break_payload, dict) and break_payload.get("_hitl"):
        hitl_payload = {k: v for k, v in break_payload.items() if k != "_hitl"}
        break_payload = None
    try:
        log_tool_call(
            session_id,
            name,
            args,
            result if result != HITL_SENTINEL else "(hitl)",
            break_payload,
            loop_context=loop_context,
        )
    except Exception:
        pass
    return result, break_payload, hitl_payload
