"""Application settings from environment."""
from pathlib import Path

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

    def sqlite_path(self) -> Path:
        url = self.database_url.strip()
        for prefix in ("sqlite:", "file:"):
            if url.startswith(prefix):
                url = url[len(prefix) :].lstrip("/")
                break
        return Path(url) if url else Path("./data/waifu_tutor.db")
