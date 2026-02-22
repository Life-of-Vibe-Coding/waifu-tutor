# Agentic Skill Workflow (Agno Native)

This document describes the current agentic workflow in the chat backend after migrating from a custom Python harness to a native [Agno](https://pypi.org/project/agno/) agent. The Agno agent now owns the tool-calling loop; the backend focuses on:

- assembling context (documents, reminders, skill registry)
- exposing tools to Agno in OpenAI-style schema
- wrapping the Agno agent in a simple helper used by the API and CLI

## High-Level Flow

1. Startup
- `app.context.load_agent_context()` calls `get_default_agent().get_cached_tools()` and `build_skill_registry()`.
- Tools come from `backend/app/tool/tools/__init__.py` as OpenAI-style JSON schemas.
- Skills are discovered from YAML frontmatter in `SKILL.md` files under the skills root via `backend/app/skills/registry.py`.

2. Building the Agno Agent
- `get_default_agent()` in `backend/app/agent/__init__.py` constructs a lightweight wrapper around `agno.agent.Agent`.
- For each tool schema in `CHAT_TOOLS`, it wraps `execute_tool(name, args, ...)` in an `agno.tools.Function`.
- It also constructs `agno.skills.Skills` using `LocalSkills(path=settings.skills_dir, validate=False)` so Agno can load skill markdown natively.

3. Per-Request Chat Flow
- `POST /api/ai/chat` and `/api/ai/chat/stream` call `_complete_chat()` in `backend/app/api/chat.py`.
- `_complete_chat()`:
  - builds OpenViking-style context via `build_openviking_chat_context()`
  - concatenates tool + skill registry context from `get_agent_context_text()`
  - assembles a single user message asking the agent to answer in character and use tools when appropriate
- It then calls `get_default_agent().run(messages, session_id, user_id, user_timezone)`.

4. Inside the Agno Agent
- The custom Python `while True` tool loop has been removed.
- Agno:
  - receives messages and the registered tools/skills
  - decides when to call tools and which skills to load
  - iterates internally until it produces a final assistant message (or no output)
- The wrapper in `app.agent` only:
  - builds the agent
  - calls `agent.run(agno_msgs)`
  - returns `(reply_text_or_none, used_fallback, reminder_payload, hitl_payload)` where `hitl_payload` is always `None` in the current implementation.

5. Fallback behavior
- If the Agno agent returns no usable assistant text, `_complete_chat()` falls back to `ai_chat()` with compacted conversation history.
- This mirrors the previous behavior but without a custom tool loop.

## Human-in-the-Loop (HITL) Status

- The legacy HITL tool (`request_human_approval`) and its Python handler have been removed from the tool registry.
- Existing HITL infrastructure is still present but dormant:
  - backend store: `backend/app/hitl/store.py`
  - API resume endpoint: `/api/ai/chat/hitl-response`
  - frontend modal: `ChatPage` HITL checkpoint UI
- Since no tool currently produces HITL checkpoints, `hitl_payload` is always `None` and the HITL paths are not exercised at runtime.
- Skill docs may still describe HITL checkpoints conceptually (for future re-enablement), but they no longer correspond to a live tool.

## Primary Code Locations

- `backend/app/agent/__init__.py` — Agno-backed agent wrapper (`_SimpleAgent`)
- `backend/app/context/context_builder.py` — startup context assembly and agent context formatting
- `backend/app/skills/registry.py` — skill registry (frontmatter only)
- `backend/app/api/chat.py` — HTTP chat endpoints and fallback behavior
- `backend/app/tool/tools/__init__.py` — tool schemas and `execute_tool`
- `backend/app/hitl/store.py` — dormant HITL checkpoint storage
