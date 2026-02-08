# Waifu Tutor

Full-stack phase-1 implementation based on `waifu_tutor_architecture.md`.

## Stack
- Frontend: React + Vite + TypeScript + Tailwind + React Query + Zustand
- Backend: FastAPI + SQLAlchemy + SQLite + Qdrant + Gemini adapter
- Runtime: Docker Compose (`infra/docker-compose.yml`)

## Quick start

```bash
cp .env.example .env
./scripts/dev.sh
```

Frontend: `http://localhost:5173`
Backend: `http://localhost:8000`
Qdrant: `http://localhost:6333`

## Demo mode
- `DEMO_MODE=true` by default
- Auth endpoints are preserved but return demo-user contracts

## Live2D setup
- This app is wired to use the official Cubism Web sample build output.
- Follow: https://docs.live2d.com/en/cubism-sdk-tutorials/sample-build-web/
- Copy sample `dist` output into: `frontend/public/live2d-demo/`
- See detailed steps: `docs/live2d_setup.md`

See `docs/runbook.md` for more details.
