"""Structured, readable logging for chat process and skill/tool calling.

Logs are written to log_dir/chat/chat.log. When chat.log reaches 10 MB it is rotated:
current file is renamed to chat_yyyy_MM_dd_HH_mm.log and a new chat.log is started.
Use log_chat_* and log_tool_* from this module; do not depend on global logger names.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Max size per log file before rotation (10 MB)
_MAX_LOG_BYTES = 10 * 1024 * 1024


def _pretty_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return repr(obj)


def _ensure_log_dir(settings: Any) -> Path:
    from app.core.config import get_settings

    s = settings or get_settings()
    log_dir = getattr(s, "log_dir", None) or Path("logs")
    if not log_dir.is_absolute():
        # Resolve relative to backend root (same as settings)
        backend_root = Path(__file__).resolve().parent.parent.parent
        log_dir = backend_root / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _chat_log_dir(settings: Any) -> Path:
    """Return log_dir/chat, creating it if needed."""
    d = _ensure_log_dir(settings) / "chat"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rotation_filename(default_name: str) -> str:
    """Name rotated file as chat_yyyy_MM_dd_HH_mm.log (same folder)."""
    parent = Path(default_name).parent
    ts = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H_%M")
    return str(parent / f"chat_{ts}.log")


def _get_chat_file_logger(name: str, log_key: str) -> logging.Logger:
    """Return a logger that writes to logs/chat/chat.log; rotates at 10 MB to chat_yyyy_MM_dd_HH_mm.log."""
    from app.core.config import get_settings

    logger = logging.getLogger(f"waifu.chat.{name}")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    chat_dir = _chat_log_dir(get_settings())
    path = chat_dir / "chat.log"
    handler = RotatingFileHandler(
        path,
        maxBytes=_MAX_LOG_BYTES,
        backupCount=0,
        encoding="utf-8",
    )
    handler.namer = _rotation_filename
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def _write_chat_log(
    section: str,
    session_id: str,
    payload: str,
    extra: str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    lines = [
        "",
        "=" * 80,
        f"  [{ts}]  {section}  session_id={session_id}",
        "=" * 80,
        payload.strip(),
    ]
    if extra:
        lines.append(extra.strip())
    msg = "\n".join(lines)
    _get_chat_file_logger("file", "chat").info(msg)


def log_chat_request(
    session_id: str,
    message: str,
    history_len: int,
    doc_id: str | None,
    debug_search_trace: bool,
) -> None:
    """Log incoming chat request (user message and request meta)."""
    payload = f"""
  message: {message or ''}
  history_length: {history_len}
  doc_id: {doc_id}
  debug_search_trace: {debug_search_trace}
"""
    _write_chat_log("CHAT REQUEST", session_id or "(new)", payload)


def log_chat_context(
    session_id: str,
    context_texts: list[str],
    attachment_title: str | None,
    persona_preview: str,
) -> None:
    """Log built context (context_texts summary, attachment, persona preview)."""
    ctx_preview = "\n".join(f"  - {t or ''}" for t in (context_texts or [])[:8])
    if (context_texts or [])[8:]:
        ctx_preview += f"\n  ... and {len(context_texts) - 8} more blocks"
    payload = f"""
  attachment_title: {attachment_title}
  persona_preview: {persona_preview or ''}

  context_blocks:
{ctx_preview or '  (none)'}
"""
    _write_chat_log("CHAT CONTEXT", session_id, payload)


def log_chat_llm_round(
    session_id: str,
    round_index: int,
    messages_sent: list[dict[str, Any]],
    content: str | None,
    tool_calls: list[dict[str, Any]] | None,
) -> None:
    """Log one LLM round: messages sent (summary) and response (content + tool_calls)."""
    # Summarize messages for readability (role + content length or tool_calls)
    summary_lines = []
    for i, m in enumerate(messages_sent):
        role = m.get("role", "?")
        content = m.get("content") or ""
        tc = m.get("tool_calls")
        if tc:
            summary_lines.append(f"  [{i}] {role}: (content_len={len(content or '')}) tool_calls={len(tc)}")
        else:
            summary_lines.append(f"  [{i}] {role}: {content or ''}")
    messages_block = "\n".join(summary_lines)

    out_lines = [f"  content: {content or '(none)'}"]
    if tool_calls:
        out_lines.append(f"  tool_calls: {len(tool_calls)}")
        for j, tc in enumerate(tool_calls):
            fn = (tc.get("function") or {})
            out_lines.append(f"    [{j}] id={tc.get('id', '')} name={fn.get('name', '')} args={fn.get('arguments', '{}')}")
    payload = f"""
  round: {round_index}

  messages_sent (summary):
{messages_block}

  response:
{chr(10).join(out_lines)}
"""
    _write_chat_log("CHAT LLM ROUND", session_id, payload)


def log_chat_final_response(
    session_id: str,
    reply_text: str,
    used_fallback: bool,
    reminder: dict[str, Any] | None,
) -> None:
    """Log final assistant reply and metadata."""
    payload = f"""
  reply: {reply_text or ''}
  model_fallback: {used_fallback}
  reminder: {reminder is not None}
"""
    if reminder:
        payload += f"\n  reminder_payload:\n{_pretty_json(reminder)}"
    _write_chat_log("CHAT FINAL RESPONSE", session_id, payload)


def log_tool_call(
    session_id: str,
    tool_name: str,
    arguments: str | dict[str, Any],
    result: str,
    reminder_payload: dict[str, Any] | None,
) -> None:
    """Log a single tool invocation: name, arguments, result, and optional reminder."""
    args_str = arguments if isinstance(arguments, str) else _pretty_json(arguments)
    payload = f"""
  tool: {tool_name}
  arguments:
{args_str}

  result:
{result}
  reminder_returned: {reminder_payload is not None}
"""
    if reminder_payload:
        payload += f"\n  reminder:\n{_pretty_json(reminder_payload)}"
    _write_chat_log("TOOL CALL", session_id, payload)


def log_chat_error(session_id: str, phase: str, error_message: str) -> None:
    """Log a chat-phase error."""
    payload = f"""
  phase: {phase}
  error: {error_message or ''}
"""
    _write_chat_log("CHAT ERROR", session_id, payload)
