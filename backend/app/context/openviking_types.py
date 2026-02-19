"""OpenViking session/message types with graceful fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

try:
    from openviking.message import ContextPart, Part, TextPart, ToolPart  # type: ignore
except Exception:
    @dataclass(slots=True)
    class TextPart:
        text: str

    @dataclass(slots=True)
    class ContextPart:
        uri: str
        abstract: str | None = None
        context_type: str = "memory"

    @dataclass(slots=True)
    class ToolPart:
        tool_name: str
        tool_input: dict[str, Any] | None = None
        tool_output: Any | None = None
        skill_uri: str = ""

    Part = TextPart | ContextPart | ToolPart


class SessionLike(Protocol):
    """Minimal session API we rely on from OpenViking."""

    session_id: str
    messages: list[Any]

    def add_message(self, role: str, parts: list[Part]) -> Any:
        ...

    def used(
        self,
        contexts: list[str] | None = None,
        skill: dict[str, Any] | None = None,
    ) -> None:
        ...

    def commit(self) -> dict[str, Any]:
        ...

    def load(self) -> None:
        ...


@dataclass(slots=True)
class MemoryFallbackSession:
    """In-process fallback when OpenViking client is unavailable."""

    session_id: str
    user_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    used_contexts: list[str] = field(default_factory=list)
    used_skills: list[dict[str, Any]] = field(default_factory=list)
    committed: bool = False
    committed_at: datetime | None = None

    def add_message(self, role: str, parts: list[Part]) -> dict[str, Any]:
        msg = {
            "id": f"msg_{uuid4().hex}",
            "role": role,
            "parts": list(parts),
            "created_at": datetime.now(tz=timezone.utc),
        }
        self.messages.append(msg)
        return msg

    def used(
        self,
        contexts: list[str] | None = None,
        skill: dict[str, Any] | None = None,
    ) -> None:
        if contexts:
            for uri in contexts:
                if uri and uri not in self.used_contexts:
                    self.used_contexts.append(uri)
        if skill:
            self.used_skills.append(dict(skill))

    def commit(self) -> dict[str, Any]:
        self.committed = True
        self.committed_at = datetime.now(tz=timezone.utc)
        return {
            "session_id": self.session_id,
            "status": "committed",
            "memories_extracted": 0,
            "active_count_updated": len(self.used_contexts),
            "archived": bool(self.messages),
        }

    def load(self) -> None:
        return None
