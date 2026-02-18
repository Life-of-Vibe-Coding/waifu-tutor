"""AI chat via Volcengine ARK (Doubao-Seed-1.8), with fallback."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_PERSONA = "You are Waifu Tutor, a warm and supportive study companion. Be concise, accurate, and encouraging."


def _volcengine_complete(messages: list[dict[str, str]]) -> str | None:
    settings = get_settings()
    if not settings.volcengine_api_key:
        logger.warning("Chat fallback: VOLCENGINE_API_KEY not set in backend .env")
        return None
    base = settings.volcengine_chat_base.rstrip("/")
    url = f"{base}/chat/completions"
    payload: dict[str, Any] = {"model": settings.chat_model, "messages": messages}
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.volcengine_api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code != 200:
                try:
                    body = r.text[:500] if r.text else ""
                except Exception:
                    body = ""
                logger.warning(
                    "Chat fallback: Volcengine API returned status %s, body=%s",
                    r.status_code,
                    body,
                )
                return None
            data = r.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            return (content or "").strip() or None
    except Exception as e:
        logger.warning("Chat fallback: Volcengine request failed: %s", e, exc_info=True)
        return None


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
    system_persona: str | None = None,
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

    attachment_hint = ""
    context_label = "Context (from user's documents):"
    if attachment_doc_title and context_texts:
        attachment_hint = (
            f'The user selected "{attachment_doc_title}" as context. '
            "The excerpts below are from this material. Use them precisely.\n\n"
        )
        context_label = "Content from selected document:"

    user_content = (
        f"{history_block}{attachment_hint}{context_label}\n{context_block}\n\n"
        f"User question:\n{prompt}\n\n"
        "Reply in character: accurate, helpful, concise, and encouraging."
    )
    persona = (system_persona or DEFAULT_PERSONA).strip() or DEFAULT_PERSONA
    out = _volcengine_complete([{"role": "system", "content": persona}, {"role": "user", "content": user_content}])
    if out:
        return out, False
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
