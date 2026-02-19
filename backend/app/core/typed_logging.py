"""Shared infrastructure for typed log directories and file loggers.

Log layout: log_dir/<type>/<basename>.log
- chat -> logs/chat/chat.log
- all  -> logs/all/all.log (all text via app.core.text_logging.log_text)
Add new types by using get_log_dir_for() and get_typed_file_logger().
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Max size per log file before rotation (10 MB)
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def get_log_base_dir(settings: Any = None) -> Path:
    """Return the base log directory (e.g. backend/logs), creating it if needed."""
    from app.core.config import get_settings

    s = settings or get_settings()
    log_dir = getattr(s, "log_dir", None) or Path("logs")
    if not log_dir.is_absolute():
        backend_root = Path(__file__).resolve().parent.parent.parent
        log_dir = backend_root / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_dir_for(log_type: str, settings: Any = None) -> Path:
    """Return log_dir/<log_type>, e.g. logs/chat. Creates the dir if needed."""
    base = get_log_base_dir(settings)
    sub = base / log_type
    sub.mkdir(parents=True, exist_ok=True)
    return sub


def _rotation_namer(default_name: str, prefix: str) -> str:
    parent = Path(default_name).parent
    ts = datetime.now(timezone.utc).strftime("%Y_%m_%d_%H_%M")
    return str(parent / f"{prefix}_{ts}.log")


def get_typed_file_logger(
    log_type: str,
    logger_name: str,
    file_basename: str | None = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    settings: Any = None,
) -> logging.Logger:
    """Return a logger that writes to log_dir/<log_type>/<file_basename or log_type>.log with rotation."""
    from app.core.config import get_settings

    s = settings or get_settings()
    name = file_basename or log_type
    logger = logging.getLogger(f"waifu.{log_type}.{logger_name}")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_dir = get_log_dir_for(log_type, s)
    path = log_dir / f"{name}.log"

    def namer(default_name: str) -> str:
        return _rotation_namer(default_name, name)

    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=0,
        encoding="utf-8",
    )
    handler.namer = namer
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger
