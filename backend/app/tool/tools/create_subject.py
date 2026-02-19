"""Create a new subject (folder) for organizing documents."""
from __future__ import annotations

import json
from typing import Any

from app.db.repositories import create_subject

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_subject",
        "description": "Create a new subject (folder) for organizing documents. Call only after the user has agreed to create a new folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the new subject (e.g. 'Math', 'Physics', 'History').",
                }
            },
            "required": ["name"],
        },
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    subject_name = args.get("name")
    if not subject_name:
        return json.dumps({"error": "Subject name required"}), None
    new_subject = create_subject(user_id, subject_name)
    return json.dumps(new_subject), None
