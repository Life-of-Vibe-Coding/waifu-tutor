"""Structured, readable logging for chat process and tool calling.

Logs are written to log_dir/chat/chat.log. When chat.log reaches 10 MB it is rotated:
current file is renamed to chat_yyyy_MM_dd_HH_mm.log and a new chat.log is started.
Use log_chat_* and log_tool_* from this module; do not depend on global logger names.
"""
from __future__ import annotations

import json
import logging
import sys
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
    logger = _get_chat_file_logger("file", "chat")
    logger.info(msg)
    # Flush so tail -f and editors see new content immediately
    for h in logger.handlers:
        h.flush()
    # Echo CHAT LLM ROUND (prompts) to stderr so they appear in the terminal
    if section == "CHAT LLM ROUND":
        print(msg, file=sys.stderr)
        sys.stderr.flush()


def log_agent_context_startup(context_text: str) -> None:
    """Write agent context (tools) to logs/chat/chat.log at startup."""
    _write_chat_log("AGENT CONTEXT (startup)", "(startup)", context_text or "(empty)")


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
  === CONTEXT SUMMARY BEGIN ===
  attachment_title: {attachment_title}
  persona_preview: {persona_preview or ''}

  context_blocks:
{ctx_preview or '  (none)'}
  === CONTEXT SUMMARY END ===
"""
    _write_chat_log("CHAT CONTEXT SUMMARY", session_id, payload)


def log_chat_agent_input(session_id: str, prompt_text: str) -> None:
    """Log the full prompt/context sent to the agent for this turn."""
    payload = f"""
  === AGENT INPUT BEGIN ===
{_truncate_for_log(prompt_text or '')}
  === AGENT INPUT END ===
"""
    _write_chat_log("CHAT AGENT INPUT (FULL)", session_id, payload)


# Max characters to log per message role to avoid huge log files (None = no truncation)
_CHAT_HISTORY_LOG_MAX_CHARS = 16_000


def _truncate_for_log(text: str, max_chars: int = _CHAT_HISTORY_LOG_MAX_CHARS) -> str:
    if not text or max_chars is None or len(text) <= max_chars:
        return text or ""
    segment = text[: max_chars + 1]
    last_break = max(segment.rfind(" "), segment.rfind("\n"))
    if last_break >= 0:
        cut = text[:last_break]
    else:
        cut = text[:max_chars]
    return cut + "\n... [truncated]"


def log_chat_llm_round(
    session_id: str,
    round_index: int,
    messages_sent: list[dict[str, Any]],
    content: str | None,
    tool_calls: list[dict[str, Any]] | None,
) -> None:
    """Log one LLM round: chat history and response (content + tool_calls)."""
    # Build full chat history for this round: system prompt, user prompt, agent prompt, tool results
    history_lines = []
    for i, m in enumerate(messages_sent):
        role = m.get("role", "?")
        msg_content = m.get("content") or ""
        tc = m.get("tool_calls")
        label = {"system": "system_prompt", "user": "user_prompt", "assistant": "agent_prompt", "tool": "tool_result"}.get(role, role)
        history_lines.append(f"  --- [{i}] {role} ({label}) ---")
        if tc:
            history_lines.append(f"  tool_calls: {len(tc)}")
            for j, t in enumerate(tc):
                fn = t.get("function") or {}
                history_lines.append(f"    [{j}] id={t.get('id', '')} name={fn.get('name', '')} args={fn.get('arguments', '{}')}")
        if msg_content:
            history_lines.append(_truncate_for_log(msg_content))
        history_lines.append("")
    chat_history_block = "\n".join(history_lines)

    out_lines = []
    if content:
        out_lines.append("  content:")
        out_lines.append(_truncate_for_log(content))
    if tool_calls:
        out_lines.append(f"  tool_calls: {len(tool_calls)}")
        for j, tc in enumerate(tool_calls):
            fn = (tc.get("function") or {})
            out_lines.append(f"    [{j}] id={tc.get('id', '')} name={fn.get('name', '')} args={fn.get('arguments', '{}')}")
    payload = f"""
  round: {round_index}

  chat_history (system / user / agent / tool):
{chat_history_block}

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
    loop_context: dict[str, Any] | None = None,
) -> None:
    """Log a single tool invocation: name, arguments, result, and optional reminder."""
    args_str = arguments if isinstance(arguments, str) else _pretty_json(arguments)
    loop_lines: list[str] = []
    if isinstance(loop_context, dict):
        round_index = loop_context.get("round_index")
        max_rounds = loop_context.get("max_rounds")
        execution_index = loop_context.get("execution_index")
        execution_total = loop_context.get("execution_total")
        tool_call_id = loop_context.get("tool_call_id")
        if round_index is not None and max_rounds is not None:
            loop_lines.append(f"  loop_round: {round_index}/{max_rounds}")
        elif round_index is not None:
            loop_lines.append(f"  loop_round: {round_index}")
        if execution_index is not None and execution_total is not None:
            loop_lines.append(f"  loop_execution: {execution_index}/{execution_total}")
        elif execution_index is not None:
            loop_lines.append(f"  loop_execution: {execution_index}")
        if tool_call_id:
            loop_lines.append(f"  tool_call_id: {tool_call_id}")
    loop_prefix = "\n".join(loop_lines)
    if loop_prefix:
        loop_prefix += "\n"
    payload = f"""
{loop_prefix}  tool: {tool_name}
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
