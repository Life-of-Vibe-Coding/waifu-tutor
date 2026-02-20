#!/usr/bin/env python3
"""CLI test for the skill registry and load_skill/load_subskill tools.

Usage (from backend directory):
  uv run python scripts/test_skill_cli.py --chat          # conversational (default)
  uv run python scripts/test_skill_cli.py --list          # list skills and exit
  uv run python scripts/test_skill_cli.py --skill NAME    # one-shot load skill
  uv run python scripts/test_skill_cli.py --skill NAME --subskill PATH
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure backend app is on path when run from project root or backend
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

MAX_TOOL_ROUNDS = 20


def prompt_hitl_cli(hitl: dict[str, Any]) -> dict[str, Any]:
    """Prompt user in terminal for HITL response. Returns dict for tool result."""
    print("\n--- Human-in-the-loop ---")
    print(hitl.get("summary", ""))
    params = hitl.get("params")
    if params:
        print("Params:", json.dumps(params, indent=2))
    options = hitl.get("options") or []
    if options:
        print("Options:")
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
    print("  a = Approve, c = Cancel, or enter option number/text to select")
    line = (input("> ").strip() or "a").lower()
    if line in ("c", "cancel", "n", "no"):
        return {"cancelled": True}
    if line in ("a", "approve", "y", "yes", ""):
        return {"approved": True}
    # Option by number or by text
    if line.isdigit():
        idx = int(line)
        if 1 <= idx <= len(options):
            return {"selected": options[idx - 1]}
    if line in options:
        return {"selected": line}
    # Treat as free input if allowed
    if hitl.get("allow_free_input"):
        return {"free_input": line}
    return {"approved": True}


def run_agentic_loop_cli(
    messages: list[dict[str, Any]],
    session_id: str,
    user_id: str,
) -> tuple[str | None, dict[str, Any] | None]:
    """Run tool loop; on HITL prompt in CLI and continue. Returns (final_reply, hitl_payload or None)."""
    from app.api.chat import (
        _ensure_loop_objective_context,
        _ensure_skill_execution_context,
        _extract_skill_content_from_load_skill_result,
        _tools_for_messages,
    )
    from app.services.ai import complete_with_tools
    from app.tool import execute_tool
    from app.core.chat_logging import log_chat_agent_input

    _ensure_loop_objective_context(messages)
    empty_round_retries = 0
    for round_index in range(MAX_TOOL_ROUNDS):
        try:
            log_chat_agent_input(session_id, json.dumps(messages, indent=2, ensure_ascii=True))
        except Exception:
            pass
        content, tool_calls = complete_with_tools(messages, _tools_for_messages(messages))
        if content and not tool_calls:
            # Append assistant reply so next turn has full history
            messages.append({"role": "assistant", "content": content})
            return content, None
        if not tool_calls:
            if not (content or "").strip() and empty_round_retries < 2:
                empty_round_retries += 1
                messages.append({
                    "role": "user",
                    "content": (
                        "You returned an empty response. Continue from the latest context/tool result. "
                        "Or the final assistant response."
                    ),
                })
                continue
            break
        empty_round_retries = 0
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        for execution_index, tc in enumerate(tool_calls, start=1):
            name = (tc.get("function") or {}).get("name", "")
            args = (tc.get("function") or {}).get("arguments", "{}")
            result, _br, hitl_payload = execute_tool(
                name,
                args,
                session_id,
                user_id,
                loop_context={
                    "round_index": round_index + 1,
                    "max_rounds": MAX_TOOL_ROUNDS,
                    "execution_index": execution_index,
                    "execution_total": len(tool_calls),
                    "tool_call_id": tc.get("id", ""),
                },
            )
            if hitl_payload:
                response = prompt_hitl_cli(hitl_payload)
                if response.get("cancelled"):
                    result = json.dumps({"approved": False, "cancelled": True})
                else:
                    result = json.dumps({
                        "approved": True,
                        "overrides": response.get("overrides"),
                        "selected": response.get("selected"),
                        "free_input": response.get("free_input"),
                    })
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result})
            if name == "load_skill":
                extracted = _extract_skill_content_from_load_skill_result(result)
                if extracted:
                    skill_content, skill_name = extracted
                    _ensure_skill_execution_context(messages, skill_content, skill_name)
    return None, None


def _messages_to_conversation_history(messages: list[dict[str, Any]], max_items: int = 12, max_content_len: int = 1500) -> list[dict[str, str]]:
    """Build conversation_history from tool-loop messages (user/assistant only, truncated) for fallback chat."""
    history: list[dict[str, str]] = []
    for m in messages or []:
        role = m.get("role")
        if role == "tool":
            continue
        if role not in ("user", "assistant"):
            continue
        content = (m.get("content") or "").strip()
        if len(content) > max_content_len:
            content = content[:max_content_len] + "..."
        history.append({"role": role, "content": content})
    return history[-max_items:]


def run_chat() -> int:
    """Interactive conversational loop with skills and HITL."""
    from app.context import (
        append_openviking_text_message,
        build_openviking_chat_context,
        get_agent_context_text,
        load_agent_context,
        put_openviking_session,
    )
    from app.core.config import get_settings
    from app.core.chat_logging import log_chat_agent_input, log_chat_final_response

    load_agent_context()
    agent_context = get_agent_context_text()
    session_id = "cli-session"
    user_id = get_settings().demo_user_id

    print("Skills CLI (conversational). Say 'quit' or 'exit' to stop.\n")
    conversation_history: list[dict[str, str]] = []

    while True:
        try:
            line = input("You: ").strip()
        except EOFError:
            break
        if not line or line.lower() in ("quit", "exit", "q"):
            break

        context_texts, ov_session = build_openviking_chat_context(
            session_id=session_id,
            user_id=user_id,
            user_message=line,
            history=conversation_history,
            doc_id=None,
            attachment_title=None,
            attachment_uri=None,
        )
        put_openviking_session(ov_session)

        context_block = "\n\n".join(context_texts[:14])
        system_content = (
            f"Context:\n{context_block}\n\n"
            "Instructions:\n"
            "Reply in character: accurate, helpful, concise, and encouraging. Use tools when appropriate."
        )
        if agent_context:
            system_content = f"{agent_context}\n\n{system_content}"
        try:
            log_chat_agent_input(session_id, system_content)
        except Exception:
            pass

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": line},
        ]
        reply, hitl = run_agentic_loop_cli(messages, session_id, user_id)
        if hitl:
            print("[HITL not resolved in loop – this should not happen]\n")
            continue
        if reply:
            conversation_history.append({"role": "user", "content": line})
            conversation_history.append({"role": "assistant", "content": reply})
            append_openviking_text_message(session_id, "assistant", reply)
            try:
                log_chat_final_response(session_id, reply, False, None)
            except Exception:
                pass
            print(f"\nAssistant: {reply}\n")
        else:
            from app.services.ai import chat as ai_chat
            # Pass recent conversation so fallback knows context (e.g. essay outline approved, need paragraphs)
            fallback_history = _messages_to_conversation_history(messages)
            reply, _ = ai_chat(line, context_texts, None, conversation_history=fallback_history or conversation_history)
            if not (reply or "").strip():
                reply = "I'm sorry, I couldn't complete that. Please try again."
            conversation_history.append({"role": "user", "content": line})
            conversation_history.append({"role": "assistant", "content": reply})
            append_openviking_text_message(session_id, "assistant", reply)
            try:
                log_chat_final_response(session_id, reply, True, None)
            except Exception:
                pass
            print(f"\nAssistant: {reply}\n")

    print("Bye.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test skill registry and tools from CLI")
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Run in conversational mode (default if no other args)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Only list registered skills and exit",
    )
    parser.add_argument(
        "--skill",
        metavar="NAME",
        help="One-shot: load this skill and print (default: exam-mode-tuner)",
    )
    parser.add_argument(
        "--subskill",
        metavar="PATH",
        help="One-shot: also read this subskill path (e.g. exam-mode-tuner/question-generation/question-generation.md)",
    )
    args = parser.parse_args()

    from app.skills.registry import build_skill_registry, get_skill_registry, get_skills_root
    from app.tool.tools import load_skill, load_subskill

    root = get_skills_root()
    build_skill_registry(root)
    registry = get_skill_registry()

    print(f"Skills root: {root}")
    print(f"Registered skills ({len(registry)}):")
    for s in registry:
        desc = s["description"]
        print(f"  - {s['name']}: {(desc[:57] + '...') if len(desc) > 60 else desc}")

    if args.list:
        return 0

    # Conversational mode (default when no one-shot args)
    if args.chat or (not args.skill and not args.subskill):
        return run_chat()

    # One-shot: load skill and optionally subskill
    skill_name = args.skill or "exam-mode-tuner"
    print(f"\n--- load_skill({skill_name!r}) ---")
    result, _ = load_skill.run({"name": skill_name}, "cli-session", "cli-user")
    data = json.loads(result)
    if "error" in data:
        print(f"Error: {data['error']}")
        return 1
    content = data.get("content", "")
    lines = content.strip().split("\n")
    print(f"OK ({len(content)} chars, {len(lines)} lines)")
    for line in lines[:20]:
        print(f"  {line}")
    if len(lines) > 20:
        print(f"  ... ({len(lines) - 20} more)")

    if args.subskill:
        print(f"\n--- load_subskill({args.subskill!r}) ---")
        result2, _ = load_subskill.run({"path": args.subskill}, "cli-session", "cli-user")
        data2 = json.loads(result2)
        if "error" in data2:
            print(f"Error: {data2['error']}")
            return 1
        content2 = data2.get("content", "")
        lines2 = content2.strip().split("\n")
        print(f"OK ({len(content2)} chars, {len(lines2)} lines)")
        for line in lines2[:15]:
            print(f"  {line}")
        if len(lines2) > 15:
            print(f"  ... ({len(lines2) - 15} more)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
