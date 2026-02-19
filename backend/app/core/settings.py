"""Application settings from environment."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to backend/ (works regardless of cwd)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ENV_FILE = _BACKEND_DIR / ".env"


@lru_cache(maxsize=4)
def _read_openviking_conf(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    try:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # Database (db/ at project root)
    database_url: str = "sqlite:///../db/data/waifu_tutor.db"

    # Uploads
    upload_dir: Path = Path("../db/data/uploads")
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MiB

    # AI: Volcengine ARK (e.g. doubao-seed-2-0-mini-260215)
    volcengine_api_key: str | None = None
    volcengine_chat_base: str = "https://ark.cn-beijing.volces.com/api/v3"
    chat_model: str = "doubao-seed-2-0-mini-260215"
    # Timeout in seconds for chat/tool completion (long skill+subskill context may need >45s)
    chat_request_timeout: float = 90.0

    # Demo user
    demo_user_id: str = "demo-user"
    demo_email: str = "demo@waifu.local"
    demo_display_name: str = "Demo Student"

    # Logging: base directory (default: backend/logs). Subdirs: chat/. Set LOG_DIR in .env to override.
    log_dir: Path = Path("logs")

    # Skills: root directory for hierarchical skills (SKILL.md + subskills). Default: docs/skill-framework.
    skills_dir: Path = _PROJECT_ROOT / "docs" / "skill-framework"
    # OpenViking config file root
    openviking_conf_path: Path = _PROJECT_ROOT / ".openviking" / "ov.conf"
    # Session defaults (can be overridden by .openviking/ov.conf -> session)
    openviking_session_backend: str = "openviking"
    openviking_session_max_cached: int = 1000
    openviking_session_hydrate_on_commit: bool = True

    def sqlite_path(self) -> Path:
        url = self.database_url.strip()
        for prefix in ("sqlite:", "file:"):
            if url.startswith(prefix):
                url = url[len(prefix) :].lstrip("/")
                break
        return Path(url) if url else Path("./data/waifu_tutor.db")

    def openviking_conf(self) -> dict[str, Any]:
        return _read_openviking_conf(str(self.openviking_conf_path.resolve()))

    def openviking_session_conf(self) -> dict[str, Any]:
        raw = self.openviking_conf().get("session", {})
        conf = raw if isinstance(raw, dict) else {}
        backend = str(conf.get("backend", self.openviking_session_backend) or self.openviking_session_backend)
        max_cached_raw = conf.get("max_cached", conf.get("max_sessions", self.openviking_session_max_cached))
        try:
            max_cached = int(max_cached_raw)
        except Exception:
            max_cached = self.openviking_session_max_cached
        hydrate = conf.get("hydrate_on_commit", self.openviking_session_hydrate_on_commit)
        hydrate_on_commit = bool(hydrate) if isinstance(hydrate, bool) else str(hydrate).lower() in ("1", "true", "yes", "on")
        if max_cached < 1:
            max_cached = self.openviking_session_max_cached
        return {
            "backend": backend,
            "max_cached": max_cached,
            "hydrate_on_commit": hydrate_on_commit,
        }
