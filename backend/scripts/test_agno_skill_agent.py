#!/usr/bin/env python3
"""Simple Agno + skills smoke test."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Agno agent with provided skills")
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only print discovered skills and exit",
    )
    parser.add_argument(
        "--prompt",
        default="Use the registered exam-mode-tuner skill and summarize step 1 in one short sentence.",
        help="Prompt to run through the agent harness",
    )
    parser.add_argument("--skill", default="exam-mode-tuner", help="Skill name to validate in native registration")
    parser.add_argument(
        "--live-agent",
        action="store_true",
        help="Also run a real model turn through harness.run (requires working provider config)",
    )
    parser.add_argument("--session-id", default="agno-skill-smoke-session")
    parser.add_argument("--user-id", default="agno-skill-smoke-user")
    args = parser.parse_args()

    from app.agent import get_default_agent
    from app.skills.registry import build_skill_registry, get_skill_registry, get_skills_root

    root = get_skills_root()
    build_skill_registry(root)
    skills = get_skill_registry()
    print(f"Skills root: {root}")
    print(f"Registered skills ({len(skills)}):")
    for item in skills:
        print(f"  - {item['name']}")
    if not skills:
        print("ERROR: No skills found.")
        return 1
    if args.list_only:
        return 0

    harness = get_default_agent()
    agno_skills = getattr(harness, "_agno_skills", None)
    if agno_skills is None:
        print("ERROR: native Agno skills are not initialized on harness.")
        return 2
    registered_names = set(agno_skills.get_skill_names())
    print(f"Native Agno registered skills ({len(registered_names)}):")
    for name in sorted(registered_names):
        print(f"  - {name}")
    if args.skill not in registered_names:
        print(f"ERROR: skill not registered natively: {args.skill}")
        return 3

    if not args.live_agent:
        return 0

    messages = [
        {"role": "system", "content": harness.get_agent_context_text()},
        {"role": "user", "content": args.prompt},
    ]
    try:
        reply, used_fallback, _, hitl_payload = harness.run(messages, args.session_id, args.user_id)
    except Exception as exc:
        print(f"ERROR: live agent run failed: {exc}")
        return 4

    print(f"Used fallback: {used_fallback}")
    if hitl_payload:
        print(f"HITL requested: {hitl_payload.get('type')}")
    print(f"Reply: {reply or '<empty>'}")

    if not reply and not hitl_payload:
        print("ERROR: empty response.")
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
