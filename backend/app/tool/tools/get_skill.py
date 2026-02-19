"""Fetch the content of a specific skill from viking/agent/skills by name."""
from __future__ import annotations

import json
from typing import Any

from app.tool.tools._skills import get_skill_content

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_skill",
        "description": "Fetch the content of a specific skill or subskill from viking/agent/skills. Use after list_skills to load full instructions. When a skill's instructions say 'Call subskill → X/Y', use skill_name 'parent_skill/subskill_name' (e.g. 'memory-comprehension-coach/mastery-diagnosis') to load and follow that subskill.",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Top-level skill name (e.g. 'writing-coach', 'memory-comprehension-coach') or subskill path 'parent_skill/subskill_name' (e.g. 'memory-comprehension-coach/mastery-diagnosis'). list_skills returns both; use the exact name shown.",
                },
                "level": {
                    "type": "string",
                    "description": "Content level: 'abstract' (brief), 'overview' (parameters/usage), or 'full' (entire SKILL.md).",
                    "enum": ["abstract", "overview", "full"],
                    "default": "full",
                },
            },
            "required": ["skill_name"],
        },
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    skill_name = args.get("skill_name")
    level = args.get("level", "full")
    if not skill_name:
        return json.dumps({"error": "skill_name required"}), None
    content = get_skill_content(skill_name, level)
    if content is None:
        return json.dumps({"error": f"Skill not found: {skill_name}"}), None
    return json.dumps({"skill_name": skill_name, "level": level, "content": content}), None
