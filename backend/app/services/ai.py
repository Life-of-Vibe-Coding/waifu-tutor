"""AI chat via Volcengine ARK (Doubao-Seed-1.8) using Agno, with fallback."""
from __future__ import annotations

import logging

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_base_model() -> OpenAIChat:
    settings = get_settings()
    conf = settings.openviking_conf()
    vlm_conf = conf.get("vlm") if isinstance(conf, dict) else {}
    if not isinstance(vlm_conf, dict):
        vlm_conf = {}
    model_id = str(vlm_conf.get("model") or settings.chat_model)
    api_key = str(vlm_conf.get("api_key") or settings.volcengine_api_key or "sk-fallback")
    base_url_raw = str(vlm_conf.get("api_base") or settings.volcengine_chat_base)
    base_url = base_url_raw.rstrip("/") if base_url_raw else settings.volcengine_chat_base.rstrip("/")
    return OpenAIChat(
        id=model_id,
        api_key=api_key,
        base_url=base_url,
    )


def fallback_chat(prompt: str, context: list[str]) -> str:
    prefix = "\n".join(f"- {c[:220]}" for c in context[:4])
    if prefix:
        return (
            f"Here is a focused answer from your study context:\n{prefix}\n\n"
            f"Question: {prompt}\n"
            "You got this, we can go deeper together!"
        )
    return "I can help! Upload study material or ask a focused question and we will break it down step by step."


def chat(
    prompt: str,
    context_texts: list[str],
    attachment_doc_title: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, bool]:
    """Returns (reply_text, used_fallback). used_fallback is True when Volcengine was not used."""
    context_block = "\n\n".join(context_texts[:14])
    history_block = ""
    if conversation_history:
        lines: list[str] = []
        for item in conversation_history[-12:]:
            role = str(item.get("role", "user") or "user")
            content = str(item.get("content", "") or "").strip()
            if content:
                lines.append(f"[{role}] {content}")
        if lines:
            history_block = "Recent conversation history:\n" + "\n".join(lines) + "\n\n"

    context_label = "Context (from user's documents):"
    user_content = (
        f"{history_block}{context_label}\n{context_block}\n\n"
        f"User question:\n{prompt}\n\n"
        "Reply in character: accurate, helpful, concise, and encouraging."
    )
    
    agent = Agent(model=get_base_model(), markdown=True)
    try:
        response = agent.run(user_content)
        if response and response.content:
            return response.content, False
    except Exception as e:
        logger.warning("Chat fallback: Agno request failed: %s", e, exc_info=True)
        
    return fallback_chat(prompt, context_texts), True


def mood_from_text(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ("great", "awesome", "amazing", "proud", "well done")):
        return "happy"
    if any(w in text_lower for w in ("sorry", "don't worry", "let's try", "step by step")):
        return "gentle"
    if any(w in text_lower for w in ("keep going", "you got this", "you can do it")):
        return "encouraging"
    return "neutral"
