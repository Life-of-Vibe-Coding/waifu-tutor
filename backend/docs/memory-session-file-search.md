# Memory, Session, and File Search

This document explains how conversation session persistence and **context search** (document chunks) are implemented in the backend.

## Overview

The backend supports:

- Session-aware chat (`session_id` across requests)
- Context for chat: **document chunks** from SQLite (no external context DB)
- Search trajectory output (`search_trace`) for observability/debug when `debug_search_trace=true`
- Session commit in SQLite and OpenViking in-memory lifecycle commit

Core modules:

- `app/api/chat.py`
- `app/api/sessions.py`
- `app/services/file_search.py` — document chunk context
- `app/api/documents.py`

## Data Model (SQLite)

Conversation records are persisted in SQLite:

- `chat_sessions`
  - `id`, `user_id`, `title`
  - `created_at`, `updated_at`, `last_message_at`, `committed_at`
- `chat_messages`
  - `id`, `session_id`, `user_id`, `role`, `content`, `created_at`

Migration source: `app/db/migrations.py`

Repository helpers: `upsert_chat_session`, `insert_chat_message`, `list_chat_sessions`, `list_chat_messages`, `mark_chat_session_committed`

## Session Lifecycle

### 1) Session creation / reuse

`POST /api/ai/chat` and `POST /api/ai/chat/stream` accept:

- `message`
- `history`
- `doc_id` (optional)
- `session_id` (optional)

If `session_id` is provided, the backend reuses it. If missing, the backend creates a new session ID and returns it.

### 2) Turn recording

For each completed exchange, the same exchange is persisted to SQLite (`chat_messages`).

### 3) Session commit

`POST /api/sessions/{session_id}/commit`:

- Marks SQLite `chat_sessions.committed_at` for the session.
- Commits OpenViking session state for the same `session_id` (hydrates from stored messages if needed).

## File Search (Context)

Context retrieval uses **document chunks** only. Logic is in `app/services/file_search.py` (`ContextSearchService`).

- When the user attaches a document (`doc_id`), chat loads chunks for that document from SQLite via `get_chunks_for_document(doc_id, limit)`.
- When no `doc_id` is set, no document context is loaded.
- Result shape: `chunk_id`, `doc_id`, `text`, `source="document"`, `score=1.0`, `uri=""`.

### Document ingestion

On upload (`POST /api/documents/upload`), the backend:

1. Parses and chunks the document
2. Writes chunks to SQLite (`document_chunks` table)
3. Sets document status to `ready`

No external indexing step.

### Query-time context

Chat uses `ContextSearchService.search(...)` which returns chunks for `doc_id` when provided. These are passed into the prompt as **Context** for the model.

### Search trace

When `debug_search_trace=true` in the request body, the response includes `search_trace` with `mode`, `doc_id`, and `result_count`.

## Chat Response Contract

`POST /api/ai/chat` returns:

- `message`
- `mood`
- `session_id`
- `model_fallback` (when fallback model was used)
- `search_trace` (optional, when `debug_search_trace=true`)

`POST /api/ai/chat/stream` events: `token`, `mood`, `done` (with `message`, `session_id`), optional `reminder`.

## Session APIs

- `GET /api/sessions` — list sessions from SQLite
- `GET /api/sessions/{session_id}` — session metadata + messages
- `POST /api/sessions/{session_id}/commit` — set SQLite `committed_at`
  - Also returns OpenViking commit metadata in `commit.openviking`.

## Frontend Integration

Frontend tracks `sessionId` in Zustand. Chat API calls pass `session_id`. `ChatPage` updates `sessionId` from the backend and provides a "New Chat" action.

## Quick Verification

```bash
cd backend
uv run python -c "from app.api.sessions import list_sessions; print(list_sessions(20))"
```

For full chat flow, call `POST /api/ai/chat` with a valid body (e.g. via frontend or curl).
