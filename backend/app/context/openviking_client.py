"""OpenViking client bootstrap."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

_CLIENT: Any | None = None
logger = logging.getLogger(__name__)


def initialize_openviking_client() -> Any | None:
    """Initialize and cache SyncOpenViking client."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        import openviking as ov  # type: ignore
    except Exception:
        return None
    project_conf = Path(__file__).resolve().parents[3] / ".openviking" / "ov.conf"
    if project_conf.exists() and "OPENVIKING_CONFIG_FILE" not in os.environ:
        os.environ["OPENVIKING_CONFIG_FILE"] = str(project_conf)
    try:
        Path("./data").mkdir(parents=True, exist_ok=True)
        client = ov.SyncOpenViking(path="./data")
        client.initialize()
        _CLIENT = client
        return _CLIENT
    except Exception as exc:
        logger.warning("OpenViking client initialization failed, falling back to in-memory session mode: %s", exc)
        return None


def get_openviking_client() -> Any | None:
    return _CLIENT
