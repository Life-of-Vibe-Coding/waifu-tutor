"""Agent context: tools loaded at startup for prompt injection."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.tool.tools import CHAT_TOOLS
from app.skills import build_skill_registry, get_skill_registry

logger = logging.getLogger(__name__)

_CACHED_TOOLS: list[dict[str, str]] = []


def load_agent_context() -> None:
    """Load tools and skill registry. Call at application startup."""
    global _CACHED_TOOLS
    _CACHED_TOOLS = []
    for t in CHAT_TOOLS:
        fn = (t.get("function") or {}) if isinstance(t, dict) else {}
        name = fn.get("name", "")
        desc = fn.get("description", "")
        if name:
            _CACHED_TOOLS.append({"name": name, "description": desc})
    try:
        from app.core.config import get_settings
        skills_root = Path(get_settings().skills_dir)
    except Exception:
        skills_root = Path(__file__).resolve().parent.parent.parent / "docs" / "skill-framework"
    build_skill_registry(skills_root)
    logger.info("Agent context loaded: %d tool(s), %d skill(s)", len(_CACHED_TOOLS), len(get_skill_registry()))


def get_cached_tools() -> list[dict[str, str]]:
    """Return cached tool name/description list. Empty if load_agent_context() not yet called."""
    return list(_CACHED_TOOLS)


def get_agent_context_text() -> str:
    """Format cached tools and skill registry for system/user prompt."""
    parts = []
    if _CACHED_TOOLS:
        parts.append("Available tools:\n" + "\n".join(f"- {t['name']}: {t['description']}" for t in _CACHED_TOOLS))
    registry = get_skill_registry()
    if registry:
        parts.append(
            "Available top-level skills (load with load_skill before executing):\n"
            + "\n".join(f"- {s['name']}: {s['description']}" for s in registry)
        )
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n\nUse the skill registry to choose a skill, then call load_skill before executing. Load subskills via read_file when the parent skill says so. Call request_human_approval before consequential actions or after significant outputs; do not fabricate subskill outputs or skip checkpoints."


def get_agent_context() -> dict[str, Any]:
    """Return full context dict: tools and preformatted text."""
    return {
        "tools": get_cached_tools(),
        "text": get_agent_context_text(),
    }
