"""Load a top-level skill by name: read full SKILL.md content."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.skills.registry import get_skills_root

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "Load a top-level skill by name. Call this when the user's intent matches a skill from the registry, before executing the skill's steps. Returns the full SKILL.md content.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill name from the registry (e.g. exam-mode-tuner).",
                },
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
    root = get_skills_root()
    name = (args.get("name") or "").strip()
    if not name:
        return json.dumps({"error": "Missing skill name"}), None
    # Restrict to a single path segment (top-level skill folder only)
    if "/" in name or "\\" in name or name in (".", ".."):
        return json.dumps({"error": "Invalid skill name"}), None
    path = root / name / "SKILL.md"
    if not path.is_file():
        return json.dumps({"error": f"Skill not found: {name}"}), None
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return json.dumps({"content": content, "name": name}), None
    except Exception as e:
        return json.dumps({"error": str(e)}), None
