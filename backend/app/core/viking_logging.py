"""Structured logging for OpenViking operations (client lifecycle, sessions, indexing, search, etc.).

Logs are written to log_dir/viking/viking.log. Use log_viking_* from this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.typed_logging import get_typed_file_logger

_VIKING_LOGGER_KEY = "file"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _format_extra(**kwargs: Any) -> str:
    if not kwargs:
        return ""
    parts = [f"  {k}: {v}" for k, v in kwargs.items() if v is not None]
    return "\n" + "\n".join(parts) if parts else ""


def log_viking_operation(
    operation: str,
    detail: str,
    session_id: str | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Log one Viking operation (e.g. client_init, session_load, search, index, commit)."""
    logger = get_typed_file_logger("viking", _VIKING_LOGGER_KEY)
    lines = [
        "",
        "-" * 60,
        f"  [{_ts()}]  {operation}",
        f"  detail: {detail}",
    ]
    if session_id is not None:
        lines.append(f"  session_id: {session_id}")
    if error is not None:
        lines.append(f"  error: {error}")
    lines.append(_format_extra(**extra))
    logger.info("\n".join(lines).strip())


def log_viking_client_init(success: bool, error: str | None = None) -> None:
    """Log OpenViking client initialization."""
    log_viking_operation(
        "client_init",
        "ok" if success else "failed",
        error=error,
    )


def log_viking_client_close() -> None:
    """Log OpenViking client close."""
    log_viking_operation("client_close", "ok")


def log_viking_session_load(session_id: str, found: bool) -> None:
    """Log loading a session."""
    log_viking_operation(
        "session_load",
        "found" if found else "new",
        session_id=session_id,
    )


def log_viking_search(query: str, scope: str, result_count: int, error: str | None = None) -> None:
    """Log a Viking file search."""
    log_viking_operation(
        "search",
        f"scope={scope} results={result_count}",
        error=error,
        query=query or "",
    )


def log_viking_auto_commit(session_id: str, messages_committed: int, success: bool, error: str | None = None) -> None:
    """Log auto-commit of session to memory."""
    log_viking_operation(
        "auto_commit",
        f"messages={messages_committed} success={success}",
        session_id=session_id,
        error=error,
    )


def log_viking_index_document(doc_id: str, storage_path: str, success: bool, openviking_uri: str | None = None, error: str | None = None) -> None:
    """Log document indexing into OpenViking."""
    log_viking_operation(
        "index_document",
        f"doc_id={doc_id} path={storage_path} success={success}",
        error=error,
        openviking_uri=openviking_uri,
    )
