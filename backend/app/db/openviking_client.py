"""OpenViking context DB client with singleton lifecycle and explicit config loading."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.config import get_settings
from app.core.viking_logging import log_viking_client_close, log_viking_client_init

_client = None
_client_lock = Lock()


def get_openviking_path() -> Path:
    """Return OpenViking data directory (same base as SQLite)."""
    return get_settings().openviking_path()


def _load_openviking_config() -> dict[str, Any]:
    settings = get_settings()
    cfg_path = settings.resolved_openviking_config_path()
    if not cfg_path.exists():
        raise FileNotFoundError(f"OpenViking config not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _build_openviking_config(path: Path):
    from openviking.utils.config.embedding_config import EmbeddingConfig, EmbeddingModelConfig
    from openviking.utils.config.open_viking_config import OpenVikingConfig
    from openviking.utils.config.storage_config import AGFSConfig, StorageConfig
    from openviking.utils.config.vlm_config import VLMConfig

    settings = get_settings()
    raw = _load_openviking_config()
    dense_raw = ((raw.get("embedding") or {}).get("dense") or {}).copy()
    if not dense_raw:
        raise ValueError("OpenViking config missing embedding.dense")
    vlm_raw = (raw.get("vlm") or {}).copy()
    if not vlm_raw:
        raise ValueError("OpenViking config missing vlm")

    return OpenVikingConfig(
        storage=StorageConfig(
            agfs=AGFSConfig(
                path=str(path),
                port=settings.openviking_agfs_port,
                url=f"http://localhost:{settings.openviking_agfs_port}",
            )
        ),
        embedding=EmbeddingConfig(dense=EmbeddingModelConfig(**dense_raw)),
        vlm=VLMConfig(**vlm_raw),
    )


def get_openviking_client():
    """Return process-wide SyncOpenViking singleton."""
    import openviking as ov

    global _client
    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client

        settings = get_settings()
        cfg_path = settings.resolved_openviking_config_path()
        os.environ["OPENVIKING_CONFIG_FILE"] = str(cfg_path)

        path = get_openviking_path()
        path.mkdir(parents=True, exist_ok=True)
        try:
            config = _build_openviking_config(path)
            _client = ov.SyncOpenViking(path=str(path), config=config)
            log_viking_client_init(success=True)
            return _client
        except Exception as e:
            log_viking_client_init(success=False, error=str(e))
            raise


def close_openviking_client() -> None:
    """Close singleton client if initialized."""
    global _client
    with _client_lock:
        if _client is None:
            return
        try:
            _client.close()
            log_viking_client_close()
        finally:
            _client = None


def openviking_enabled() -> bool:
    """Whether OpenViking config exists and can be used."""
    settings = get_settings()
    return settings.resolved_openviking_config_path().exists()
