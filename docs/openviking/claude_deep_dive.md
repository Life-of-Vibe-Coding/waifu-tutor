# OpenViking — Deep Dive into Core URI Paths

OpenViking (open-sourced by ByteDance's Volcengine Viking Team in January 2026) is a **context database for AI Agents**, built on a virtual filesystem abstraction. Everything is addressed with a `viking://` URI. The entire context space is divided into three top-level namespaces: `agent/`, `user/`, and `resources/`. Here is a detailed explanation of each path.

---

## The Virtual Filesystem at a Glance

```
viking://
├── resources/          ← External knowledge ingested into the system
├── user/
│   └── memories/       ← What the system knows about the user
└── agent/
    ├── instructions/   ← Static behavioral rules for the Agent
    ├── memories/       ← The Agent's accumulated task experience
    └── skills/         ← Reusable, named capabilities
```

Everything stored under these paths is automatically processed into **three context layers**:

- **L0 (Abstract)** — one-sentence summary, used for vector retrieval and quick filtering
- **L1 (Overview)** — core information and usage scenarios, loaded during the Agent's planning phase
- **L2 (Details)** — the full content, fetched on demand during deep execution

This means the Agent never blindly dumps all context into a prompt — it retrieves progressively, keeping token costs low.

---

## `viking://agent/instructions`

**What it is:** The Agent's static behavioral rulebook.

This directory holds text-based rules, role definitions, task constraints, tone guidelines, and any fixed directives that should govern how the Agent always behaves — regardless of the session or user. Think of it as the equivalent of a system prompt, but stored and versioned in the filesystem, making it auditable and editable without changing code.

**Characteristics:**
- Developer-authored, not auto-updated by the memory system.
- Loaded eagerly or near-eagerly by the Agent at the start of each session because instructions are high-priority, stable context.
- Supports subdirectories so you can organize by category (e.g., `instructions/safety`, `instructions/persona`, `instructions/output-format`).
- Each file (or subdirectory) gets its own L0/L1/L2 layers, so even instructions are hierarchically browsable.

**Example use cases:** "Always respond in English," "Never reveal internal tool names," "Act as a senior software engineer specializing in Python," task-specific workflow rules.

---

## `viking://agent/memories`

**What it is:** The Agent's accumulated operational experience from past tasks.

Unlike user memories, this directory captures what the Agent itself has learned through doing — tool usage patterns, common failure modes, operational tips, workflow shortcuts, and task execution insights. This is what makes an Agent "smarter with use" over time.

**How it is populated:**
At the end of each session, developers can trigger the **memory extraction mechanism**. The system asynchronously analyzes the session's task execution results and automatically distills key learnings into `agent/memories`. Concrete examples include: "Using tool X before tool Y yields better results for file conversion tasks," "Search queries narrower than 5 words consistently return higher-quality results."

**Characteristics:**
- Auto-evolved by the system's memory self-iteration loop (not manually written by developers in normal operation).
- Organized into subdirectories based on topic or task type (e.g., `agent/memories/code_analysis`, `agent/memories/data_extraction`).
- Retrieved semantically during task planning: the Agent finds relevant past experience and incorporates it into current decisions.
- Distinct from `user/memories` — agent memories are about *how the Agent operates*, not about *who the user is*.

---

## `viking://agent/skills`

**What it is:** A library of reusable, named capabilities the Agent can look up and execute.

Each skill is a named entry under this directory — essentially a stored procedure or a documented capability the Agent knows how to invoke. Skills can include descriptions of multi-step processes, tool usage sequences, code templates, or domain-specific workflows (e.g., "how to search a codebase," "how to analyze tabular data," "how to draft and send a report").

**Characteristics:**
- Stored as structured documents with their own L0/L1/L2 layers — so the Agent can do a quick L0 lookup to decide whether a skill is relevant before loading its full L2 details.
- The Agent can browse `agent/skills/` using `ls` and `find` commands to discover what capabilities are available.
- Supports semantic retrieval: when given a task, the Agent can query `agent/skills` for the closest matching skill and follow its stored procedure.
- Skills are typically developer-authored upfront but can theoretically be added or refined as part of the Agent's self-evolution.

**Example entries:** `agent/skills/search_code`, `agent/skills/analyze_data`, `agent/skills/generate_report`, `agent/skills/browser_navigation`.

This is different from function/tool definitions in LLM tool-use APIs — skills are richer, semantically searchable, human-readable procedures stored as context, not runtime-registered callables.

---

## `viking://resources`

**What it is:** The Agent's external knowledge base — anything the Agent needs to know about the world or a project.

This is the most general-purpose namespace. Any file, URL, directory, GitHub repository, web page, PDF, or codebase that the Agent needs to reference is ingested here via `client.add_resource(path=...)`. The system then parses it, structures it into a virtual directory tree, and generates L0/L1/L2 layers for every node.

**Characteristics:**
- Supports a wide range of source types: local files and directories, remote URLs, documentation sites, code repositories.
- The virtual directory mirrors the original source structure (e.g., ingesting a GitHub repo produces subdirectories for `docs/`, `src/`, etc.).
- Every directory and file in the tree has a `.abstract` and `.overview` file auto-generated at ingest time by the VLM.
- Retrieval is done via **Directory Recursive Retrieval**: the Agent first locates the highest-scoring directory using vector search on abstracts, then drills down recursively to find the exact content.
- Resources are read-only from the Agent's perspective — they represent external ground truth, not evolving Agent state.

**Example structure after ingesting a project:**

```
viking://resources/my_project/
├── .abstract
├── .overview
├── docs/
│   ├── .abstract
│   ├── api/
│   │   ├── auth.md
│   │   └── endpoints.md
│   └── tutorials/
└── src/
```

---

## `viking://session`

**What it is:** The live, ephemeral conversation context for an ongoing Agent session.

The `session` namespace holds the current conversation history — the sequence of user messages, Agent responses, tool calls, tool results, and intermediate reasoning artifacts generated during a single task run. It is the Agent's working memory for the current interaction.

**Characteristics:**
- Managed automatically by OpenViking's built-in session management layer (the `openviking/session/` module in the codebase).
- As the session grows, the system automatically compresses earlier parts of the conversation: content, resource references, and tool call results are summarized so the active context window stays manageable without losing critical information.
- At session end, the session's content is the primary input to the **memory extraction loop** — the system analyzes what happened and distills learnings into `agent/memories` and `user/memories`.
- This enables the "smarter with use" self-evolution property: every completed session feeds back into persistent long-term context.
- Developers trigger session close/extraction explicitly via the API, giving them control over when memory consolidation happens.

---

## `viking://user/memories`

**What it is:** A persistent, evolving profile of the user — their preferences, habits, and working style.

This namespace stores everything the Agent learns about the specific person it is working with: communication style preferences, coding language preferences, output format preferences, domain expertise, past decisions, recurring patterns, and personal context that makes the Agent's responses more tailored over time.

**How it is populated:**
Like agent memories, user memories are extracted automatically at session end. The memory extraction mechanism analyzes the session, identifies user-specific signals (expressed preferences, corrections the user made, style feedback, explicit statements), and updates the relevant subdirectories.

**Characteristics:**
- Persists across sessions — user memories accumulate over the lifetime of the Agent-user relationship.
- Organized into meaningful subdirectories: e.g., `user/memories/preferences/writing_style`, `user/memories/preferences/coding_habits`, `user/memories/background/domain_expertise`.
- Semantically retrieved at the start of sessions or during task planning to personalize responses.
- Distinct from `agent/memories` — user memories answer "who is this person and how do they like to work?", while agent memories answer "what has this Agent learned about doing its job well?"

**Example stored memories:** "User prefers concise bullet-point summaries," "User works primarily in Python and dislikes Java examples," "User is a senior ML engineer; explanations should skip basic concepts."

---

## Summary Table

| Path | Type | Authored By | Evolves Via | Purpose |
|---|---|---|---|---|
| `viking://agent/instructions` | Static rules | Developer | Manual edits | Behavioral guidelines, persona, constraints |
| `viking://agent/memories` | Evolving experience | System (auto-extracted) | Session end | Agent's operational know-how |
| `viking://agent/skills` | Capability library | Developer + system | Manual / auto | Reusable named procedures |
| `viking://resources` | External knowledge | Developer (via `add_resource`) | Re-ingestion | Project docs, URLs, codebases |
| `viking://session` | Live conversation | System (auto-managed) | Real-time | Current working context window |
| `viking://user/memories` | User profile | System (auto-extracted) | Session end | User preferences and habits |

---

> **Key Design Insight:** All six paths share the same filesystem interface (`ls`, `find`, `read`, `abstract`, `overview`) and the same L0/L1/L2 layered loading model — so the Agent interacts with all types of context using a single, uniform paradigm rather than six different APIs.
