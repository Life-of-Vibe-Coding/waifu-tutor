# API Notes

## Base URL
- `http://localhost:8000`

## Key Endpoints
- Auth: `/api/auth/register`, `/api/auth/login`
- Profile: `/api/user/profile`
- Documents: `/api/documents/upload`, `/api/documents/list`, `/api/documents/{doc_id}`
- AI: `/api/ai/summarize`, `/api/ai/generate-flashcards`, `/api/ai/chat`, `/api/ai/chat/stream`, `/api/ai/quiz-feedback`
- Flashcards: `/api/flashcards/{doc_id}`, `/api/flashcards/{card_id}/review`
- Study: `/api/study/progress`
- Reminders: `/api/reminders/create`, `/api/reminders/list`, `/api/reminders/{reminder_id}`

## SSE Stream Contract
`POST /api/ai/chat/stream`

Event types emitted:
- `context`
- `token`
- `mood`
- `done`

Each `data` payload includes:
- `event_id`
- `timestamp`
- `data`
