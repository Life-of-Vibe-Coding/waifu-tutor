"""Application settings from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to backend/ (works regardless of cwd)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
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

    # Logging: base directory (default: backend/logs). Subdirs: chat/, viking/. Set LOG_DIR in .env to override.
    log_dir: Path = Path("logs")

    # OpenViking context DB (uses same data root as SQLite: db/data/openviking)
    openviking_data_dir: str | None = None  # None = auto: same base as DB
    openviking_config_file: str | None = None
    openviking_agfs_port: int = 9090
    openviking_auto_commit_turns: int = 24

    def sqlite_path(self) -> Path:
        url = self.database_url.strip()
        for prefix in ("sqlite:", "file:"):
            if url.startswith(prefix):
                url = url[len(prefix) :].lstrip("/")
                break
        return Path(url) if url else Path("./data/waifu_tutor.db")

    def openviking_path(self) -> Path:
        """Path for OpenViking data; reuses existing db data dir."""
        if self.openviking_data_dir:
            return Path(self.openviking_data_dir)
        return self.sqlite_path().parent / "openviking"

    def resolved_openviking_config_path(self) -> Path:
        """Resolve OpenViking config path. Defaults to backend/.openviking/ov.conf."""
        if self.openviking_config_file:
            return Path(self.openviking_config_file)
        return _BACKEND_DIR / ".openviking" / "ov.conf"
