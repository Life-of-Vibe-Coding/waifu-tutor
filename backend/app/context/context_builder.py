"""Agent context: tools loaded at startup for prompt injection."""
from __future__ import annotations

import logging
from typing import Any

from app.context.openviking_types import ContextPart, Part, SessionLike, TextPart
from app.context.session_store import ensure_openviking_session

logger = logging.getLogger(__name__)


def load_agent_context() -> None:
    """Load tools and skill registry via agent harness. Call at application startup."""
    from app.agent import get_default_agent
    from app.skills import get_skill_registry

    agent = get_default_agent()
    tools = agent.get_cached_tools()
    skill_count = len(get_skill_registry())
    logger.info("Agent context loaded: %d tool(s), %d skill(s)", len(tools), skill_count)


def get_cached_tools() -> list[dict[str, str]]:
    """Return cached tool name/description list. Empty if load_agent_context() not yet called."""
    from app.agent import get_default_agent

    return list(get_default_agent().get_cached_tools())


def get_agent_context_text() -> str:
    """Format cached tools and skill registry for system/user prompt."""
    from app.agent import get_default_agent

    return get_default_agent().get_agent_context_text()


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
