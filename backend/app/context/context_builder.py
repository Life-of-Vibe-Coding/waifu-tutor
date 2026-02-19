"""Agent context: tools and available skills, loaded at startup for prompt injection."""
from __future__ import annotations

import logging
from typing import Any

from app.tool.tools import CHAT_TOOLS
from app.tool.tools._skills import list_skills_from_fs

logger = logging.getLogger(__name__)

_CACHED_TOOLS: list[dict[str, str]] = []
_CACHED_SKILLS: list[dict[str, str]] = []


def load_agent_context() -> None:
    """Load tools and skills into cache. Call at application startup."""
    global _CACHED_TOOLS, _CACHED_SKILLS
    _CACHED_TOOLS = []
    for t in CHAT_TOOLS:
        fn = (t.get("function") or {}) if isinstance(t, dict) else {}
        name = fn.get("name", "")
        desc = fn.get("description", "")
        if name:
            _CACHED_TOOLS.append({"name": name, "description": desc})
    _CACHED_SKILLS = list_skills_from_fs()
    logger.info(
        "Agent context loaded: %d tool(s), %d skill(s)",
        len(_CACHED_TOOLS),
        len(_CACHED_SKILLS),
    )


def get_cached_tools() -> list[dict[str, str]]:
    """Return cached tool name/description list. Empty if load_agent_context() not yet called."""
    return list(_CACHED_TOOLS)


def get_cached_skills() -> list[dict[str, str]]:
    """Return cached skill name/description list. Empty if load_agent_context() not yet called."""
    return list(_CACHED_SKILLS)


def get_agent_context_text() -> str:
    """Format cached tools and skills as a single block for system/user prompt."""
    parts: list[str] = []
    if _CACHED_TOOLS:
        lines = [f"- {t['name']}: {t['description']}" for t in _CACHED_TOOLS]
        parts.append("Available tools:\n" + "\n".join(lines))
    if _CACHED_SKILLS:
        lines = [f"- {s['name']}: {s['description']}" for s in _CACHED_SKILLS]
        parts.append("Available skills:\n" + "\n".join(lines))
        parts.append(
            "Rule for skills: To use a skill, call get_skill(skill_name) to fetch its content (use level 'full' for full instructions). Skills may list subskills in their content (e.g. 'Call subskill → mastery-diagnosis/mastery-diagnosis.md'); when you see that, call get_skill with skill_name 'parent_skill/subskill_name' (e.g. get_skill('memory-comprehension-coach/mastery-diagnosis')) to load and follow the subskill. list_skills includes both top-level skills and subskills (as parent/subskill); use the exact name returned."
        )
    if not parts:
        return ""
    return "\n\n".join(parts)


def get_agent_context() -> dict[str, Any]:
    """Return full context dict: tools, skills, and preformatted text."""
    return {
        "tools": get_cached_tools(),
        "skills": get_cached_skills(),
        "text": get_agent_context_text(),
    }
