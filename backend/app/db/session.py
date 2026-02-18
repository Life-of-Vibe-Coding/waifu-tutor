"""SQLite connection and init. Sync for simplicity; init_db runs migrations."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _db_path() -> Path:
    p = get_settings().sqlite_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = _row_factory
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _row_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def init_db() -> None:
    """Run schema migrations. Called at startup."""
    from app.db.migrations import run_migrations

    run_migrations()
