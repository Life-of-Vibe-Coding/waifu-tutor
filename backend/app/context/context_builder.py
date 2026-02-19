"""Agent context: tools loaded at startup for prompt injection."""
from __future__ import annotations

import logging
from typing import Any

from app.tool.tools import CHAT_TOOLS

logger = logging.getLogger(__name__)

_CACHED_TOOLS: list[dict[str, str]] = []


def load_agent_context() -> None:
    """Load tools into cache. Call at application startup."""
    global _CACHED_TOOLS
    _CACHED_TOOLS = []
    for t in CHAT_TOOLS:
        fn = (t.get("function") or {}) if isinstance(t, dict) else {}
        name = fn.get("name", "")
        desc = fn.get("description", "")
        if name:
            _CACHED_TOOLS.append({"name": name, "description": desc})
    logger.info("Agent context loaded: %d tool(s)", len(_CACHED_TOOLS))


def get_cached_tools() -> list[dict[str, str]]:
    """Return cached tool name/description list. Empty if load_agent_context() not yet called."""
    return list(_CACHED_TOOLS)


def get_agent_context_text() -> str:
    """Format cached tools as a single block for system/user prompt."""
    if not _CACHED_TOOLS:
        return ""
    lines = [f"- {t['name']}: {t['description']}" for t in _CACHED_TOOLS]
    return "Available tools:\n" + "\n".join(lines)


def get_agent_context() -> dict[str, Any]:
    """Return full context dict: tools and preformatted text."""
    return {
        "tools": get_cached_tools(),
        "text": get_agent_context_text(),
    }
