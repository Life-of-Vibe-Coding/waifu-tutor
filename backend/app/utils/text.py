from datetime import UTC, datetime
import json
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def event_payload(data: dict) -> str:
    payload = {
        "event_id": str(uuid4()),
        "timestamp": utcnow().isoformat(),
        "data": data,
    }
    return json.dumps(payload, ensure_ascii=False)
