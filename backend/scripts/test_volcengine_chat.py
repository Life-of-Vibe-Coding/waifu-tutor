"""One-off test: call Volcengine chat with current .env and print result."""
from __future__ import annotations

import sys
from pathlib import Path

# backend/ must be on path for app imports
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

from app.core.config import get_settings
from app.services.ai import _volcengine_complete

def main() -> None:
    s = get_settings()
    print("VOLCENGINE_API_KEY loaded:", bool(s.volcengine_api_key))
    print("VOLCENGINE_CHAT_BASE:", s.volcengine_chat_base)
    print("CHAT_MODEL:", s.chat_model)
    print()

    messages = [
        {"role": "user", "content": "Reply with exactly: OK"},
    ]
    out = _volcengine_complete(messages)
    if out:
        print("SUCCESS. Reply:", repr(out[:200]))
    else:
        print("FAILED (fallback would be used). Check logs above or backend logs for reason.")


if __name__ == "__main__":
    main()
