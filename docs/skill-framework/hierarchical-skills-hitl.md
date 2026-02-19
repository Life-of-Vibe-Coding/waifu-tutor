# How Skills and Tools Are Executed: Hierarchical Skills with HITL

---

## Core Concepts

Before diving in, two key distinctions:

**Tools vs Skills vs Subskills**

| Layer | Examples | What it is | Where it lives |
|---|---|---|---|
| **Tools** | `load_skill`, `read_file` | Low-level verbs — fixed capabilities baked into the agent | `agent.py` |
| **Skills** | `exam-mode-tuner` | High-level recipe — orchestrates subskills for a complete task | `skills/*/SKILL.md` |
| **Subskills** | `question-generation`, `adaptive-difficulty` | Focused sub-recipes — handle one phase of the parent skill | `skills/*/subskill/*.md` |

**Eager vs Lazy Loading**

The registry reads only YAML frontmatter at startup. Full skill and subskill content is loaded on demand — only when the model decides it's needed. This keeps token costs low and lets subskills stay invisible until the parent delegates to them.

**Core execution model**

1. **One full round has full context.** A skill is executed within one continuous round of execution: tools, subskills, and human-in-the-loop. Within this round, the agent has all the context it needs to complete the skill. HITL pause/resume is part of that same round — the loop resumes with the same `messages`; it does not start a new round.

2. **Exit after completion.** When the skill completes (final assistant content, no tool calls), the loop exits. The next user message starts a fresh `messages` list and a new tool loop. The previous turn’s tool trace is not carried forward — we exit the skill execution context.

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

## Phase 3: The Agentic Loop — With HITL Checkpoints

The loop runs as before — `while True`, calling the API until `stop_reason == "end_turn"`. What changes with hierarchical skills and HITL is that the loop now has **two ways to pause**: tool calls (machine-to-machine) and explicit human checkpoints (machine-to-human).

### The Extended Flow

```
while True:
    response = call Claude API
          │
          ├── stop_reason == "end_turn"
          │       └── no pending HITL → return final text  ✓ EXIT
          │
          ├── stop_reason == "tool_use"
          │       ├── load_skill    → read parent SKILL.md
          │       ├── read_file     → read subskill .md
          │       ├── <other tools> → dispatch to handler
          │       └── append tool_result → loop again
          │
          └── stop_reason == "hitl_checkpoint"
                  └── pause loop, present to user → await input
                          │
                          ├── approved  → append confirmation → loop again
                          ├── modified  → append edited params → loop again
                          └── cancelled → abort and explain
```

HITL checkpoints are not a separate stop reason in the raw API — they are a convention built on top of `tool_use`. The model calls a special tool (e.g. `request_human_approval`) whose handler pauses execution and surfaces a prompt to the user rather than returning immediately.

---

## Phase 4: Subskill Loading — Progressive Delegation

When the parent skill's instructions say *"call → question-generation"*, the model issues a `read_file` tool call for the subskill's markdown file. It does not load subskills eagerly — it reads them one at a time, exactly when the workflow reaches that phase.

```
Round 1  →  load_skill("exam-mode-tuner")
                Parent skill loaded. Model reads step list.

Round 2  →  read_file("question-generation/question-generation.md")
                Subskill loaded. Model generates question plan.

[HITL checkpoint — see below]

Round 3  →  <exam runs per-question loop>
                read_file("adaptive-difficulty/adaptive-difficulty.md")  ← per answer
                    Subskill loaded. Model adjusts difficulty.

Round 4  →  read_file("performance-analytics/performance-analytics.md")
                Subskill loaded. Model produces report.

[HITL checkpoint — see below]

Round 5  →  stop_reason == "end_turn"  ✓ EXIT
```

Each `read_file` call for a subskill follows the same tool round-trip as any other tool call — the result is appended to `messages` as a `tool_result`, and the loop continues. The model never has all subskills in context simultaneously unless it explicitly loads them; it only carries what it has needed so far.

---

## Phase 5: HITL Checkpoints in Practice

HITL checkpoints appear at two kinds of moments: **before consequential actions** and **after significant outputs**.

### Checkpoint Type A — Parameter Confirmation (Before)

After loading the parent skill and deriving exam parameters, but before generating questions, the model calls:

```json
{
  "name": "request_human_approval",
  "input": {
    "checkpoint": "exam_params",
    "summary": "I'll generate a 10-question adaptive exam covering arrays, linked lists, and trees. Mix: 4 multiple choice, 4 fill-in, 2 short answer. Starting at medium difficulty. Time limit: 35 min. Does this look right?",
    "params": {
      "question_count": 10,
      "types": ["choice", "fill_blank", "short_answer"],
      "difficulty": "adaptive",
      "time_limit_min": 35,
      "concepts": ["arrays", "linked lists", "trees"]
    }
  }
}
```

The loop **pauses**. The handler surfaces this to the user as a structured prompt. Possible responses:

- **Approved** → `tool_result` returns `{ "approved": true }` → loop continues into question generation.
- **Modified** → user says "make it 15 questions, no essays" → `tool_result` returns `{ "approved": true, "overrides": { "question_count": 15, "types": ["choice", "fill_blank"] } }` → model incorporates changes before loading the subskill.
- **Cancelled** → loop aborts cleanly.

### Checkpoint Type B — Output Review (After)

After `performance-analytics` produces its report, but before the model recommends a follow-up skill, it surfaces:

```json
{
  "name": "request_human_approval",
  "input": {
    "checkpoint": "post_exam_routing",
    "summary": "You scored 75%. Weak areas: tree traversal, graph BFS. I'd suggest moving to memory-comprehension-coach to consolidate these. Want to proceed, pick a different path, or stop here?",
    "options": [
      "→ memory-comprehension-coach (consolidate weak areas)",
      "→ study-guide-creator (full restudy)",
      "→ exam-mode-tuner again (harder test)",
      "Stop here"
    ]
  }
}
```

The user's choice becomes the `tool_result`. The model uses it to decide whether to load a new top-level skill or exit — making cross-skill routing a human decision rather than a fully automated one.

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
├── [R1] load_skill("exam-mode-tuner")            ← parent instructions in context
├── [HITL-A] request_human_approval(exam_params)  ← pause; user confirms or edits
├── [R2] read_file("question-generation/...")     ← subskill loaded on demand
├── [R3–Rn] per-answer loop
│       └── read_file("adaptive-difficulty/...")  ← subskill re-read each iteration
├── [Rn+1] read_file("performance-analytics/...") ← subskill loaded after exam ends
├── [HITL-B] request_human_approval(post_routing) ← pause; user picks next step
└── end_turn → return final output to user
```

Subskills are loaded exactly when needed. Humans are consulted exactly when the stakes warrant it. Neither happens more than necessary.

---

## Context Persistence and Subskill Execution

When a task requires **multiple subskill checks** (e.g. load parent → read subskill A → HITL → read subskill B), context persistence and correct execution behave as follows.

### Within one chat run / tool loop: **yes**

The same `messages` list is reused across rounds. `_run_tool_loop` appends each assistant turn (including `tool_calls`) and each `tool` result to `messages`, then passes that list to the next API call. So multiple subskill reads and tool rounds chain in a single execution without losing context (`backend/app/api/chat.py`, loop around lines 127–201).

### Across HITL pause / resume: **yes**

When the model calls `request_human_approval`, the handler stores the full loop state (including `messages`, `tool_call_id`, `session_id`, `user_id`) via `set_pending` (`backend/app/hitl/store.py`). On `POST /api/ai/chat/hitl-response`, the backend loads that state with `consume_pending`, appends the user’s synthetic tool result to the stored `messages`, and calls `_run_tool_loop` again. Execution resumes from the exact point where it paused (`backend/app/api/chat.py`, ~182–192 for store, ~343–369 for resume).

### Across separate user turns: **limited**

Persisted chat storage (and the history the client sends on the next request) contains only **user and assistant text messages**, not the internal tool trace. Each new user message starts a fresh `messages` list built from the current prompt and the client-provided `history`; the previous turn’s tool-call chain is not replayed. So on a later user turn, the model may need to re-read the top-level skill or subskills to continue correctly (`backend/app/api/chat.py`, e.g. `_complete_chat` building `messages` from a single user content block and `_messages_to_conversation_history` stripping tool messages for fallback).

### Correct execution of subskills: **prompt-guided, not enforced**

The system instructs the model (via `get_agent_context_text`) to load the top-level skill then subskills via `read_file` and not to fabricate subskill outputs or skip checkpoints. There is **no server-side orchestrator** that validates that every required subskill step was actually performed. Long-horizon correctness across turns therefore depends on model behavior unless you add explicit step/state enforcement (`backend/app/context/context_builder.py`, line 53).
