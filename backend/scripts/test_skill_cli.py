#!/usr/bin/env python3
"""CLI test for the skill registry and chat tools.

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

_HIDDEN_TOOLS: set[str] = set()


def _filter_hidden_tools_in_text(text: str) -> str:
    """Remove hidden tool lines from printed/injected context text."""
    out_lines: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if any(stripped.startswith(f"- {name}:") for name in _HIDDEN_TOOLS):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


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
    """Run tool loop via native agent; on HITL prompt and continue. Returns (final_reply, hitl_payload or None)."""
    from app.agent import get_default_agent

    agent = get_default_agent()
    while True:
        run_res = agent.run(messages, session_id, user_id, user_timezone=None)
        trace_getter = getattr(agent, "get_last_trace", None)
        if callable(trace_getter):
            trace_lines = trace_getter()
            if trace_lines:
                print("\n--- Agent execution trace ---")
                for line in trace_lines:
                    print(f"  - {line}")
                print("--- End trace ---")
        reasoning_getter = getattr(agent, "get_last_reasoning", None)
        if callable(reasoning_getter):
            reasoning_lines = reasoning_getter()
            if reasoning_lines:
                print("\n--- Agent thought summary ---")
                for line in reasoning_lines:
                    print(f"  - {line}")
                print("--- End thoughts ---")
        if run_res.hitl_payload is None:
            return run_res.text, None
        checkpoint_id = str(run_res.hitl_payload.get("checkpoint_id") or "")
        if not checkpoint_id:
            print("[HITL checkpoint missing checkpoint_id]")
            return None, run_res.hitl_payload
        response = prompt_hitl_cli(run_res.hitl_payload)
        from agno.run.requirement import RunRequirement
        from app.hitl import consume_pending

        pending = consume_pending(checkpoint_id)
        if not pending:
            print("[HITL checkpoint expired]")
            return None, run_res.hitl_payload
        reqs = [RunRequirement.from_dict(item) for item in (pending.get("requirements") or []) if isinstance(item, dict)]
        if not reqs:
            print("[HITL checkpoint missing requirements]")
            return None, run_res.hitl_payload
        req = reqs[0]
        if response.get("cancelled"):
            req.reject(note="User cancelled")
        else:
            req.confirm()
        run_res = agent.continue_run(
            run_id=str(pending.get("run_id") or ""),
            requirements=reqs,
            session_id=session_id,
            user_id=user_id,
            user_timezone=None,
        )
        if run_res.hitl_payload is None:
            return run_res.text, None

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
        put_openviking_session,
    )
    from app.core.config import get_settings
    from app.core.chat_logging import log_chat_final_response

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

        messages: list[dict[str, Any]] = [{"role": "user", "content": line}]
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
        help="One-shot: load this skill and print",
    )
    parser.add_argument(
        "--subskill",
        metavar="PATH",
        help="One-shot: also read this subskill path (e.g. exam-mode-tuner/question-generation/question-generation.md)",
    )
    args = parser.parse_args()

    from app.context import get_cached_tools, load_agent_context
    from app.skills.registry import build_skill_registry, get_skill_registry, get_skills_root

    root = get_skills_root()
    build_skill_registry(root)
    load_agent_context()
    registry = get_skill_registry()
    tools = [t for t in get_cached_tools() if t.get("name") not in _HIDDEN_TOOLS]

    print("--- Agent CLI Context ---")
    print(f"Tools ({len(tools)}):")
    for t in tools:
        print(f"  - {t.get('name', '')}: {t.get('description', '')}")

    print(f"Skills root: {root}")
    print(f"Registered skills ({len(registry)}):")
    for s in registry:
        print(f"  - {s['name']}: {s['description']}")
    print("--- End Context ---")

    if args.list:
        return 0

    # Conversational mode (default when no one-shot args)
    if args.chat or (not args.skill and not args.subskill):
        return run_chat()

    # One-shot: load skill and optionally subskill
    if args.skill:
        print(f"\n--- skill {args.skill!r} ---")
        skill_name = (args.skill or "").strip()
        if not skill_name or "/" in skill_name or "\\" in skill_name or skill_name in (".", ".."):
            print("Error: invalid skill name")
            return 1
        skill_md = root / skill_name / "SKILL.md"
        if not skill_md.is_file():
            print(f"Error: skill not found: {skill_name}")
            return 1
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        lines = content.strip().split("\n")
        print(f"OK ({len(content)} chars, {len(lines)} lines)")
        for line in lines[:20]:
            print(f"  {line}")
        if len(lines) > 20:
            print(f"  ... ({len(lines) - 20} more)")

    if args.subskill:
        print(f"\n--- subskill {args.subskill!r} ---")
        path_str = (args.subskill or "").strip().replace("\\", "/")
        if not path_str or path_str.startswith("/") or ".." in path_str.split("/"):
            print("Error: invalid or unsafe subskill path")
            return 1
        parts = [p for p in path_str.split("/") if p and p != "."]
        resolved = root
        for p in parts:
            resolved = resolved / p
        try:
            resolved = resolved.resolve()
            root_resolved = root.resolve()
            if not str(resolved).startswith(str(root_resolved)):
                print("Error: subskill path escapes skills root")
                return 1
        except Exception as e:  # pragma: no cover - defensive
            print(f"Error: failed to resolve subskill path: {e}")
            return 1
        if not resolved.is_file():
            print(f"Error: subskill not found: {path_str}")
            return 1
        content2 = resolved.read_text(encoding="utf-8", errors="replace")
        lines2 = content2.strip().split("\n")
        print(f"OK ({len(content2)} chars, {len(lines2)} lines)")
        for line in lines2[:15]:
            print(f"  {line}")
        if len(lines2) > 15:
            print(f"  ... ({len(lines2) - 15} more)")
    elif not args.skill:
        print("\nError: provide --skill and/or --subskill for one-shot mode.")
        return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
