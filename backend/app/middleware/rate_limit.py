from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self.limit = settings.ai_rate_limit_per_min
        self.window = timedelta(minutes=1)
        self.hits: dict[str, deque[datetime]] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/ai"):
            now = datetime.now(UTC)
            client_ip = request.client.host if request.client else "unknown"
            key = f"{client_ip}:{request.url.path}"

            events = self.hits[key]
            while events and now - events[0] > self.window:
                events.popleft()

            if len(events) >= self.limit:
                return self._limit_response(request)

            events.append(now)

        return await call_next(request)

    def _limit_response(self, request):
        request_id = getattr(request.state, "request_id", "unknown")
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={
                "code": "rate_limited",
                "message": "AI rate limit exceeded. Try again later.",
                "details": None,
                "request_id": request_id,
            },
        )
