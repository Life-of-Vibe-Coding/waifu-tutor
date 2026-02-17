# Waifu Tutor

Full-stack learning companion (Next.js + SQLite, no Qdrant).

## Stack
- **Next.js 14** (App Router) – frontend + API routes
- **SQLite** (better-sqlite3) – relational data, FTS5 keyword search, in-DB vector storage for semantic search
- **Gemini** (optional) – summarization, flashcards, chat, embeddings

## Quick start

```bash
cp .env.example .env
# Optional: set GEMINI_API_KEY in .env for AI features
pnpm install
pnpm dev
```

Open **http://localhost:3000**.

## Project layout
- `app/` – Next.js pages and API routes
- `components/` – React UI (chat, Live2D stage, companion HUD)
- `lib/` – DB, AI (Gemini), search (FTS + SQLite vectors), document parsing
- `state/` – Zustand store
- `types/` – shared TypeScript types
- `public/` – static assets (e.g. Live2D demo under `public/live2d-demo/`)

## Data
- SQLite file: `data/waifu_tutor.db` (created on first run)
- Uploads: `data/uploads/`
- No Qdrant or external vector DB; embeddings are stored in SQLite and similarity is computed in-process.

## Live2D
- Copy Cubism Web sample build output into `public/live2d-demo/` (see `docs/live2d_setup.md` if present).
- If the demo is missing, the app shows a fallback character.
