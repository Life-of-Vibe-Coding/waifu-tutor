"""Agent harness: skill registry, context building, and tool loop."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.config import AgentConfig
from app.services.ai import complete_with_tools
from app.tool import execute_tool
from app.skills import build_skill_registry, get_skill_registry
from app.context.session_store import record_openviking_session_usage
from app.hitl import set_pending
from app.core.chat_logging import log_chat_llm_round, log_chat_final_response

logger = logging.getLogger(__name__)

_LOOP_OBJECTIVE_MARKER = "[loop_main_objective]"
_SKILL_EXECUTION_MARKER = "[skill_execution_mode]"

_REFLECTION_AFTER_SUBSKILL = (
    "Reflect: You just completed a subskill. Is the main objective complete? "
    "If not, call the next subskill or tool (e.g. load_subskill for the next step). "
    "Do not return intermediate outputs (e.g. outline only, plan only) as the final response."
)


def create_agent(config: AgentConfig) -> AgentHarness:
    """Create an agent harness from config."""
    return AgentHarness(config)


class AgentHarness:
    """Agent harness: owns skill registry, context building, and tool loop."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        build_skill_registry(config.skills_root)

    def get_cached_tools(self) -> list[dict[str, str]]:
        """Return cached tool name/description list."""
        out = []
        for t in self.config.tools:
            fn = (t.get("function") or {}) if isinstance(t, dict) else {}
            name = fn.get("name", "")
            desc = fn.get("description", "")
            if name:
                out.append({"name": name, "description": desc})
        return out

    def get_agent_context_text(self) -> str:
        """Format tools and skill registry for system/user prompt injection."""
        tools = self.config.tools
        registry = get_skill_registry()
        parts = []
        if tools:
            tool_descs = []
            for t in tools:
                fn = (t.get("function") or {}) if isinstance(t, dict) else {}
                name = fn.get("name", "")
                desc = fn.get("description", "")
                if name:
                    tool_descs.append(f"- {name}: {desc}")
            if tool_descs:
                parts.append("Available tools:\n" + "\n".join(tool_descs))
        if registry:
            skill_lines = [f"- {s['name']}: {s['description']}" for s in registry]
            parts.append(
                "Available top-level skills (load with load_skill before executing):\n"
                + "\n".join(skill_lines)
            )
        if not parts:
            return ""
        return (
            "\n\n".join(parts)
            + "\n\nTo run a skill, call load_skill first. You will receive full instructions after loading."
        )

    def _is_in_skill_execution_mode(self, messages: list[dict[str, Any]]) -> bool:
        """Return True if messages indicate skill execution mode (subskill flow active)."""
        for m in messages or []:
            if m.get("role") == "system" and _SKILL_EXECUTION_MARKER in str(
                m.get("content") or ""
            ):
                return True
        return False

    def _inject_reflection_after_subskill(
        self, messages: list[dict[str, Any]], tool_name: str
    ) -> None:
        """After load_subskill in skill mode, append a reflection prompt to nudge continuation."""
        if tool_name != "load_subskill":
            return
        if not self._is_in_skill_execution_mode(messages):
            return
        messages.append({
            "role": "user",
            "content": _REFLECTION_AFTER_SUBSKILL,
        })

    def _tools_for_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return tools list; exclude load_skill when already in skill execution mode."""
        for m in messages or []:
            if m.get("role") == "system" and _SKILL_EXECUTION_MARKER in str(m.get("content") or ""):
                return [t for t in self.config.tools if (t.get("function") or {}).get("name") != "load_skill"]
        return self.config.tools

    def _extract_conversation_from_system(self, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Extract [user]/[assistant] pairs from 'Recent session messages' in system content."""
        pairs: list[dict[str, str]] = []
        for m in messages or []:
            if m.get("role") != "system":
                continue
            content = str(m.get("content") or "")
            marker = "Recent session messages:"
            if marker not in content:
                continue
            block = content.split(marker, 1)[1]
            # Stop at Instructions or next top-level section
            for sep in ("\n\nInstructions:", "\n\nContext:", "\nInstructions:"):
                if sep in block:
                    block = block.split(sep, 1)[0]
            block = block.strip()
            current_role: str | None = None
            current_lines: list[str] = []
            for line in block.split("\n"):
                if line.startswith("[user]"):
                    if current_role:
                        text = "\n".join(current_lines).strip()
                        if text:
                            pairs.append({"role": current_role, "content": text})
                    current_role = "user"
                    current_lines = [line[6:].lstrip()]
                elif line.startswith("[assistant]"):
                    if current_role:
                        text = "\n".join(current_lines).strip()
                        if text:
                            pairs.append({"role": current_role, "content": text})
                    current_role = "assistant"
                    current_lines = [line[10:].lstrip()]
                elif current_role:
                    current_lines.append(line)
            if current_role:
                text = "\n".join(current_lines).strip()
                if text:
                    pairs.append({"role": current_role, "content": text})
            break
        return pairs

    def _extract_tool_loop_conversation(
        self, messages: list[dict[str, Any]], exclude_load_skill: bool = True
    ) -> list[dict[str, str]]:
        """Extract user/assistant pairs from tool-loop messages since entering the loop."""
        pairs: list[dict[str, str]] = []
        skip_next_tool = False
        for m in messages or []:
            role = m.get("role")
            if role == "system":
                continue
            if role == "user":
                content = (m.get("content") or "").strip()
                if content:
                    pairs.append({"role": "user", "content": content})
            elif role == "assistant":
                tcs = m.get("tool_calls") or []
                if not tcs:
                    content = (m.get("content") or "").strip()
                    if content:
                        pairs.append({"role": "assistant", "content": content})
                else:
                    fn = (tcs[0].get("function") or {}) if tcs else {}
                    name = fn.get("name", "")
                    if exclude_load_skill and name == "load_skill":
                        pairs.append({
                            "role": "assistant",
                            "content": "(Loaded skill; continuing with skill execution.)",
                        })
                        skip_next_tool = True
                    else:
                        brief = f"(Called {name})"
                        pairs.append({"role": "assistant", "content": brief})
            elif role == "tool" and skip_next_tool:
                skip_next_tool = False
        return pairs

    def _extract_main_objective(self, messages: list[dict[str, Any]]) -> str:
        """Extract the latest user objective from the tool-loop messages."""
        for m in reversed(messages or []):
            if m.get("role") != "user":
                continue
            content = str(m.get("content") or "").strip()
            if not content:
                continue
            marker = "User question:\n"
            if marker in content:
                tail = content.split(marker, 1)[1]
                objective = tail.split("\n\n", 1)[0].strip()
                if objective:
                    return objective
            return content
        return ""

    def _last_substantive_objective(self, pairs: list[dict[str, str]]) -> str:
        """Return the last non-anaphoric user message for use as objective."""
        anaphoric = {"yes", "no", "ok", "okay", "continue", "sure", "go ahead", "approved"}
        for p in reversed(pairs or []):
            if p.get("role") != "user":
                continue
            content = (p.get("content") or "").strip().lower()
            if content and content not in anaphoric and len(content) > 3:
                return p.get("content", "").strip()
        for p in reversed(pairs or []):
            if p.get("role") == "user":
                return (p.get("content") or "").strip()
        return ""

    def _ensure_loop_objective_context(self, messages: list[dict[str, Any]]) -> None:
        """Pin one system instruction so tool-loop rounds stay aligned to one objective."""
        for m in messages:
            if m.get("role") == "system" and _LOOP_OBJECTIVE_MARKER in str(m.get("content") or ""):
                return
        objective = self._extract_main_objective(messages) or "Complete the latest user request."
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    f"{_LOOP_OBJECTIVE_MARKER}\n"
                    f"Main objective: {objective}\n"
                    "During tool/skill execution, keep outputs internal and continue until the final user-ready response is complete. "
                    "Do not return intermediate artifacts (e.g. only outline, only plan, only partial draft) unless the user explicitly asks for intermediate output only."
                ),
            },
        )

    def _extract_skill_content_from_load_skill_result(self, result: str) -> tuple[str, str] | None:
        """If result is a successful load_skill response, return (content, name)."""
        try:
            data = json.loads(result)
            if not isinstance(data, dict) or data.get("error"):
                return None
            content = data.get("content")
            name = data.get("name", "")
            if content and isinstance(content, str):
                return (content, name)
        except Exception:
            pass
        return None

    def _format_skill_execution_system(
        self, skill_content: str, skill_name: str, objective: str = ""
    ) -> str:
        """Build merged system prompt: loop objective + skill execution instructions."""
        obj = objective or "Complete the user request."
        skill_block = (
            f"Executing the following skill: {skill_name}\n"
            f"{skill_content}\n\n"
            "You MUST call load_subskill(path) when the skill directs you to a subskill before proceeding to the next step. "
            "Subskills are procedural guides (markdown instructions), NOT invokable tools. "
            "After load_subskill returns the subskill content, follow its Steps and produce the output yourself; do NOT try to call a tool by the subskill's name (e.g. outline-builder, paragraph-generator). "
            "Do not skip subskills or fabricate their outputs. "
            "Call request_human_approval before consequential actions or after significant outputs when the skill or situation warrants it.\n\n"
            "After each subskill or tool execution: reflect — is the main objective complete? If not, proceed to the next step (e.g. call the next subskill or tool). Do not return intermediate outputs (e.g. outline only, plan only) as the final response unless the user explicitly asked for that only."
        )
        return (
            f"{_SKILL_EXECUTION_MARKER}\n"
            f"Main objective: {obj}\n"
            "During tool/skill execution, keep outputs internal and continue until the final user-ready response is complete. "
            "Do not return intermediate artifacts (e.g. only outline, only plan, only partial draft) unless the user explicitly asks for intermediate output only.\n\n"
            f"You are in skill execution mode. The active skill instructions are:\n\n{skill_block}"
        )

    def _ensure_skill_execution_context(
        self, messages: list[dict[str, Any]], skill_content: str, skill_name: str = ""
    ) -> None:
        """Inject or update merged system message (objective + skill content + load_subskill enforcement).
        Recovers conversation from Recent session messages + tool-loop and adds as user/assistant prompts.
        """
        # Extract conversation before trim (from system Recent session messages + tool loop)
        from_system = self._extract_conversation_from_system(messages)
        from_loop = self._extract_tool_loop_conversation(messages, exclude_load_skill=True)
        recovered: list[dict[str, str]] = list(from_system)
        recovered.extend(from_loop)
        if not recovered:
            recovered = [{"role": "user", "content": self._extract_main_objective(messages) or "Complete the user request."}]
        objective = self._last_substantive_objective(recovered) or self._extract_main_objective(messages) or "Complete the user request."
        content = self._format_skill_execution_system(skill_content, skill_name, objective)
        merged = {"role": "system", "content": content}
        i = 0
        replaced = False
        while i < len(messages):
            m = messages[i]
            if m.get("role") == "system" and (
                _SKILL_EXECUTION_MARKER in str(m.get("content") or "")
                or _LOOP_OBJECTIVE_MARKER in str(m.get("content") or "")
            ):
                if not replaced:
                    m["content"] = content
                    replaced = True
                    i += 1
                else:
                    messages.pop(i)
                continue
            i += 1
        if not replaced:
            messages.insert(0, merged)
        self._trim_messages_for_skill_execution(messages, recovered_pairs=recovered)

    def _trim_messages_for_skill_execution(
        self, messages: list[dict[str, Any]], recovered_pairs: list[dict[str, str]] | None = None
    ) -> None:
        """During skill execution, remove main system prompt and load_skill assistant+tool.
        Replace with recovered user/assistant conversation to preserve context.
        """
        i = 0
        while i < len(messages):
            m = messages[i]
            if m.get("role") != "system":
                i += 1
                continue
            content = str(m.get("content") or "")
            if "Available tools" in content and (
                _LOOP_OBJECTIVE_MARKER not in content and _SKILL_EXECUTION_MARKER not in content
            ):
                messages.pop(i)
                continue
            i += 1
        while len(messages) >= 2:
            last = messages[-1]
            prev = messages[-2]
            if last.get("role") == "tool" and prev.get("role") == "assistant":
                tcs = prev.get("tool_calls") or []
                if len(tcs) == 1 and (tcs[0].get("function") or {}).get("name") == "load_skill":
                    messages.pop()
                    messages.pop()
                    continue
            break
        # Remove all non-system messages and replace with recovered conversation
        while len(messages) > 1:
            messages.pop()
        for p in (recovered_pairs or []):
            messages.append({"role": p["role"], "content": p.get("content", "")})

    def run(
        self,
        messages: list[dict[str, Any]],
        session_id: str,
        user_id: str,
        user_timezone: str | None = None,
    ) -> tuple[str | None, bool, dict[str, Any] | None, dict[str, Any] | None]:
        """Run agentic tool loop. Returns (reply_text or None, used_fallback, reminder_payload, hitl_payload).
        When hitl_payload is set, reply_text is None and the chat layer must pause and surface the checkpoint.
        """
        self._ensure_loop_objective_context(messages)
        reminder_payload: dict[str, Any] | None = None
        empty_round_retries = 0
        max_rounds = self.config.max_tool_rounds
        max_empty = self.config.max_empty_response_retries

        for round_index in range(max_rounds):
            content, tool_calls = complete_with_tools(
                messages, self._tools_for_messages(messages)
            )
            try:
                log_chat_llm_round(session_id, round_index + 1, messages, content, tool_calls)
            except Exception:
                pass
            if content and not tool_calls:
                try:
                    log_chat_final_response(session_id, content, False, reminder_payload)
                except Exception:
                    pass
                return content, False, reminder_payload, None
            if not tool_calls:
                if not (content or "").strip() and empty_round_retries < max_empty:
                    empty_round_retries += 1
                    if empty_round_retries < max_empty:
                        retry_instruction = (
                            "You returned an empty response. Continue from the latest tool result while staying focused on the same main objective. "
                            "Either provide tool calls or the final assistant response."
                        )
                    else:
                        retry_instruction = (
                            "You repeatedly returned an empty response. Continue from the latest tool result and provide the final assistant response "
                            "for the same main objective in this turn. Do not leave content empty."
                        )
                    messages.append({"role": "user", "content": retry_instruction})
                    continue
                if not (content or "").strip():
                    recovery_text = (
                        "I hit a temporary generation issue while finishing that request. "
                        'Please reply with "continue" and I will resume from the last step.'
                    )
                    try:
                        log_chat_final_response(session_id, recovery_text, True, reminder_payload)
                    except Exception:
                        pass
                    return recovery_text, True, reminder_payload, None
                break
            empty_round_retries = 0
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)
            for execution_index, tc in enumerate(tool_calls, start=1):
                name = (tc.get("function") or {}).get("name", "")
                args = (tc.get("function") or {}).get("arguments", "{}")
                result, br, hitl_payload = execute_tool(
                    name,
                    args,
                    session_id,
                    user_id,
                    user_timezone=user_timezone,
                    loop_context={
                        "round_index": round_index + 1,
                        "max_rounds": max_rounds,
                        "execution_index": execution_index,
                        "execution_total": len(tool_calls),
                        "tool_call_id": tc.get("id", ""),
                    },
                )
                success = True
                try:
                    parsed_result = json.loads(result)
                    if isinstance(parsed_result, dict) and parsed_result.get("error"):
                        success = False
                except Exception:
                    success = True
                record_openviking_session_usage(
                    session_id,
                    skill={
                        "uri": f"viking://agent/skills/{name}" if name else "",
                        "input": args if isinstance(args, str) else json.dumps(args),
                        "output": result,
                        "success": success,
                    },
                )
                if hitl_payload:
                    tool_call_id = tc.get("id", "")
                    checkpoint_id = set_pending(
                        session_id=session_id,
                        user_id=user_id,
                        messages=messages,
                        tool_call_id=tool_call_id,
                        hitl_input=hitl_payload,
                        user_timezone=user_timezone,
                    )
                    hitl_payload["checkpoint_id"] = checkpoint_id
                    hitl_payload["session_id"] = session_id
                    hitl_payload["tool_call_id"] = tool_call_id
                    return None, False, reminder_payload, hitl_payload
                if br:
                    reminder_payload = br
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })
                if name == "load_skill":
                    extracted = self._extract_skill_content_from_load_skill_result(result)
                    if extracted:
                        skill_content, skill_name = extracted
                        self._ensure_skill_execution_context(
                            messages, skill_content, skill_name
                        )
                else:
                    self._inject_reflection_after_subskill(messages, name)
        return None, True, reminder_payload, None
