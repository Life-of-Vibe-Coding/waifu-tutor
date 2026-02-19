"""Get the current time in the user's local timezone."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Get the current time in the user's local timezone. When the user asks what time it is, reply with ONLY the time_24h value in 24-hour format (e.g. '18:02:40'). Do not include date, year, or timezone name in your answer.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    now_utc = datetime.now(timezone.utc)
    try:
        tz = ZoneInfo(user_timezone) if user_timezone else timezone.utc
    except Exception:
        tz = timezone.utc
    now_local = now_utc.astimezone(tz)
    time_24h = now_local.strftime("%H:%M:%S")
    result = json.dumps({
        "time_24h": time_24h,
        "utc_iso": now_utc.isoformat(),
    })
    return result, None
