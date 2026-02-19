"""OpenViking context DB client: config from .openviking/ov.conf, data under openviking_data_dir."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    import openviking as ov

logger = logging.getLogger(__name__)

_initialized_client: "ov.SyncOpenViking | None" = None


def get_openviking_path() -> Path:
    """Return the OpenViking data directory (from settings, referring to .openviking/ov.conf for config)."""
    return get_settings().openviking_data_dir.resolve()


def _ensure_config_env() -> None:
    """Set OPENVIKING_CONFIG_FILE from settings so the openviking library uses .openviking/ov.conf."""
    settings = get_settings()
    config_path = Path(settings.openviking_config_file).resolve()
    if config_path.exists():
        os.environ["OPENVIKING_CONFIG_FILE"] = str(config_path)
    else:
        logger.warning("OpenViking config not found at %s; indexing will be skipped.", config_path)


def get_openviking_client():  # -> ov.SyncOpenViking
    """Return an initialized SyncOpenViking client. Config from .openviking/ov.conf, data in openviking_data_dir."""
    global _initialized_client
    if _initialized_client is not None:
        return _initialized_client
    _ensure_config_env()
    import openviking as ov

    data_path = get_openviking_path()
    data_path.mkdir(parents=True, exist_ok=True)
    client = ov.SyncOpenViking(path=str(data_path))
    client.initialize()
    _initialized_client = client
    return client


def index_document(storage_path: Path, doc_id: str) -> str | None:
    """
    Index a document file into OpenViking. Config and data dir come from settings (.openviking/ov.conf).
    Returns the root_uri (viking://...) on success, None if config missing or indexing fails.
    """
    if not Path(get_settings().openviking_config_file).resolve().exists():
        logger.info("OpenViking config missing; skip indexing for doc %s", doc_id)
        return None
    path_str = str(storage_path.resolve())
    if not storage_path.exists():
        logger.warning("Document file not found for OpenViking: %s", path_str)
        return None
    try:
        client = get_openviking_client()
        result = client.add_resource(path=path_str)
        root_uri = result.get("root_uri")
        if root_uri:
            logger.info("OpenViking indexed doc %s -> %s", doc_id, root_uri)
            return root_uri
        logger.warning("OpenViking add_resource returned no root_uri for %s", doc_id)
        return None
    except Exception as e:
        logger.exception("OpenViking indexing failed for doc %s: %s", doc_id, e)
        return None
