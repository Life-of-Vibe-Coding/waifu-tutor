# Waifu Tutor Runbook

## Local Development (Docker Compose)
1. Copy environment template: `cp .env.example .env`
2. Start stack: `./scripts/dev.sh`
3. Open frontend at `http://localhost:5173`
4. Use Upload page to ingest a document.

## Local Development (Without Docker)
### Backend
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
pnpm install
pnpm --filter @waifu-tutor/frontend dev
```

## Environment Variables
- `GEMINI_API_KEY`: optional. If missing, deterministic fallback provider is used.
- `QDRANT_URL`: defaults to `http://localhost:6333`
- `DATABASE_URL`: defaults to `sqlite:///./data/waifu_tutor.db`

## Live2D Character Runtime
- Build Cubism Web sample from the official tutorial:
  - https://docs.live2d.com/en/cubism-sdk-tutorials/sample-build-web/
- Copy built sample `dist` files into:
  - `frontend/public/live2d-demo/`
- The app will auto-load `frontend/public/live2d-demo/index.html` in the character panel.
- Full integration note:
  - `docs/live2d_setup.md`

## Troubleshooting
- If upload fails for PDF/DOCX, ensure parser dependencies are installed.
- If vector search returns empty, verify Qdrant is running and collection dimension matches `EMBEDDING_DIM`.
- Browser notification reminders require notification permission in the UI.
