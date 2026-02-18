"""OpenAI-style tool definitions and execution for the chat agent."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.chat_logging import log_tool_call
from app.db.repositories import (
    create_subject,
    list_documents,
    list_subjects,
    set_document_subject,
)
from app.services.scheduler import schedule_reminder

logger = logging.getLogger(__name__)

# OpenAI-style tools list for the chat completions API
CHAT_TOOLS: list[dict[str, Any]] = [
    {
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
    },
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time in the user's local timezone. When the user asks what time it is, reply with ONLY the time_24h value in 24-hour format (e.g. '18:02:40'). Do not include date, year, or timezone name in your answer.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "list_subjects",
            "description": "List all existing subjects/folders in the system. Use this to see where a document might fit.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "organize_document",
            "description": "Assign a document to a subject (folder). Call only after the user has explicitly confirmed the classification (e.g. 'yes', 'that's correct', 'put it there'). Do not call for 'reason about', 'verify', 'group' (analyze), or 'identify' requests—use list_recent_uploads and list_subjects, propose, and ask for confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "ID of the document to move.",
                    },
                    "subject_id": {
                        "type": "string",
                        "description": "ID of the subject to assign the document to.",
                    },
                },
                "required": ["doc_id", "subject_id"],
            },
        },
    },
]


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

    result: str
    break_payload: dict[str, Any] | None = None

    if name == "get_current_time":
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
        break_payload = None

    elif name == "set_break_reminder":
        minutes = int(args.get("minutes", 15))
        message = args.get("message") or None
        reminder_id, due_at_iso = schedule_reminder(
            session_id, user_id, minutes, message=message, kind="break"
        )
        payload = {"reminder_id": reminder_id, "due_at": due_at_iso, "minutes": minutes, "kind": "break"}
        result = json.dumps({"ok": True, **payload})
        break_payload = payload

    elif name == "set_focus_timer":
        minutes = int(args.get("minutes", 25))
        message = args.get("message") or None
        reminder_id, due_at_iso = schedule_reminder(
            session_id, user_id, minutes, message=message, kind="focus"
        )
        payload = {"reminder_id": reminder_id, "due_at": due_at_iso, "minutes": minutes, "kind": "focus"}
        result = json.dumps({"ok": True, **payload})
        break_payload = payload

    elif name == "list_recent_uploads":
        limit = int(args.get("limit", 10))
        docs = list_documents(user_id)
        recent = docs[:limit]
        simplified = [
            {"id": d["id"], "title": d["title"], "filename": d["filename"], "subject_id": d["subject_id"], "source_folder": d.get("source_folder")}
            for d in recent
        ]
        result = json.dumps(simplified)
        break_payload = None

    elif name == "list_subjects":
        subjects = list_subjects(user_id)
        result = json.dumps(subjects)
        break_payload = None

    elif name == "create_subject":
        subject_name = args.get("name")
        if not subject_name:
            result = json.dumps({"error": "Subject name required"})
        else:
            new_subject = create_subject(user_id, subject_name)
            result = json.dumps(new_subject)
        break_payload = None

    elif name == "organize_document":
        doc_id = args.get("doc_id")
        subject_id = args.get("subject_id")
        if not doc_id or not subject_id:
            result = json.dumps({"error": "doc_id and subject_id required"})
        else:
            updated_doc = set_document_subject(doc_id, user_id, subject_id)
            if updated_doc:
                result = json.dumps({"status": "success", "doc": {"id": updated_doc["id"], "subject_id": updated_doc["subject_id"]}})
            else:
                result = json.dumps({"error": "Document not found"})
        break_payload = None

    else:
        result = json.dumps({"error": f"Unknown tool: {name}"})
        break_payload = None

    try:
        log_tool_call(session_id, name, args, result, break_payload)
    except Exception:
        pass
    return result, break_payload
