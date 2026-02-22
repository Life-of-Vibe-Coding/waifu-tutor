"""Lightweight Agno-backed agent accessors (no custom harness)."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.hitl import set_pending
from app.skills import build_skill_registry, get_skill_registry
from app.tool.tools import CHAT_TOOLS, execute_tool

logger = logging.getLogger(__name__)

_default_agent: _SimpleAgent | None = None
_default_agent_lock = threading.Lock()


@dataclass(slots=True)
class AgentRunResult:
    """Typed result for one agent run."""
    text: str | None
    used_fallback: bool
    reminder_payload: dict[str, Any] | None = None
    hitl_payload: dict[str, Any] | None = None
    error: str | None = None


@dataclass(slots=True)
class _ToolRuntimeContext:
    """Per-run dynamic data needed by tool entrypoints."""
    session_id: str
    user_id: str
    user_timezone: str | None
    loop_context: dict[str, Any]


class _SimpleAgent:
    """Minimal wrapper that builds an Agno Agent with project tools and skills."""

    @staticmethod
    def _normalize_role(role: str | None) -> str:
        """Map roles to provider-compatible values."""
        r = str(role or "").strip().lower()
        if r in ("system", "assistant", "user", "tool"):
            return r
        if r == "developer":
            return "system"
        return "user"

    def __init__(self) -> None:
        from agno.agent import Agent
        from agno.models.openai import OpenAIResponses

        settings = get_settings()
        build_skill_registry(settings.skills_dir)
        self._agno_skills = self._build_agno_skills(str(settings.skills_dir))
        self._last_trace: list[str] = []
        self._last_reasoning: list[str] = []
        self._run_lock = threading.Lock()
        self._runtime_context: _ToolRuntimeContext | None = None
        self._agno_tools = self._build_agno_tools()
        self._agno_db = self._build_agno_db()
        self._agent = Agent(
            model=OpenAIResponses(
                id=settings.chat_model,
                api_key=settings.volcengine_api_key or "sk-fallback",
                base_url=settings.volcengine_chat_base.rstrip("/"),
            ),
            tools=self._agno_tools,
            skills=self._agno_skills,
            db=self._agno_db,
            add_history_to_context=True,
            num_history_runs=12,
        )

    def _build_agno_skills(self, skills_dir: str) -> Any | None:
        """Build native Agno skills from configured skills directory."""
        try:
            from agno.skills import LocalSkills, Skills

            return Skills(loaders=[LocalSkills(path=skills_dir, validate=False)])
        except Exception:
            logger.exception("Failed to initialize Agno skills from %s", skills_dir)
            return None

    def _build_agno_db(self) -> Any | None:
        """Build Agno DB for session conversation memory."""
        settings = get_settings()
        try:
            from agno.db.sqlite import SqliteDb

            db_path = settings.sqlite_path()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return SqliteDb(db_file=str(db_path))
        except Exception as exc:
            logger.warning("Agno SqliteDb unavailable (%s); using InMemoryDb for session history.", exc)
            try:
                from agno.db.in_memory import InMemoryDb

                return InMemoryDb()
            except Exception:
                logger.exception("Failed to initialize Agno DB")
                return None

    def _execute_tool(self, tool_name: str, kwargs: dict[str, Any]) -> str:
        """Execute a configured chat tool within current runtime context."""
        runtime_context = self._runtime_context
        if runtime_context is None:
            logger.error("Tool %s called without runtime context", tool_name)
            return "Tool runtime context is unavailable."
        side_effects = runtime_context.loop_context.setdefault("side_effects", {})
        try:
            res_str, reminder_payload, _ = execute_tool(
                tool_name,
                json.dumps(kwargs),
                runtime_context.session_id,
                runtime_context.user_id,
                runtime_context.user_timezone,
                runtime_context.loop_context,
            )
        except Exception:
            logger.exception("Tool execution failed: %s", tool_name)
            return "Tool execution failed."
        if reminder_payload is not None:
            side_effects["reminder_payload"] = reminder_payload
        return res_str

    def _build_agno_tools(self) -> list[Any]:
        from agno.tools import Function

        funcs: list[Any] = []
        for t in CHAT_TOOLS:
            fn = t.get("function", {})
            name = fn.get("name", "")
            desc = fn.get("description", "")
            params = fn.get("parameters")
            if not name:
                continue

            def _make_entrypoint(tool_name: str):
                def _entrypoint(**kwargs):
                    return self._execute_tool(tool_name, kwargs)

                return _entrypoint

            funcs.append(Function(
                name=name,
                description=desc,
                parameters=params,
                entrypoint=_make_entrypoint(name),
                # Some OpenAI-compatible providers reject non-standard tool schema fields
                # such as `requires_confirmation`; keep tool schema minimal for compatibility.
            ))
        return funcs

    def _build_trace_from_messages(self, messages: list[Any]) -> list[str]:
        """Build a concise execution trace from Agno messages."""
        trace: list[str] = []
        for m in messages or []:
            tool_calls = getattr(m, "tool_calls", None) or []
            for tc in tool_calls:
                fn = tc.get("function") if isinstance(tc, dict) else {}
                fn_name = (fn or {}).get("name", "")
                fn_args = (fn or {}).get("arguments", "")
                if fn_name:
                    trace.append(f"tool_call: {fn_name}({fn_args})")
            if getattr(m, "role", None) == "tool":
                tool_name = getattr(m, "tool_name", None) or getattr(m, "name", None) or "tool"
                content = str(getattr(m, "content", "") or "").strip()
                if len(content) > 220:
                    content = content[:220] + "..."
                trace.append(f"tool_result: {tool_name} => {content}")
        return trace

    def _sync_messages_from_run(self, messages: list[dict[str, Any]], run_messages: list[Any]) -> None:
        """Replace caller messages with full Agno conversation for pause/resume loops."""
        out: list[dict[str, Any]] = []
        for m in run_messages or []:
            item: dict[str, Any] = {"role": self._normalize_role(getattr(m, "role", "assistant"))}
            content = getattr(m, "content", None)
            if content is not None:
                item["content"] = content
            tool_calls = getattr(m, "tool_calls", None)
            if tool_calls:
                item["tool_calls"] = tool_calls
            tool_call_id = getattr(m, "tool_call_id", None)
            if tool_call_id:
                item["tool_call_id"] = tool_call_id
            tool_name = getattr(m, "tool_name", None)
            if tool_name:
                item["tool_name"] = tool_name
            out.append(item)
        if out:
            messages[:] = out

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

    def get_last_trace(self) -> list[str]:
        """Return trace lines from the latest run."""
        return list(self._last_trace)

    def get_last_reasoning(self) -> list[str]:
        """Return reasoning summary lines from the latest run (if available)."""
        return list(self._last_reasoning)

    def _build_reasoning_summary(self, run_output: Any) -> list[str]:
        """Build a concise reasoning summary from Agno run output."""
        out: list[str] = []
        reasoning_content = str(getattr(run_output, "reasoning_content", "") or "").strip()
        if reasoning_content:
            for line in reasoning_content.splitlines():
                ln = line.strip()
                if not ln:
                    continue
                if len(ln) > 220:
                    ln = ln[:220] + "..."
                out.append(ln)
                if len(out) >= 8:
                    break
        if out:
            return out
        reasoning_steps = list(getattr(run_output, "reasoning_steps", None) or [])
        for step in reasoning_steps[:6]:
            text = str(step).strip()
            if not text:
                continue
            if len(text) > 220:
                text = text[:220] + "..."
            out.append(text)
        return out

    def _build_hitl_payload(
        self,
        run_output: Any,
        requirements: list[Any],
        session_id: str,
        user_id: str,
        user_timezone: str | None,
    ) -> dict[str, Any] | None:
        if not requirements:
            return None
        run_id = str(getattr(run_output, "run_id", "") or "")
        if not run_id:
            logger.warning("Paused run without run_id; cannot build checkpoint")
            return None
        req_dicts = [r.to_dict() for r in requirements]
        checkpoint_id = set_pending(
            session_id=session_id,
            user_id=user_id,
            run_id=run_id,
            requirements=req_dicts,
            user_timezone=user_timezone,
        )
        first = requirements[0]
        tool_exec = getattr(first, "tool_execution", None)
        tool_name = getattr(tool_exec, "tool_name", "") if tool_exec else ""
        tool_args = getattr(tool_exec, "tool_args", {}) if tool_exec else {}
        summary = f"Approve tool call: {tool_name}" if tool_name else "Approval required before proceeding."
        options: list[str] = []
        feedback_schema = getattr(first, "user_feedback_schema", None) or []
        if feedback_schema and hasattr(feedback_schema[0], "options"):
            options = [str(opt.label) for opt in (feedback_schema[0].options or []) if getattr(opt, "label", None)]
        return {
            "type": "human_approval",
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "checkpoint": str(getattr(first, "id", checkpoint_id)),
            "summary": summary,
            "params": tool_args or {},
            "options": options,
            "allow_free_input": True,
        }

    def _run_with_context(
        self,
        *,
        session_id: str,
        user_id: str,
        user_timezone: str | None,
        loop_context: dict[str, Any],
        invoke: Any,
    ) -> Any:
        with self._run_lock:
            self._runtime_context = _ToolRuntimeContext(
                session_id=session_id,
                user_id=user_id,
                user_timezone=user_timezone,
                loop_context=loop_context,
            )
            try:
                return invoke()
            finally:
                self._runtime_context = None

    def run(
        self,
        messages: list[dict[str, Any]],
        session_id: str,
        user_id: str,
        user_timezone: str | None = None,
    ) -> AgentRunResult:
        from agno.models.message import Message

        loop_context = {"round_index": 1, "max_rounds": 1}
        agno_msgs = []
        for m in messages:
            kwargs: dict[str, Any] = {"role": self._normalize_role(m.get("role")), "content": m.get("content")}
            if m.get("tool_calls") is not None:
                kwargs["tool_calls"] = m.get("tool_calls")
            if m.get("tool_call_id") is not None:
                kwargs["tool_call_id"] = m.get("tool_call_id")
            if m.get("tool_name") is not None:
                kwargs["tool_name"] = m.get("tool_name")
            agno_msgs.append(Message(**kwargs))
        res = None
        try:
            res = self._run_with_context(
                session_id=session_id,
                user_id=user_id,
                user_timezone=user_timezone,
                loop_context=loop_context,
                invoke=lambda: self._agent.run(
                    agno_msgs,
                    session_id=session_id,
                    user_id=user_id,
                ),
            )
        except Exception as exc:
            logger.exception("Agno agent.run failed")
            self._last_reasoning = []
            return AgentRunResult(
                text=None,
                used_fallback=True,
                error=str(exc),
            )
        self._last_trace = self._build_trace_from_messages(getattr(res, "messages", None) or [])
        self._last_reasoning = self._build_reasoning_summary(res)
        if res and getattr(res, "messages", None):
            self._sync_messages_from_run(messages, res.messages)
        side_effects = loop_context.get("side_effects") or {}
        if bool(getattr(res, "is_paused", False)):
            requirements = list(getattr(res, "active_requirements", None) or [])
            hitl_payload = self._build_hitl_payload(
                run_output=res,
                requirements=requirements,
                session_id=session_id,
                user_id=user_id,
                user_timezone=user_timezone,
            )
            if hitl_payload is None:
                return AgentRunResult(
                    text=None,
                    used_fallback=True,
                    reminder_payload=side_effects.get("reminder_payload"),
                    hitl_payload=None,
                    error="Paused run missing checkpoint metadata.",
                )
            return AgentRunResult(
                text=None,
                used_fallback=False,
                reminder_payload=side_effects.get("reminder_payload"),
                hitl_payload=hitl_payload,
            )
        if res and getattr(res, "messages", None):
            msgs_all = res.messages
            if msgs_all and msgs_all[-1].role == "assistant" and not getattr(msgs_all[-1], "tool_calls", None):
                return AgentRunResult(
                    text=msgs_all[-1].content or "",
                    used_fallback=False,
                    reminder_payload=side_effects.get("reminder_payload"),
                    hitl_payload=None,
                )
        return AgentRunResult(
            text=None,
            used_fallback=True,
            reminder_payload=None,
            hitl_payload=None,
        )

    def continue_run(
        self,
        *,
        run_id: str,
        requirements: list[Any],
        session_id: str,
        user_id: str,
        user_timezone: str | None = None,
    ) -> AgentRunResult:
        loop_context = {"round_index": 1, "max_rounds": 1}
        try:
            res = self._run_with_context(
                session_id=session_id,
                user_id=user_id,
                user_timezone=user_timezone,
                loop_context=loop_context,
                invoke=lambda: self._agent.continue_run(
                    run_id=run_id,
                    requirements=requirements,
                    session_id=session_id,
                    user_id=user_id,
                ),
            )
        except Exception as exc:
            logger.exception("Agno agent.continue_run failed")
            self._last_reasoning = []
            return AgentRunResult(text=None, used_fallback=True, error=str(exc))
        self._last_trace = self._build_trace_from_messages(getattr(res, "messages", None) or [])
        self._last_reasoning = self._build_reasoning_summary(res)
        side_effects = loop_context.get("side_effects") or {}
        if bool(getattr(res, "is_paused", False)):
            hitl_payload = self._build_hitl_payload(
                run_output=res,
                requirements=list(getattr(res, "active_requirements", None) or []),
                session_id=session_id,
                user_id=user_id,
                user_timezone=user_timezone,
            )
            if hitl_payload is None:
                return AgentRunResult(
                    text=None,
                    used_fallback=True,
                    reminder_payload=side_effects.get("reminder_payload"),
                    hitl_payload=None,
                    error="Paused continuation missing checkpoint metadata.",
                )
            return AgentRunResult(
                text=None,
                used_fallback=False,
                reminder_payload=side_effects.get("reminder_payload"),
                hitl_payload=hitl_payload,
            )
        if res and getattr(res, "messages", None):
            msgs_all = res.messages
            if msgs_all and msgs_all[-1].role == "assistant" and not getattr(msgs_all[-1], "tool_calls", None):
                return AgentRunResult(
                    text=msgs_all[-1].content or "",
                    used_fallback=False,
                    reminder_payload=side_effects.get("reminder_payload"),
                    hitl_payload=None,
                )
        content = getattr(res, "content", None)
        if isinstance(content, str) and content.strip():
            return AgentRunResult(
                text=content,
                used_fallback=False,
                reminder_payload=side_effects.get("reminder_payload"),
                hitl_payload=None,
            )
        return AgentRunResult(text=None, used_fallback=True, reminder_payload=None, hitl_payload=None)


def get_default_agent() -> _SimpleAgent:
    global _default_agent
    if _default_agent is not None:
        return _default_agent
    with _default_agent_lock:
        if _default_agent is None:
            _default_agent = _SimpleAgent()
    return _default_agent


def set_default_agent(agent: _SimpleAgent | None) -> None:
    global _default_agent
    with _default_agent_lock:
        _default_agent = agent


__all__ = [
    "AgentRunResult",
    "get_default_agent",
    "set_default_agent",
]
