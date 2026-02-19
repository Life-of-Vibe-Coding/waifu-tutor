# Waifu Tutor Runbook

## Local Development (recommended)

1. Copy backend env: `cp backend/.env.example backend/.env`
2. From frontend: `cd frontend && npm install && npm run dev:all` (starts backend on 8000 and frontend on 5173)
3. Open **http://localhost:5173**

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
- `OPENVIKING_CONFIG_FILE`: optional; path to OpenViking config (embedding + VLM). **Default: project root `.openviking/ov.conf`**.
- `OPENVIKING_DATA_DIR`: optional; OpenViking context DB path. Default: `db/data/openviking` (under project root).
- `UPLOAD_DIR`, `MAX_UPLOAD_BYTES`: upload path and size limit.
- `VOLCENGINE_API_KEY`, `CHAT_MODEL`: Volcengine ARK (e.g. Doubao-Seed-1.8) for chat.

## OpenViking (context DB)
- Backend uses **uv** for deps; OpenViking is installed via `uv sync` (see `backend/pyproject.toml`).
- **Config**: By default the app uses **`.openviking/ov.conf`** at the project root (embedding + VLM). Override with `OPENVIKING_CONFIG_FILE`.
- **Data**: Stored under `db/data/openviking` (override with `OPENVIKING_DATA_DIR`). Uploaded documents are indexed into OpenViking and `openviking_uri` is saved on the document.
- Helpers: `app.db.openviking_client.get_openviking_path()`, `get_openviking_client()`, `index_document()`. See [OpenViking docs](https://github.com/volcengine/openviking).

## Live2D Character Runtime
- Build Cubism Web sample and copy output into `frontend/public/live2d-demo/`.
- See `backend/docs/live2d_setup.md` if present.

## Troubleshooting
- If upload fails for PDF/DOCX, ensure backend has `pypdf` and `python-docx` (in `backend/pyproject.toml`).
- If chat returns fallback text, set `VOLCENGINE_API_KEY` in backend `.env`.
- Notes / Gmail / courses / organize return 501 until those endpoints are implemented in the Python backend.
