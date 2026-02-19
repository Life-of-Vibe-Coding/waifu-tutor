# Waifu Tutor Runbook

## Local Development (recommended)

1. Copy backend env: `cp backend/.env.example backend/.env`
2. **Option A – from project root:** `npm run dev` starts backend (8000) and frontend (5173).
3. **Option B – from frontend:** `cd frontend && npm install && npm run dev:all` (starts backend on 8000 and frontend on 5173).
4. Open **http://localhost:5173**

## Local Development (separate terminals)

### Backend
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. The Vite dev server proxies `/api` and `/health` to `http://localhost:8000`.

## Environment Variables
- `DATABASE_URL`: defaults to `sqlite:///../db/data/waifu_tutor.db` (relative to backend cwd).
- `UPLOAD_DIR`, `MAX_UPLOAD_BYTES`: upload path and size limit.
- `VOLCENGINE_API_KEY`, `CHAT_MODEL`: Volcengine ARK (e.g. Doubao-Seed-1.8) for chat.

## Live2D Character Runtime
- Build Cubism Web sample and copy output into `frontend/public/live2d-demo/`.
- See `backend/docs/live2d_setup.md` if present.

## Troubleshooting
- If upload fails for PDF/DOCX, ensure backend has `pypdf` and `python-docx` (in `backend/pyproject.toml`).
- If chat returns fallback text, set `VOLCENGINE_API_KEY` in backend `.env`.
- Notes / Gmail / courses / organize return 501 until those endpoints are implemented in the Python backend.
