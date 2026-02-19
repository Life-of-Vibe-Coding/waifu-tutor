"""List all existing subjects/folders in the system."""
from __future__ import annotations

import json
from typing import Any

from app.db.repositories import list_subjects

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_subjects",
        "description": "List all existing subjects/folders in the system. Use this to see where a document might fit.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    subjects = list_subjects(user_id)
    return json.dumps(subjects), None
