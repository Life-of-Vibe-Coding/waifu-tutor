"""Application settings from environment."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to backend/ (works regardless of cwd)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ENV_FILE = _BACKEND_DIR / ".env"


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

    # Demo user
    demo_user_id: str = "demo-user"
    demo_email: str = "demo@waifu.local"
    demo_display_name: str = "Demo Student"

    # Logging: base directory (default: backend/logs). Subdirs: chat/. Set LOG_DIR in .env to override.
    log_dir: Path = Path("logs")

    # OpenViking: config file (embedding + VLM) and data directory. Config defaults to project .openviking/ov.conf.
    openviking_config_file: Path = _PROJECT_ROOT / ".openviking" / "ov.conf"
    openviking_data_dir: Path = _PROJECT_ROOT / "db" / "data" / "openviking"

    @field_validator("openviking_config_file", "openviking_data_dir", mode="before")
    @classmethod
    def _path_from_str(cls, v: Path | str) -> Path:
        return Path(v) if isinstance(v, str) else v

    def sqlite_path(self) -> Path:
        url = self.database_url.strip()
        for prefix in ("sqlite:", "file:"):
            if url.startswith(prefix):
                url = url[len(prefix) :].lstrip("/")
                break
        return Path(url) if url else Path("./data/waifu_tutor.db")
