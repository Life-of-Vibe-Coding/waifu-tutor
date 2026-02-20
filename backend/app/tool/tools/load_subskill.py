"""Load a subskill by path (relative to skills root)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.skills.registry import get_skills_root


def _safe_resolve(root: Path, path_str: str) -> Path | None:
    """Resolve path under root; reject .. and absolute paths."""
    path_str = (path_str or "").strip().replace("\\", "/")
    if not path_str or path_str.startswith("/") or ".." in path_str.split("/"):
        return None
    parts = [p for p in path_str.split("/") if p and p != "."]
    resolved = root
    for p in parts:
        resolved = resolved / p
    try:
        resolved = resolved.resolve()
        root_resolved = root.resolve()
        if not str(resolved).startswith(str(root_resolved)):
            return None
        return resolved
    except Exception:
        return None


TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_subskill",
        "description": "Load a subskill by path when the parent skill directs you to one. Call this before proceeding when the skill says to delegate to a subskill (e.g. 'call → question-generation'). Path is relative to the skills root (e.g. exam-mode-tuner/question-generation/question-generation.md). Returns the subskill markdown content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to subskill markdown under skills root (e.g. exam-mode-tuner/question-generation/question-generation.md).",
                },
            },
            "required": ["path"],
        },
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    root = get_skills_root()
    path_str = (args.get("path") or "").strip()
    if not path_str:
        return json.dumps({"error": "Missing path"}), None
    resolved = _safe_resolve(root, path_str)
    if resolved is None:
        return json.dumps({"error": "Invalid or unsafe path"}), None
    if not resolved.is_file():
        return json.dumps({"error": f"Subskill not found: {path_str}"}), None
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        return json.dumps({"content": content, "path": path_str}), None
    except Exception as e:
        return json.dumps({"error": str(e)}), None
