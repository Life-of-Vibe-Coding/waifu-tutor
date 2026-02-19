"""Single file for logging all text (agent context, debug dumps, etc.).

Logs are written to log_dir/all/all.log. When it reaches 10 MB it is rotated
to all_yyyy_MM_dd_HH_mm.log. Use log_text() from this module.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.typed_logging import get_typed_file_logger

_ALL_LOGGER_NAME = "all"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def log_text(text: str, section: str = "") -> None:
    """Append text to logs/all/all.log. Optionally prefix with a section label."""
    logger = get_typed_file_logger("all", _ALL_LOGGER_NAME)
    if section:
        msg = f"\n{'=' * 80}\n  [{_timestamp()}]  {section}\n{'=' * 80}\n{text.strip()}\n"
    else:
        msg = f"[{_timestamp()}]  {text.strip()}\n"
    logger.info(msg)
