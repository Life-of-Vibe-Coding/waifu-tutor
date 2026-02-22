# Runbook: Agentic Skills (Agno Native)

This runbook explains how to define skills and how they are wired into the Agno-backed agent after removing the custom Python harness.

## Adding a new top-level skill

1. **Create a folder** under the skills root (default: `docs/skill-framework/`) with the skill name, e.g. `my-skill/`.
2. **Add `SKILL.md`** in that folder with YAML frontmatter so the registry picks it up:
   ```yaml
   ---
   name: my-skill
   description: One-line description shown in the registry and used for intent matching.
   ---
   # My Skill
   ## When to Use
   ...
   ## Steps
   ...
   ```
3. **Subskills** (optional): Add subfolders under the skill, e.g. `my-skill/phase-a/phase-a.md`. Agno’s native skill system (`agno.skills.Skills` + `LocalSkills`) can load these markdown files when the model decides to follow the instructions in your top-level skill. Subskills are not explicitly registered; they are implementation details of the parent.
4. **Restart** the backend (or rely on startup) so `build_skill_registry()` rescans and injects the new skill into the agent context.

## HITL checkpoints (current status)

- The previous design exposed a `request_human_approval` tool that paused the custom harness loop and surfaced a checkpoint to the user.
- After migrating to the native Agno agent:
  - `request_human_approval` is no longer registered as a tool.
  - The Agno wrapper in `app.agent` does not emit HITL checkpoints; `hitl_payload` is always `None`.
- Existing components that reference HITL remain in the codebase but are effectively disabled:
  - backend storage: `backend/app/hitl/store.py`
  - API resume endpoint: `/api/ai/chat/hitl-response`
  - frontend modal in `ChatPage` for HITL confirmation.
- Skill docs may still mention HITL checkpoints as part of the ideal workflow, but they do not correspond to a live tool right now.

## Configuration

- **Skills root**: Set `SKILLS_DIR` in backend `.env` to override the default `docs/skill-framework` (path relative to project root or absolute).

## Testing from CLI

From the **backend** directory:

**Conversational (interactive)** – chat with the Agno-backed agent; skills and tools run in the terminal. Requires `VOLCENGINE_API_KEY` in `.env`.

```bash
cd backend
uv run python scripts/test_skill_cli.py
# or explicitly:
uv run python scripts/test_skill_cli.py --chat
```

At the prompt, ask for a practice exam or to load a skill. The CLI now performs a single agent turn per user message; HITL checkpoints are not expected because the HITL tool is no longer registered.

**One-shot**

```bash
uv run python scripts/test_skill_cli.py --list
uv run python scripts/test_skill_cli.py --skill exam-mode-tuner
uv run python scripts/test_skill_cli.py --skill exam-mode-tuner --subskill exam-mode-tuner/question-generation/question-generation.md
```

- `--list`: Print skills root and registered skills only.
- `--skill NAME`: Load that skill’s `SKILL.md` and print the first 20 lines (default: `exam-mode-tuner`).
- `--subskill PATH`: Also read a subskill file and print the first 15 lines.

## Safety

- **Skill paths**: When resolving subskill paths in tests or utilities, only paths under the skills root are allowed; `..` and absolute paths are rejected.
- **Registry**: Missing or malformed frontmatter is skipped with a warning; startup does not fail.
