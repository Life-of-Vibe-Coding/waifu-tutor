"""Human-in-the-loop: request approval, free-form input, or selection from options. Pauses the agent until the user responds."""
from __future__ import annotations

from typing import Any

# Sentinel returned by run() to signal the chat layer to pause and surface HITL.
# The chat layer checks for this and does not append a normal tool result.
HITL_SENTINEL = "__HITL_PAUSE__"

TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "request_human_approval",
        "description": (
            "Pause and ask the user for input before continuing. Use before consequential actions (e.g. confirm exam params) "
            "or after significant outputs (e.g. choose next skill). The user can: approve, provide overrides/input, "
            "or select one of the provided options. Do not proceed until the user responds."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "checkpoint": {
                    "type": "string",
                    "description": "Short identifier for this checkpoint (e.g. exam_params, post_exam_routing).",
                },
                "summary": {
                    "type": "string",
                    "description": "Human-readable summary shown to the user (e.g. what will happen or what to decide).",
                },
                "params": {
                    "type": "object",
                    "description": "Optional structured data the user may approve or modify (e.g. question_count, types, time_limit_min).",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of choices the user can pick from (e.g. next skill or 'Stop here').",
                },
                "allow_free_input": {
                    "type": "boolean",
                    "description": "If true, the user may submit free-form text in addition to approve/modify/options.",
                    "default": False,
                },
            },
            "required": ["checkpoint", "summary"],
        },
    },
}


def run(
    args: dict[str, Any],
    session_id: str,
    user_id: str,
    user_timezone: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Does not return a normal result. Raises a special exception or returns a sentinel so the chat layer stores state and pauses."""
    # We return the sentinel string and the caller (execute_tool) will detect it and return (result, None, hitl_payload).
    # Actually we need execute_tool to return 3 values. So the run() contract is (result_str, reminder_payload).
    # We'll use a custom return: we need the chat layer to get (None, None, hitl_payload). So execute_tool must
    # support a special case: when this tool runs, it doesn't return (result, reminder) but signals HITL.
    # Option A: run() raises HitlPause(hitl_payload) and execute_tool catches it and returns (sentinel, None, hitl_payload).
    # Option B: run() returns (HITL_SENTINEL, hitl_payload_dict). execute_tool checks if result == HITL_SENTINEL and then
    # returns (result, reminder, hitl_payload) with a third value.
    # I'll do Option B: run returns (HITL_SENTINEL, payload). execute_tool will return 3-tuple when payload is a dict with checkpoint_id etc.
    # Actually the payload for the frontend needs checkpoint_id, session_id, checkpoint, summary, params, options. The checkpoint_id
    # and session_id are added by the chat layer when it stores state. So run() just returns (HITL_SENTINEL, input_data) and
    # the chat layer adds checkpoint_id, session_id and stores messages etc.
    payload: dict[str, Any] = {
        "checkpoint": (args.get("checkpoint") or "").strip(),
        "summary": (args.get("summary") or "").strip(),
        "params": args.get("params"),
        "options": args.get("options"),
        "allow_free_input": bool(args.get("allow_free_input")),
    }
    if not payload["checkpoint"] or not payload["summary"]:
        return (
            '{"error": "checkpoint and summary are required"}',
            None,
        )
    # Return sentinel as first element; second element we use to pass the payload. But run() signature is (str, reminder|None).
    # So we need to extend the contract: run() can return (HITL_SENTINEL, extra_dict). If extra_dict has a key like "_hitl",
    # then execute_tool returns 3-tuple. Let me define: run() returns (result_str, reminder_payload). For HITL we need a third
    # value. So I'll change execute_tool to return a 3-tuple: (result_str, reminder_payload, hitl_payload). Normal tools return
    # (result, reminder, None). request_human_approval's run() will return (HITL_SENTINEL, payload). So we need run() to return
    # something that carries the payload. Option: run() returns (HITL_SENTINEL, payload_dict). So the second return value is
    # normally reminder_payload (dict or None). If we return (HITL_SENTINEL, {...}) the {...} could be the HITL payload and
    # we'd confuse it with reminder_payload. So let's use a special reminder_payload: e.g. {"_hitl": True, "checkpoint": ..., ...}.
    # Then execute_tool returns (result, None, reminder_payload) when reminder_payload has _hitl, and the chat layer checks for that.
    payload["_hitl"] = True
    return (HITL_SENTINEL, payload)
