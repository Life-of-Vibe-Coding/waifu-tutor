# Waifu Tutor

Full-stack learning companion: **React (Vite)** frontend + **Python 3.12 (FastAPI)** backend, SQLite.

## Stack

### Frontend
| | |
|---|---|
| Framework | React 18 + Vite 5 |
| Routing | React Router 6 |
| State | Zustand 5 |
| Data Fetching | TanStack React Query 5 |
| HTTP | Axios |
| Styling | Tailwind CSS 3 + Framer Motion |
| Language | TypeScript 5 |
| Testing | Vitest |

### Backend
| | |
|---|---|
| Runtime | Python 3.12 |
| Framework | FastAPI + Uvicorn |
| Database | SQLite (FTS5, async via aiosqlite) |
| Document Parsing | pypdf, python-docx |
| Package Manager | uv |

### AI
| | |
|---|---|
| Chat | Gemini or Qwen (DashScope) / Doubao-Seed (VolcEngine) |
| Config | `backend/.env` (see `backend/.env.example`) |

## Quick start

```bash
# 1. Backend env
cp backend/.env.example backend/.env
# Optional: set VOLCENGINE_API_KEY in backend/.env for chat (Doubao-Seed-1.8)

# 2. Run both backend and frontend (from frontend/)
cd frontend && npm install && npm run dev:all
```

Or run separately: `cd frontend && npm run dev` (frontend only) or `cd backend && uv sync && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (backend only).

- **Frontend**: http://localhost:5173 (Vite dev server; proxies /api and /health to backend)
- **Backend**: defaults to http://localhost:8000 (FastAPI)

`npm run dev:all` now auto-handles port conflicts:
- Reuses existing Waifu backend on `8000` if available
- If `8000` is occupied by another service, starts backend on another free port and injects `VITE_API_BASE_URL` automatically for frontend chat/API calls

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env` if not using the Vite proxy (e.g. production build).

## Project layout
- `frontend/` – Vite + React app (chat, notes UI, companion HUD)
- `backend/` – FastAPI app (auth, documents, chat), scripts, infra, docs
- `db/` – database data, schema, shared types

## Data
- SQLite: `db/data/waifu_tutor.db`
- Uploads: `db/data/uploads/`

## Environment
- Backend: `backend/.env` (copy from `backend/.env.example`)
- Frontend: `frontend/.env` – optional `VITE_API_BASE_URL` for API base URL

## Live2D
- Copy Cubism Web sample build into `frontend/public/live2d-demo/`. If missing, the app shows a fallback character.

## Scripts & infra
- `backend/scripts/` – bootstrap, dev, smoke tests
- `backend/infra/` – docker-compose
