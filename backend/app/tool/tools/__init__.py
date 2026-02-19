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
]

CHAT_TOOLS: list[dict[str, Any]] = [m.TOOL_SCHEMA for m in _TOOL_MODULES]

_NAME_TO_MODULE = {m.TOOL_SCHEMA["function"]["name"]: m for m in _TOOL_MODULES}


def execute_tool(
    name: str,
    arguments: str,
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Execute a tool by name with given JSON arguments. Returns (result_string, reminder_payload or None)."""
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
    except json.JSONDecodeError as e:
        result = json.dumps({"error": f"Invalid arguments: {e}"})
        try:
            log_tool_call(session_id, name, arguments, result, None)
        except Exception:
            pass
        return result, None

    module = _NAME_TO_MODULE.get(name)
    if module is None:
        result = json.dumps({"error": f"Unknown tool: {name}"})
        try:
            log_tool_call(session_id, name, args, result, None)
        except Exception:
            pass
        return result, None

    result, break_payload = module.run(args, session_id, user_id, user_timezone=user_timezone)
    try:
        log_tool_call(session_id, name, args, result, break_payload)
    except Exception:
        pass
    return result, break_payload
