"""List the most recent documents uploaded by the user."""
from __future__ import annotations

import json
from typing import Any

from app.db.repositories import list_documents

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_recent_uploads",
        "description": "List the most recent documents uploaded by the user. Returns id, title, filename, subject_id, and source_folder (present when files were uploaded from a folder). Use this to inspect uploads before reasoning.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of documents to return (default 10).",
                    "default": 10,
                }
            },
        },
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    limit = int(args.get("limit", 10))
    docs = list_documents(user_id)
    recent = docs[:limit]
    simplified = [
        {
            "id": d["id"],
            "title": d["title"],
            "filename": d["filename"],
            "subject_id": d["subject_id"],
            "source_folder": d.get("source_folder"),
        }
        for d in recent
    ]
    return json.dumps(simplified), None
