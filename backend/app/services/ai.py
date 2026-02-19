"""AI chat via Volcengine ARK (Doubao-Seed-1.8), with fallback and tool calling."""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ReAct-style thought block: extract <thought>...</thought> from model content
_THOUGHT_PATTERN = re.compile(r"<thought>\s*(.*?)\s*</thought>", re.DOTALL | re.IGNORECASE)


def parse_thought(content: str | None) -> tuple[str | None, str | None]:
    """Extract <thought>...</thought> from content. Returns (content_without_thought, thought_text)."""
    if not (content or "").strip():
        return content, None
    match = _THOUGHT_PATTERN.search(content)
    if not match:
        return content, None
    thought = match.group(1).strip() or None
    rest = (_THOUGHT_PATTERN.sub("", content, count=1)).strip() or None
    return rest, thought


def _volcengine_complete(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Call Volcengine chat/completions. Returns dict with 'content' (str or None) and 'tool_calls' (list or None)."""
    settings = get_settings()
    if not settings.volcengine_api_key:
        logger.warning("Chat fallback: VOLCENGINE_API_KEY not set in backend .env")
        return None
    base = settings.volcengine_chat_base.rstrip("/")
    url = f"{base}/chat/completions"
    payload: dict[str, Any] = {"model": settings.chat_model, "messages": messages}
    if tools:
        payload["tools"] = tools
    timeout = get_settings().chat_request_timeout
    try:
        with httpx.Client(timeout=timeout) as client:
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
            msg = (data.get("choices") or [{}])[0].get("message", {})
            raw_content = (msg.get("content") or "").strip() or None
            content_stripped, thought = parse_thought(raw_content)
            raw_tool_calls = msg.get("tool_calls")
            tool_calls = None
            if raw_tool_calls:
                tool_calls = [
                    {
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": (tc.get("function") or {}).get("name", ""),
                            "arguments": (tc.get("function") or {}).get("arguments", "{}"),
                        },
                    }
                    for tc in raw_tool_calls
                ]
            return {
                "content": content_stripped,
                "tool_calls": tool_calls,
                "thought": thought,
            }
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
    messages = [{"role": "user", "content": user_content}]
    out = _volcengine_complete(messages)
    if out and out.get("content"):
        return out["content"], False
    return fallback_chat(prompt, context_texts), True


def complete_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]] | None, str | None]:
    """Call Volcengine with tools. Returns (content, tool_calls, thought). Content has <thought> stripped."""
    out = _volcengine_complete(messages, tools=tools)
    if not out:
        return None, None, None
    return out.get("content"), out.get("tool_calls"), out.get("thought")


def mood_from_text(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ("great", "awesome", "amazing", "proud", "well done")):
        return "happy"
    if any(w in text_lower for w in ("sorry", "don't worry", "let's try", "step by step")):
        return "gentle"
    if any(w in text_lower for w in ("keep going", "you got this", "you can do it")):
        return "encouraging"
    return "neutral"
