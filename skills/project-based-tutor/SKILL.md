---
name: project-based-tutor
description: Guide learning through real projects; embed concepts in hands-on work; design stepwise projects, give scaffolded guidance, and review milestones. Use when the user asks to "learn by project," "learn by doing," or "practice with a project."
tags: [project, hands-on, practice, learning-by-doing, tutor, applied, scaffolding]
subskills:
  - project-design
  - scaffolded-guidance
  - milestone-review
---

# Project-Based Tutor

## When to Use

- User says "I've had enough theory, I want to practice," "Any project I can do?" "How do I use what I learned?"
- User wants to solidify theory through practice, not more reading.
- User is learning programming, engineering, design, data analysis, or other applied topics.
- User wants guided project steps, not just a single task.
- Recommended by `→ exam-mode-tuner`'s performance-analytics when the user is ready for application.
- Recommended by `→ study-guide-creator` when a module is "suitable for hands-on."

## Steps

### 1. Assess Readiness

- Check learning history:
  - Documents (`viking://resources/users/{user_id}/documents/`)
  - Exam results (from `→ exam-mode-tuner` performance-analytics)
  - Conversation and long-term memory (`viking://user/memories`)
- Decide suitable project difficulty and type
- Identify gaps: if prerequisites are missing:
  - Small gap (1–2 concepts): Explain in the project
  - Large gap (whole module): Suggest `→ study-guide-creator` first

### 2. Project Design → `project-design`

Call subskill `→ project-design/project-design.md` to:
- Design a full project from subject, concepts, and user level
- Define a clear deliverable (code / report / prototype / analysis / paper)
- Split into 3–7 milestones, each with 1–2 core concepts
- Set acceptance criteria (DoD) per milestone
- Output: project plan + milestone list + concept mapping

### 3. Stepwise Guidance → `scaffolded-guidance`

For each milestone, call subskill `→ scaffolded-guidance/scaffolded-guidance.md`:
- Use Vygotsky ZPD: scaffold only as much as needed
- Four levels: direction hint → concept hint → step hint → full demo
- Guide the user to think; don’t give the answer directly
- Adjust scaffolding from how the user does

### 4. Milestone Review → `milestone-review`

After each milestone, call subskill `→ milestone-review/milestone-review.md`:
- Review the user’s deliverable (code / text / design / data)
- Give feedback on correctness, quality, and creativity
- Use sandwich feedback (strength → improvement → encouragement)
- Tie back to theory ("You just used the observer pattern")

### 5. Recap and Link to Theory

After each milestone:
- Recap concepts used
- Link practice to theory ("That step corresponds to chapter X, concept Y")
- Note Bloom level change (e.g., from L2 understand to L3 apply)
- Optional: 1–2 quiz questions to check retention → `→ exam-mode-tuner`

### 6. Project Wrap-up

Final recap:

```
📋 Project recap
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Project: Movie dataset analysis
⏱️ Total time: ~4h (5 milestones)

📚 Concepts used:
   ✅ Pandas load & explore (Bloom L3 → L4)
   ✅ Data cleaning: missing values, types (L2 → L3)
   ✅ GroupBy aggregation (L2 → L4)
   ✅ Matplotlib visualization (L2 → L3)
   ✅ Writing analysis (L3 → L5)

💡 Takeaways:
   1. Cleaning often takes 60–80% of analysis time
   2. Visualization is for discovery, not just display
   3. Conclusions need to be backed by data

🚀 Next steps:
   - Add a prediction module → project-based-tutor (advanced)
   - Write a formal report → writing-coach
   - Test mastery with a quiz → exam-mode-tuner
```

## Input

- **Subject/topic**: What the user is learning.
- **Document** (optional): Related material ID.
- **Optional**:
  - `difficulty`: beginner / intermediate / advanced
  - `project_type`: coding / analysis / design / writing / research / engineering
  - `time_estimate`: e.g. "2 hours," "one week"
  - `tools`: e.g. "Python + Jupyter," "React + TypeScript"
  - `learning_goals`: Specific concepts to practice
  - `output_format`: code / report / presentation / prototype

## Output

- **Project summary**: Goal, deliverable, concepts, estimated time.
- **Milestone list**: Goal, concepts, acceptance criteria, time per milestone.
- **Stepwise guidance**: Scaffolded help per milestone (on demand).
- **Milestone feedback**: Review of each deliverable.
- **Wrap-up**: Concept recap, Bloom change, next-step suggestions.

## Subskill References

| Subskill | Path | When to call |
|---|---|---|
| project-design | `./project-design/project-design.md` | Step 2: Design project and milestones |
| scaffolded-guidance | `./scaffolded-guidance/scaffolded-guidance.md` | Step 3: Guide each milestone |
| milestone-review | `./milestone-review/milestone-review.md` | Step 4: Review deliverables |

## External Skill Linkage

| Trigger | Target skill | Note |
|---|---|---|
| Prerequisites missing | `→ study-guide-creator` | Build foundation first |
| Milestone deliverable is writing | `→ writing-coach` | Guide report/essay |
| Check mastery after milestone | `→ exam-mode-tuner` | Short quiz |
| Stuck on a concept | `→ memory-comprehension-coach` | Deepen understanding |
| Project involves argument/decision | `→ debate-roleplay-learning` | Practice argumentation |

## Errors and Boundaries

- **Weak foundation**: Simplify the project or recommend `→ study-guide-creator` first; don’t push when basics are missing.
- **Stuck for 3+ hint rounds**: Give full demo + walkthrough (scaffolded-guidance level 4) so the user doesn’t quit.
- **Scope too large**: Propose splitting into smaller projects; do an MVP first.
- **Non-applied subject** (e.g., history, philosophy): Use projects like research report, case analysis, or argumentative essay (link `→ writing-coach`).
- **Tool/environment issues**: Design for the user’s tools; avoid requiring complex setup.
- **User skips a milestone**: Allow it but note possible missed concepts and mark "to review later."

## Example

**User**: "I’ve learned basic Pandas. I want a project; I have 3–4 hours."

**Agent**:
1. Assess: User has Pandas basics (read, index, filter); lacks practice.
2. Call `→ project-design`: "Movie dataset analysis — from cleaning to visualization and insights."
3. Split into 5 milestones, ~3.5h total.
4. Guide with `→ scaffolded-guidance`, e.g. hint: "Try `df.isnull().sum()`."
5. After each milestone, run `→ milestone-review`.
6. At the end: recap concepts and suggest a follow-up project or report.
