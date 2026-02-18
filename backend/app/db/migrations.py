"""SQLite schema and migrations."""
from __future__ import annotations

import sqlite3
import uuid

from app.core.config import get_settings


def run_migrations() -> None:
    settings = get_settings()
    conn = _get_conn()
    try:
        _migrate_break_reminders_to_reminders(conn)
        conn.executescript(_SCHEMA)
        for sql in _TRIGGERS:
            conn.execute(sql)
        _migrate_documents_add_openviking_uri(conn)
        _migrate_documents_add_source_folder(conn)
        _seed_demo_user(conn, settings)
        conn.commit()
    finally:
        conn.close()


def _migrate_break_reminders_to_reminders(conn: sqlite3.Connection) -> None:
    """Rename table break_reminders to reminders for generic reminder support."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='break_reminders'")
    has_old = cur.fetchone() is not None
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reminders'")
    has_new = cur.fetchone() is not None
    if has_new:
        cur = conn.execute("PRAGMA table_info(reminders)")
        columns = [row["name"] for row in cur.fetchall()]
        if "session_id" not in columns:
            conn.execute("DROP TABLE reminders")
            has_new = False
    if not has_old:
        return
    if has_new:
        conn.execute("DROP TABLE break_reminders")
        return
    conn.execute("ALTER TABLE break_reminders RENAME TO reminders")


def _migrate_documents_add_openviking_uri(conn: sqlite3.Connection) -> None:
    """Add openviking_uri to documents if the table exists but column is missing."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
    if cur.fetchone() is None:
        return
    cur = conn.execute("PRAGMA table_info(documents)")
    columns = [row["name"] for row in cur.fetchall()]
    if "openviking_uri" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN openviking_uri TEXT")


def _migrate_documents_add_source_folder(conn: sqlite3.Connection) -> None:
    """Add source_folder to documents for folder upload tracking."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
    if cur.fetchone() is None:
        return
    cur = conn.execute("PRAGMA table_info(documents)")
    columns = [row["name"] for row in cur.fetchall()]
    if "source_folder" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN source_folder TEXT")


def _get_conn() -> sqlite3.Connection:
    from app.db.session import get_conn

    return get_conn()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  display_name TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subjects (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  subject_id TEXT REFERENCES subjects(id),
  title TEXT NOT NULL,
  filename TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  status TEXT DEFAULT 'processing',
  word_count INTEGER DEFAULT 0,
  topic_hint TEXT,
  difficulty_estimate TEXT,
  storage_path TEXT NOT NULL,
  openviking_uri TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL REFERENCES documents(id),
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  page INTEGER,
  section TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
  chunk_text,
  doc_id UNINDEXED,
  chunk_index UNINDEXED,
  content='document_chunks',
  content_rowid='rowid'
);

CREATE TABLE IF NOT EXISTS chat_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  title TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  last_message_at TEXT,
  committed_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES chat_sessions(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated
ON chat_sessions(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
ON chat_messages(session_id, created_at ASC);

CREATE TABLE IF NOT EXISTS reminders (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  due_at TEXT NOT NULL,
  message TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'break' CHECK (kind IN ('break', 'focus')),
  status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'due', 'acknowledged')),
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reminders_session_status
ON reminders(session_id, status);
"""

_TRIGGERS = [
    """CREATE TRIGGER IF NOT EXISTS document_chunks_ai AFTER INSERT ON document_chunks BEGIN
  INSERT INTO document_chunks_fts(rowid, chunk_text, doc_id, chunk_index)
  VALUES (new.rowid, new.chunk_text, new.doc_id, new.chunk_index);
END""",
    """CREATE TRIGGER IF NOT EXISTS document_chunks_ad AFTER DELETE ON document_chunks BEGIN
  INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, doc_id, chunk_index)
  VALUES('delete', old.rowid, old.chunk_text, old.doc_id, old.chunk_index);
END""",
    """CREATE TRIGGER IF NOT EXISTS document_chunks_au AFTER UPDATE ON document_chunks BEGIN
  INSERT INTO document_chunks_fts(document_chunks_fts, rowid, chunk_text, doc_id, chunk_index)
  VALUES('delete', old.rowid, old.chunk_text, old.doc_id, old.chunk_index);
  INSERT INTO document_chunks_fts(rowid, chunk_text, doc_id, chunk_index)
  VALUES(new.rowid, new.chunk_text, new.doc_id, new.chunk_index);
END""",
]


def _seed_demo_user(conn: sqlite3.Connection, settings) -> None:
    demo_id = settings.demo_user_id
    cur = conn.execute("SELECT 1 FROM users WHERE id = ?", (demo_id,))
    if cur.fetchone() is not None:
        return
    conn.execute(
        "INSERT INTO users (id, email, display_name) VALUES (?, ?, ?)",
        (demo_id, settings.demo_email, settings.demo_display_name),
    )
    conn.execute(
        "INSERT INTO subjects (id, user_id, name) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), demo_id, "General"),
    )
