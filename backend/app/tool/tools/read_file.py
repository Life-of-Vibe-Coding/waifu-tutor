"""Read a file under the skills root (e.g. subskill markdown). Path must be relative and inside skills root."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.skills.registry import get_skills_root

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file under the skills directory. Use for subskills (e.g. exam-mode-tuner/question-generation/question-generation.md). Path is relative to the skills root; no parent (..) or absolute paths.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from skills root, e.g. exam-mode-tuner/question-generation/question-generation.md",
                },
            },
            "required": ["path"],
        },
    },
}


def _safe_resolve(root: Path, path_str: str) -> Path | None:
    """Resolve path_str under root. Return None if outside root or invalid."""
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
        return json.dumps({"error": "Invalid or disallowed path"}), None
    if not resolved.is_file():
        return json.dumps({"error": f"File not found: {path_str}"}), None
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        return json.dumps({"content": content, "path": path_str}), None
    except Exception as e:
        return json.dumps({"error": str(e)}), None
