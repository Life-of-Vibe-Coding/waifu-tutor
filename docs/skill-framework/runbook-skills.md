# Runbook: Agentic Skills and HITL

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

3. **Subskills** (optional): Add subfolders under the skill, e.g. `my-skill/phase-a/phase-a.md`. The model loads them on demand via the `read_file` tool when the parent skill’s instructions say so. Do not register subskills in the registry.

4. **Restart** the backend (or rely on startup) so `build_skill_registry()` rescans and injects the new skill into the agent context.

## HITL checkpoints

- The model calls the `request_human_approval` tool with `checkpoint`, `summary`, and optionally `params` and `options`.
- The agent loop pauses and the frontend shows a modal with summary, params, and options. The user can **Approve**, **Cancel**, or **Select** an option (or send **free_input** if the checkpoint allows it).
- Resume is done via `POST /api/ai/chat/hitl-response` with `session_id`, `checkpoint_id`, and `response` (e.g. `{ "approved": true }`, `{ "cancelled": true }`, or `{ "selected": "…" }`).
- Pending checkpoints expire after 30 minutes (configurable in `app/hitl/store.py`).

## Configuration

- **Skills root**: Set `SKILLS_DIR` in backend `.env` to override the default `docs/skill-framework` (path relative to project root or absolute).

## Testing from CLI

From the **backend** directory:

**Conversational (interactive)** – chat with the agent; skills and tools (including HITL) run in the terminal. Requires `VOLCENGINE_API_KEY` in `.env`.

```bash
cd backend
uv run python scripts/test_skill_cli.py
# or explicitly:
uv run python scripts/test_skill_cli.py --chat
```

At the prompt, ask for a practice exam or to load a skill; if the model calls `request_human_approval`, you’ll get a terminal prompt (approve / cancel / option). Type `quit` or `exit` to stop.

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

- **read_file**: Only paths under the skills root are allowed; `..` and absolute paths are rejected.
- **Registry**: Missing or malformed frontmatter is skipped with a warning; startup does not fail.
