"""Repository helpers for documents, sessions, and chat context."""
from __future__ import annotations

from app.db.session import get_conn


def list_documents(user_id: str) -> list[dict]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id, user_id, subject_id, title, filename, mime_type, size_bytes, status, word_count,"
            " topic_hint, difficulty_estimate, storage_path, openviking_uri, created_at, updated_at"
            " FROM documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_document(doc_id: str, user_id: str) -> dict | None:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id, user_id, subject_id, title, filename, mime_type, size_bytes, status, word_count,"
            " topic_hint, difficulty_estimate, storage_path, openviking_uri, created_at, updated_at"
            " FROM documents WHERE id = ? AND user_id = ?",
            (doc_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def insert_document(
    doc_id: str,
    user_id: str,
    title: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    storage_path: str,
    status: str = "processing",
    subject_id: str | None = None,
) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO documents (id, user_id, subject_id, title, filename, mime_type, size_bytes, status, storage_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, user_id, subject_id, title, filename, mime_type, size_bytes, status, storage_path),
        )
        conn.commit()
    finally:
        conn.close()


def update_document_status(
    doc_id: str,
    status: str,
    word_count: int | None = None,
    openviking_uri: str | None = None,
) -> None:
    conn = get_conn()
    try:
        if word_count is not None:
            conn.execute(
                "UPDATE documents SET status = ?, word_count = ?, updated_at = datetime('now'), openviking_uri = COALESCE(?, openviking_uri) WHERE id = ?",
                (status, word_count, openviking_uri, doc_id),
            )
        else:
            conn.execute(
                "UPDATE documents SET status = ?, updated_at = datetime('now'), openviking_uri = COALESCE(?, openviking_uri) WHERE id = ?",
                (status, openviking_uri, doc_id),
            )
        conn.commit()
    finally:
        conn.close()


def set_document_subject(doc_id: str, user_id: str, subject_id: str | None) -> dict | None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE documents SET subject_id = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?",
            (subject_id, doc_id, user_id),
        )
        conn.commit()
        cur = conn.execute(
            "SELECT id, user_id, subject_id, title, filename, mime_type, size_bytes, status, word_count,"
            " topic_hint, difficulty_estimate, storage_path, openviking_uri, created_at, updated_at"
            " FROM documents WHERE id = ? AND user_id = ?",
            (doc_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_chunks_for_document(doc_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
        conn.commit()
    finally:
        conn.close()


def insert_chunk(
    chunk_id: str,
    doc_id: str,
    chunk_index: int,
    chunk_text: str,
    page: int | None = None,
    section: str | None = None,
) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO document_chunks (id, doc_id, chunk_index, chunk_text, page, section) VALUES (?, ?, ?, ?, ?, ?)",
            (chunk_id, doc_id, chunk_index, chunk_text, page, section),
        )
        conn.commit()
    finally:
        conn.close()


def get_chunks_for_document(doc_id: str, limit: int = 50) -> list[dict]:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT id, doc_id, chunk_index, chunk_text, page, section FROM document_chunks WHERE doc_id = ? ORDER BY chunk_index LIMIT ?",
            (doc_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def upsert_chat_session(session_id: str, user_id: str, title: str | None = None) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO chat_sessions (id, user_id, title, last_message_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
              updated_at = datetime('now'),
              last_message_at = datetime('now'),
              title = COALESCE(chat_sessions.title, excluded.title)
            """,
            (session_id, user_id, title),
        )
        conn.commit()
    finally:
        conn.close()


def get_chat_session(session_id: str, user_id: str) -> dict | None:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT id, user_id, title, created_at, updated_at, last_message_at, committed_at
            FROM chat_sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_chat_sessions(user_id: str, limit: int = 50) -> list[dict]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT id, user_id, title, created_at, updated_at, last_message_at, committed_at
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY COALESCE(last_message_at, updated_at, created_at) DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def insert_chat_message(message_id: str, session_id: str, user_id: str, role: str, content: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO chat_messages (id, session_id, user_id, role, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, session_id, user_id, role, content),
        )
        conn.execute(
            """
            UPDATE chat_sessions
            SET updated_at = datetime('now'), last_message_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_chat_messages(session_id: str, user_id: str, limit: int = 500) -> list[dict]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            SELECT id, session_id, user_id, role, content, created_at
            FROM chat_messages
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (session_id, user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def mark_chat_session_committed(session_id: str, user_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE chat_sessions
            SET committed_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()
