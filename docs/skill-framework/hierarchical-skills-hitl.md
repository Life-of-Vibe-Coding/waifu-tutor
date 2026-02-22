# How Skills and Tools Are Executed: Hierarchical Skills (Agno Native)

---

## Core Concepts

Before diving in, two key distinctions:

**Tools vs Skills vs Subskills**

| Layer | Examples | What it is | Where it lives |
|---|---|---|---|
| **Tools** | `set_break_reminder`, `list_recent_uploads` | Low-level verbs — fixed capabilities exposed to Agno | `backend/app/tool/tools/*.py` |
| **Skills** | `exam-mode-tuner` | High-level recipe — orchestrates subskills for a complete task | `skills/*/SKILL.md` |
| **Subskills** | `question-generation`, `adaptive-difficulty` | Focused sub-recipes — handle one phase of the parent skill | `skills/*/subskill/*.md` |

**Eager vs Lazy Loading**

The registry reads only YAML frontmatter at startup. Full skill and subskill content is loaded on demand — only when the model decides it's needed. This keeps token costs low and lets subskills stay invisible until the parent delegates to them.

**Core execution model**

1. A skill is executed within one continuous Agno agent run that can call tools and read skill markdown as needed.
2. When the skill completes (final assistant content, no further tool calls), the agent run ends. The next user message starts a fresh run; the previous turn’s internal tool trace is not replayed, though user/assistant text history is available.

---

## Phase 1: Startup — The Registry

`build_skill_registry()` scans every top-level folder in `skills/` and reads only the YAML frontmatter of each `SKILL.md`:

```yaml
---
name: exam-mode-tuner
description: Runs adaptive practice exams with grading and analytics...
---
```

Subskills are **not** registered. They are unknown to the model until the parent skill's instructions explicitly reference them. This is intentional — subskill details are an implementation concern of the parent, not a top-level routing concern.

---

## Phase 2: User Sends a Message

The user says something like *"Give me a practice test on data structures."* This is appended to `messages` and sent to the API.

The model matches intent to `exam-mode-tuner` in the registry and decides to load it before doing anything else.

---

## Phase 3: The Agentic Loop (inside Agno)

The old Python `while True` loop has been removed. Instead:

- The backend sends a single user message to the Agno agent with:
  - chat + document context
  - a text summary of available tools and top-level skills.
- Agno internally:
  - calls tools via the registered `Function` objects that wrap `execute_tool(...)`
  - loads skill and subskill markdown as needed through its native skill system
  - continues until it returns a final assistant message (or nothing).

The Python wrapper in `app.agent` simply builds the Agno agent, calls `agent.run(...)`, and post-processes the result.

---

## Phase 4: Subskill Loading — Progressive Delegation

When the parent skill's instructions say *"call → question-generation"*, the model issues a `load_subskill` tool call for the subskill's markdown file. It does not load subskills eagerly — it reads them one at a time, exactly when the workflow reaches that phase.

```
Round 1  →  load_skill("exam-mode-tuner")
                Parent skill loaded. Pipeline enters skill execution mode; system prompt displays SKILL.md.

Round 2  →  load_subskill("question-generation/question-generation.md")
                Subskill loaded. Model generates question plan.

[HITL checkpoint — see below]

Round 3  →  <exam runs per-question loop>
                load_subskill("adaptive-difficulty/adaptive-difficulty.md")  ← per answer
                    Subskill loaded. Model adjusts difficulty.

Round 4  →  load_subskill("performance-analytics/performance-analytics.md")
                Subskill loaded. Model produces report.

[HITL checkpoint — see below]

Round 5  →  stop_reason == "end_turn"  ✓ EXIT
```

Each `load_subskill` call for a subskill follows the same tool round-trip as any other tool call — the result is appended to `messages` as a `tool_result`, and the loop continues. The model never has all subskills in context simultaneously unless it explicitly loads them; it only carries what it has needed so far.

---

## Phase 5: HITL Checkpoints (Design vs Current Reality)

The examples in this document (and some skill markdown files) describe explicit HITL checkpoints using a `request_human_approval` tool. That tool and its handler have been removed from the live tool registry.

Current behavior:

- No tool emits HITL checkpoints.
- `hitl_payload` from `get_default_agent().run(...)` is always `None`.
- The backend store (`app/hitl/store.py`), API resume endpoint, and frontend modal exist but are dormant.

So, treat the HITL examples as **design references** for a future iteration where HITL might be reintroduced, not as a description of how the system behaves today.

---

## Why the Model Never "Guesses"

Two mechanisms enforce this:

The system prompt instructs the model to never fabricate subskill outputs, grading results, or routing decisions. It must load the relevant subskill and receive its instructions before acting.

HITL checkpoints are grounded the same way — the model cannot proceed past a checkpoint without a `tool_result` from the human. An unanswered checkpoint leaves the loop suspended, not progressing.

---

## The Full Picture

```
Startup
└── Registry: only frontmatter of top-level skills loaded

User message
└── Model matches intent → decides to load parent skill

Agentic loop
├── [R1] load_skill("exam-mode-tuner")            ← skill execution pipeline entered; system prompt displays SKILL.md
├── [HITL-A] request_human_approval(exam_params)  ← pause; user confirms or edits
├── [R2] load_subskill("question-generation/...") ← subskill loaded on demand
├── [R3–Rn] per-answer loop
│       └── load_subskill("adaptive-difficulty/...")  ← subskill re-read each iteration
├── [Rn+1] load_subskill("performance-analytics/...") ← subskill loaded after exam ends
├── [HITL-B] request_human_approval(post_routing) ← pause; user picks next step
└── end_turn → return final output to user
```

Subskills are loaded exactly when needed. Humans are consulted exactly when the stakes warrant it. Neither happens more than necessary.

---

## Context Persistence and Subskill Execution

When a task requires **multiple subskill checks** (e.g. parent skill → subskill A → subskill B), context and execution behave as follows.

### Within one agent run: **yes**

- Agno maintains its own message history, including tool calls and results, for the duration of the run.
- Multiple skill loads and subskill reads occur in one run without losing context.

### Across separate user turns: **limited**

- Persisted chat storage (and the history the client sends on the next request) contains only **user and assistant text messages**, not the internal tool trace.
- Each new user message starts a fresh agent run built from the current prompt and the client-provided `history`; the previous turn’s internal tool-call chain is not replayed.

### Correct execution of subskills: **prompt-guided**

- Skill docs still define the expected steps, including when to consult subskills.
- There is no server-side orchestrator that verifies that every substep was followed.
- Long-horizon correctness across turns depends on clear skill instructions and model behavior.
