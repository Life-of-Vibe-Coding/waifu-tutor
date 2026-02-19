"""In-memory store for pending HITL checkpoints. TTL 30 minutes."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_PENDING: dict[str, dict[str, Any]] = {}
_TTL_SEC = 30 * 60  # 30 minutes


def set_pending(
    session_id: str,
    user_id: str,
    messages: list[dict[str, Any]],
    tool_call_id: str,
    hitl_input: dict[str, Any],
    user_timezone: str | None = None,
) -> str:
    """Store pending HITL state. Returns checkpoint_id."""
    checkpoint_id = str(uuid.uuid4())
    _PENDING[checkpoint_id] = {
        "checkpoint_id": checkpoint_id,
        "session_id": session_id,
        "user_id": user_id,
        "user_timezone": user_timezone,
        "messages": messages,
        "tool_call_id": tool_call_id,
        "hitl_input": hitl_input,
        "created_at": time.monotonic(),
    }
    logger.info("HITL pending set: checkpoint_id=%s session_id=%s", checkpoint_id, session_id)
    return checkpoint_id


def get_pending(checkpoint_id: str) -> dict[str, Any] | None:
    """Return pending state if found and not expired. Does not remove."""
    entry = _PENDING.get(checkpoint_id)
    if not entry:
        return None
    if time.monotonic() - entry["created_at"] > _TTL_SEC:
        del _PENDING[checkpoint_id]
        return None
    return entry


def consume_pending(checkpoint_id: str) -> dict[str, Any] | None:
    """Load and remove pending state. Returns None if missing or expired."""
    entry = get_pending(checkpoint_id)
    if entry:
        _PENDING.pop(checkpoint_id, None)
    return entry
