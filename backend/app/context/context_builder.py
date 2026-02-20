"""Agent context: tools loaded at startup for prompt injection."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.tool.tools import CHAT_TOOLS
from app.skills import build_skill_registry, get_skill_registry
from app.context.openviking_types import ContextPart, Part, SessionLike, TextPart
from app.context.session_store import ensure_openviking_session

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
    return (
        "\n\n".join(parts)
        + "\n\nTo run a skill, call load_skill first. You will receive full instructions after loading."
    )


def get_agent_context() -> dict[str, Any]:
    """Return full context dict: tools and preformatted text."""
    return {
        "tools": get_cached_tools(),
        "text": get_agent_context_text(),
    }


def build_openviking_chat_context(
    *,
    session_id: str,
    user_id: str,
    user_message: str,
    history: list[dict[str, str]],
    doc_id: str | None,
    attachment_title: str | None,
    attachment_uri: str | None,
) -> tuple[list[str], SessionLike]:
    """Build prompt context via OpenViking-style session primitives."""
    session = ensure_openviking_session(
        session_id=session_id,
        user_id=user_id,
        history_messages=history,
    )
    context_texts: list[str] = []

    # Build readable recent-history context for prompting.
    history_lines: list[str] = []
    for item in history[-12:]:
        role = str(item.get("role", "user") or "user")
        content = str(item.get("content", "") or "").strip()
        if not content:
            continue
        history_lines.append(f"[{role}] {content}")
    if history_lines:
        context_texts.append("Recent session messages:\n" + "\n".join(history_lines))
        try:
            session.used(contexts=[f"viking://session/{session_id}/messages.jsonl"])
        except Exception:
            pass

    user_parts: list[Part] = [TextPart(user_message)]
    if doc_id:
        uri = attachment_uri or f"viking://resources/users/{user_id}/documents/{doc_id}"
        abstract = attachment_title or f"Document {doc_id}"
        user_parts.append(ContextPart(uri=uri, abstract=abstract))
        context_texts.append(f"Attached context:\n- {abstract}\n- URI: {uri}")
        try:
            session.used(contexts=[uri])
        except Exception:
            pass
    session.add_message("user", user_parts)

    return context_texts, session
