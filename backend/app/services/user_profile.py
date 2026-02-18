"""User profile (name, age, hobbies) for viking L0 user memory (viking://user/profile)."""
from __future__ import annotations

import re
from pathlib import Path

from app.db.openviking_client import get_openviking_path


def _user_profile_path() -> Path:
    return get_openviking_path() / "viking" / "user" / "profile.md"


def read_user_profile() -> str | None:
    """Read viking user profile content if it exists."""
    path = _user_profile_path()
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def is_first_time_user() -> bool:
    """True if we have no user profile (first-ever chat)."""
    content = read_user_profile()
    if not content:
        return True
    # Consider first-time if profile doesn't contain a name line (not yet filled by onboarding)
    if "name:" in content.lower() or "name =" in content.lower():
        return False
    return True


def write_user_profile(name: str, age: str, hobbies: str) -> None:
    """Write student name, age, and hobbies to viking user profile (L0 memory)."""
    path = _user_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    name = (name or "").strip() or "—"
    age = (age or "").strip() or "—"
    hobbies = (hobbies or "").strip() or "—"
    content = f"""# Student profile

- **name:** {name}
- **age:** {age}
- **hobbies:** {hobbies}
"""
    path.write_text(content, encoding="utf-8")


# Pattern for model output: PROFILE:name=...|age=...|hobbies=...
_PROFILE_LINE_RE = re.compile(
    r"PROFILE\s*:\s*name\s*=\s*([^|]+)\s*\|\s*age\s*=\s*([^|]+)\s*\|\s*hobbies\s*=\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def parse_profile_line(text: str) -> tuple[str, str, str] | None:
    """If text contains a PROFILE:name=X|age=Y|hobbies=Z line, return (name, age, hobbies); else None."""
    for line in (text or "").splitlines():
        line = line.strip()
        m = _PROFILE_LINE_RE.search(line)
        if m:
            return (
                (m.group(1) or "").strip(),
                (m.group(2) or "").strip(),
                (m.group(3) or "").strip(),
            )
    return None


def strip_profile_line(text: str) -> str:
    """Remove the PROFILE:... line from text (one line only)."""
    if "PROFILE:" not in text:
        return text
    lines = text.splitlines()
    out = []
    for line in lines:
        if _PROFILE_LINE_RE.search(line.strip()):
            continue
        out.append(line)
    return "\n".join(out).strip()
