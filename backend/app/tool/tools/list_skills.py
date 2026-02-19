"""List available agent skills from viking/agent/skills."""
from __future__ import annotations

import json
from typing import Any

from app.tool.tools._skills import list_skills_from_fs

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_skills",
        "description": "List available agent skills from viking/agent/skills. Returns skill names and short descriptions. Use when the user asks what skills are available or when choosing which skill to apply.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    skills = list_skills_from_fs()
    return json.dumps(skills), None
