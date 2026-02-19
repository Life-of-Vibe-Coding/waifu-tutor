"""Set a reminder to bring the user back after a break."""
from __future__ import annotations

import json
from typing import Any

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "set_break_reminder",
        "description": "Set a reminder to bring the user back after a break. Use when the user asks to take a break, chill, rest, or pause for a number of minutes (e.g. '15 min break', 'I want to chill for 10 minutes'). Default to 15 minutes if they don't specify.",
        "parameters": {
            "type": "object",
            "properties": {
                "minutes": {
                    "type": "integer",
                    "description": "Duration of the break in minutes (1-120). Default 15 if user does not specify.",
                    "minimum": 1,
                    "maximum": 120,
                },
                "message": {
                    "type": "string",
                    "description": "Optional custom message to show when the reminder fires (e.g. 'Time to come back!').",
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
