from datetime import UTC, datetime, timedelta
import base64
import json

from app.core.config import get_settings


# Demo token helper intentionally simple because phase-1 runs in hardcoded no-auth mode.
def issue_demo_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "exp": int((datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)).timestamp()),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    return f"demo.{encoded}.token"
