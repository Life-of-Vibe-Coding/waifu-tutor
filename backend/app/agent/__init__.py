"""Lightweight Agno-backed agent accessors (no custom harness)."""
from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.tool.tools import CHAT_TOOLS, execute_tool
from app.skills import build_skill_registry, get_skill_registry

_default_agent: _SimpleAgent | None = None


class _SimpleAgent:
    """Minimal wrapper that builds an Agno Agent with project tools and skills."""

    def __init__(self) -> None:
        settings = get_settings()
        build_skill_registry(settings.skills_dir)
        self._agno_skills = self._build_agno_skills(str(settings.skills_dir))

    def _build_agno_skills(self, skills_dir: str) -> Any | None:
        """Build native Agno skills from configured skills directory."""
        try:
            from agno.skills import LocalSkills, Skills

            return Skills(loaders=[LocalSkills(path=skills_dir, validate=False)])
        except Exception:
            return None

    def _build_agno_tools(self, session_id: str, user_id: str, user_timezone: str | None, loop_context: dict[str, Any]) -> list[Any]:
        from agno.tools import Function
        import json

        funcs: list[Any] = []
        for t in CHAT_TOOLS:
            fn = t.get("function", {})
            name = fn.get("name", "")
            desc = fn.get("description", "")
            params = fn.get("parameters")
            if not name:
                continue

            def entrypoint(**kwargs):
                res_str, _, _ = execute_tool(name, json.dumps(kwargs), session_id, user_id, user_timezone, loop_context)
                return res_str

            funcs.append(Function(name=name, description=desc, parameters=params, entrypoint=entrypoint, stop_after_tool_call=False))
        return funcs

    def get_cached_tools(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for t in CHAT_TOOLS:
            fn = t.get("function", {})
            name = fn.get("name", "")
            desc = fn.get("description", "")
            if name:
                out.append({"name": name, "description": desc})
        return out

    def get_agent_context_text(self) -> str:
        tools = self.get_cached_tools()
        registry = get_skill_registry()
        parts: list[str] = []
        if tools:
            parts.append("Available tools:\n" + "\n".join([f"- {t['name']}: {t['description']}" for t in tools]))
        if registry:
            parts.append(
                "Available top-level skills (registered natively in Agno):\n"
                + "\n".join([f"- {s['name']}: {s['description']}" for s in registry])
            )
        return "\n\n".join(parts) if parts else ""

    def run(
        self,
        messages: list[dict[str, Any]],
        session_id: str,
        user_id: str,
        user_timezone: str | None = None,
    ) -> tuple[str | None, bool, dict[str, Any] | None, dict[str, Any] | None]:
        from agno.agent import Agent
        from agno.models.openai import OpenAIResponses
        from agno.models.message import Message

        settings = get_settings()
        loop_context = {"round_index": 1, "max_rounds": 1}
        funcs = self._build_agno_tools(session_id, user_id, user_timezone, loop_context)
        agent = Agent(
            model=OpenAIResponses(
                id=settings.chat_model,
                api_key=settings.volcengine_api_key or "sk-fallback",
                base_url=settings.volcengine_chat_base.rstrip("/"),
            ),
            tools=funcs,
            skills=self._agno_skills,
        )
        agno_msgs = [Message(role=m["role"], content=m.get("content")) for m in messages]
        try:
            res = agent.run(agno_msgs)
        except Exception:
            res = None
        if res and getattr(res, "messages", None):
            msgs_all = res.messages
            if msgs_all and msgs_all[-1].role == "assistant" and not getattr(msgs_all[-1], "tool_calls", None):
                return msgs_all[-1].content or "", False, None, None
        return None, True, None, None


def get_default_agent() -> _SimpleAgent:
    global _default_agent
    if _default_agent is None:
        _default_agent = _SimpleAgent()
    return _default_agent


def set_default_agent(agent: _SimpleAgent | None) -> None:
    global _default_agent
    _default_agent = agent


__all__ = [
    "get_default_agent",
    "set_default_agent",
]
