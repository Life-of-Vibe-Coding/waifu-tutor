# Memory, Session, and OpenViking File Search

This document explains how conversation session persistence, agentic memory, and **OpenViking file search** (context retrieval over the `viking://` filesystem) are implemented in the backend.

## Overview

The backend supports:

- Session-aware chat (`session_id` across requests)
- Multi-tier memory:
  - short-term memory (recent turns)
  - conversational/session memory (OpenViking session context + summaries)
  - long-term memory (OpenViking memory retrieval)
- **OpenViking file search paradigm**: search the context filesystem by URI scope; directory recursive retrieval; L0/L1 tiered content (abstract/overview)
- SQLite fallback for context when OpenViking is unavailable
- Search trajectory output (`search_trace`) for observability/debug
- Automatic session self-iteration (auto-commit threshold)

Core modules:

- `app/api/chat.py`
- `app/api/sessions.py`
- `app/services/memory.py`
- `app/services/file_search.py` — OpenViking file search over `viking://`
- `app/db/openviking_client.py`
- `app/api/documents.py`

## Connection Prerequisites

OpenViking integration uses:

- config file: `backend/.openviking/ov.conf`
- AGFS port: `9090` (to avoid local `8080` conflicts)
- singleton client: `app/db/openviking_client.py`

Key settings in `app/core/settings.py`:

- `openviking_config_file`
- `openviking_agfs_port`
- `openviking_data_dir`

## Data Model (SQLite)

Conversation records are persisted in SQLite:

- `chat_sessions`
  - `id`, `user_id`, `title`
  - `created_at`, `updated_at`, `last_message_at`, `committed_at`
- `chat_messages`
  - `id`, `session_id`, `user_id`, `role`, `content`, `created_at`

Migration source:

- `app/db/migrations.py`

Repository helpers:

- `upsert_chat_session`
- `insert_chat_message`
- `list_chat_sessions`
- `list_chat_messages`
- `mark_chat_session_committed`

## Session Lifecycle

### 1) Session creation / reuse

`POST /api/ai/chat` and `POST /api/ai/chat/stream` accept:

- `message`
- `history`
- `doc_id` (optional)
- `session_id` (optional)

If `session_id` is provided, backend loads that OpenViking session.
If missing, backend creates a new session and returns its `session_id`.

### 2) Turn recording

For each completed exchange:

- User + assistant turns are added into OpenViking session (`session.add_message(...)`)
- Same exchange is persisted to SQLite (`chat_messages`)

### 3) Session commit

`POST /api/sessions/{session_id}/commit`:

- Triggers `session.commit()` via `MemoryManager`
- Marks SQLite `chat_sessions.committed_at`

## Memory Tiers

Memory logic is centralized in `app/services/memory.py`.

### Short-term memory

- Source: current session recent messages
- API: `get_short_term_context(session, limit=10)`
- Use: inject latest turns into chat context assembly

### Conversational (session-based) memory

- Source: `session.get_context_for_search(...)`
- API: `get_session_context(session, query, ...)`
- Contains:
  - relevant archive summaries
  - recent messages for intent/context continuity

### Long-term memory

- Source: `client.search(query, limit=...)`
- API: `get_long_term_memories(query, limit=5)`
- Use: retrieve persistent memory traces across sessions

## OpenViking File Search Paradigm

Context retrieval follows the **OpenViking filesystem paradigm**: all context lives under `viking://` URIs; the backend **searches** this virtual filesystem by scope and uses **tiered loading** (L0 abstract, L1 overview, L2 detail) so only relevant content is loaded into the prompt.

File search logic is in `app/services/file_search.py` (`ContextSearchService`).

### URI layout

- User resources root: `viking://resources/users/{user_id}`
- Single document: `viking://resources/users/{user_id}/documents/{doc_id}`

Documents are ingested as resources under these paths; search is scoped to a directory (or the whole user root) so OpenViking can do **directory recursive retrieval** (L0 → L1 → optional L2 drill-down).

### Document ingestion

On upload (`POST /api/documents/upload`), backend:

1. Parses and chunks the document (existing parser)
2. Writes chunks to SQLite (for fallback)
3. Calls OpenViking filesystem API:
   - `client.add_resource(path=storage_path, target="viking://resources/users/{user_id}/documents/{doc_id}", wait=False)`

OpenViking indexes the file under that URI and generates L0/L1 (and L2) for the node. `wait=False` keeps upload latency low; indexing is asynchronous.

### Query-time file search

Chat uses `ContextSearchService.search(...)`:

- **Scope (target_uri)**:
  - If `doc_id` is set: `viking://resources/users/{user_id}/documents/{doc_id}` (single document)
  - Otherwise: `viking://resources/users/{user_id}` (user root; directory recursive search)
- **API**: `client.search(query, target_uri=target_uri, session=session, limit=limit)` so session context can participate in retrieval
- **Result**: OpenViking returns matched nodes (files/directories) with `uri`, `abstract`, `overview`, `score`, etc.

Text used for prompt injection follows **tiered loading**: prefer L1 (`overview`), then L0 (`abstract`), then `match_reason`. This avoids dumping raw L2 into the prompt unless needed.

### Normalized search result shape

Each hit is normalized to:

- `chunk_id` (from URI or synthetic)
- `doc_id` (parsed from URI when applicable)
- `text` (overview / abstract / match_reason)
- `source` = `semantic` (OpenViking) or `document` (SQLite fallback)
- `score`
- `uri`

These are merged into the assembled prompt under **Context file search results**.

### File search configuration

#### 1) Backend runtime settings

From `app/core/settings.py`:

- `openviking_agfs_port` (default: `9090`)
- `openviking_config_file` (optional override)
- `openviking_data_dir` (optional override)

These affect OpenViking startup and where index data is stored.

#### 2) OpenViking model config (`ov.conf`)

From `backend/.openviking/ov.conf`, file search and indexing depend on:

- `embedding.dense` — vector search over L0 abstracts
- `vlm` — richer retrieval/rerank and L0/L1 generation for non-text resources

Use **Doubao-Seed-1.8** for `vlm.model` to align with chat (see `CHAT_MODEL` in settings). If the model is not activated in Ark, retrieval can fail and fallback will be used.

#### 3) Query-time parameters

From `app/api/chat.py` and `app/services/file_search.py`:

- Top-k limit: `FILE_SEARCH_TOP_N = 5`
- Method: `client.search(...)` (session-aware), not `find(...)` for this path
- Scope: `target_uri` as above; no `score_threshold` or metadata `filter` in the current implementation

#### 4) Fallback when OpenViking is unavailable

If OpenViking is disabled or search fails:

- Fallback source: SQLite `document_chunks`
- Fallback method: `get_chunks_for_document(doc_id, limit=5)`
- Fallback output: `source = "document"`, `score = 1.0`; `uri` empty
- Last error is exposed as `openviking_error` in the chat response

#### 5) Tuning

- Increase `FILE_SEARCH_TOP_N` to 8–10 for broader context (higher token cost); reduce to 3 for faster/cheaper replies
- Add `score_threshold` if results are noisy
- Use `find(...)` only if you explicitly want non–session-aware search

## OpenViking Paradigm Adoption Status

This system uses the OpenViking filesystem paradigm in the production path:

1. **Filesystem management** — Resources are organized under `viking://resources/users/{user_id}/documents/{doc_id}`.
2. **Tiered context (L0/L1/L2)** — File search uses L1/L0 (`overview`/`abstract`) for prompt injection; L2 can be added on demand later.
3. **Directory recursive retrieval** — Default search scope is user root; OpenViking searches within that tree.
4. **Search trajectory** — Chat supports `debug_search_trace`; response can include `search_trace`.
5. **Session management** — Conversation uses OpenViking session APIs and auto-commit threshold (`openviking_auto_commit_turns`).

## Fallback Strategy

If OpenViking fails (config/port/model/network), chat still responds:

- Context comes from SQLite document chunks (`get_chunks_for_document`) when applicable
- Response includes `openviking_error` for observability

Applies to both:

- `POST /api/ai/chat`
- `POST /api/ai/chat/stream` (error in `context` / `done` event payload)

## Chat Response Contract

`POST /api/ai/chat` returns:

- `message`
- `context` (file search results + metadata)
- `mood`
- `session_id`
- `openviking_error` (optional)
- `search_trace` (optional, when `debug_search_trace=true`)

`POST /api/ai/chat/stream` events:

- `context` (contains `context`, `session_id`, optional `openviking_error`, optional `search_trace`)
- `token` (contains `token`, `session_id`)
- `mood`
- `done` (contains `message`, `session_id`, optional `openviking_error`)

Request body for chat:

- `debug_search_trace`: if true, include `search_trace` in the response (target_uri, result_count, optional query_plan/query_results).

## Session APIs

- `GET /api/sessions` — list sessions from SQLite
- `GET /api/sessions/{session_id}` — session metadata + messages
- `POST /api/sessions/{session_id}/commit` — commit OpenViking session and set SQLite `committed_at`

## Frontend Integration

Frontend tracks `sessionId` in Zustand (`frontend/src/state/appStore.ts`). Chat API calls pass `session_id` (`frontend/src/lib/endpoints.ts`). `ChatPage` updates `sessionId` from the backend and provides a "New Chat" action (`frontend/src/components/features/chat/ChatPage.tsx`).

## Quick Verification

### Verify OpenViking file search

```bash
cd backend
uv run python -c "from app.db.openviking_client import get_openviking_client, close_openviking_client; c=get_openviking_client(); print(c.find('test query', limit=1)); close_openviking_client()"
```

### Verify chat and session

```bash
cd backend
uv run python -c "from app.api.chat import chat, ChatBody; out=chat(ChatBody(message='hello', history=[], doc_id=None, session_id=None)); print(out.get('session_id'), out.get('openviking_error'))"
```

### Verify session APIs

```bash
cd backend
uv run python -c "from app.api.sessions import list_sessions; print(list_sessions(20))"
```

## Notes

- If the embedding model is not activated in Ark, file search may fail and fallback will be used.
- If the AGFS port is in use, OpenViking startup can fail; keep `openviking_agfs_port` aligned with your environment.
- Document indexing is asynchronous (`wait=False`) on upload for lower latency.
