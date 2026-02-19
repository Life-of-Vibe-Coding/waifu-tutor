"""Set a focus/work timer."""
from __future__ import annotations

import json
from typing import Any

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "set_focus_timer",
        "description": "Set a focus/work timer. Use when the user wants to focus or study for a set period and be reminded when time is up (e.g. 'remind me in 25 minutes', 'I'll focus for 30 min').",
        "parameters": {
            "type": "object",
            "properties": {
                "minutes": {
                    "type": "integer",
                    "description": "Duration of the focus session in minutes (1-120).",
                    "minimum": 1,
                    "maximum": 120,
                },
                "message": {
                    "type": "string",
                    "description": "Optional custom message when the timer ends.",
                },
            },
            "required": ["minutes"],
        },
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    result = json.dumps({"ok": False, "error": "Reminders are currently disabled."})
    return result, None
