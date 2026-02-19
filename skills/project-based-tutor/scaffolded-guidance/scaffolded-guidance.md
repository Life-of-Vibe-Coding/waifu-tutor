---
name: scaffolded-guidance
description: Provide 4-level progressive hints (direction → concept → steps → full demo) based on ZPD, so the user can complete milestones without being given the answer. Called by project-based-tutor in step 3.
tags: [scaffolding, ZPD, hint, guidance, progressive, socratic]
parent: project-based-tutor
---

# Scaffolded Guidance

> Subskill of `project-based-tutor` — called in step 3

## When to Use

- Called by `project-based-tutor` in step 3 to guide each milestone.
- When the user is stuck in any learning task (not only projects).

## Input

- **milestone**: Full description (goal, concepts, acceptance criteria).
- **user_state**: starting / stuck / partial / wrong_direction.
- **attempt_count**: How many hints or attempts so far for this milestone.
- **user_submission** (optional): Current code/text/artifact.

## Steps

### 1. Diagnose User State

| Difficulty | Signal | Strategy |
|---|---|---|
| **Don’t know how to start** | "I don’t know where to start," "What’s the first step?" | Level 1: Direction |
| **Concept gap** | Code or text shows misunderstanding | Quick explain via `→ memory-comprehension-coach`, then back to hints |
| **Uncertain method** | Knows goal but not which function/approach | Level 2: Concept |
| **Implementation issue** | Direction right but code/writing wrong | Level 3: Steps |
| **Completely stuck** | Still stuck after several tries | Level 4: Full demo |

### 2. Four-Level Hint System

**Level 1 — Direction**
- No specific method; only direction and framing
- Example: "This step is about missing values. Which columns have missing data? Should you drop or fill? What does it depend on?"
- Use when: user is just starting

**Level 2 — Concept**
- Name the concept/tool, not the exact code
- Example: "Pandas has `.fillna()` and `.dropna()` for missing values. What’s the difference? Which fits your data?"
- Use when: user knows the goal but not the tool

**Level 3 — Steps**
- Give ordered steps; user still writes/does it
- Example:
  ```
  1. Use df.isnull().sum() to see missing per column
  2. For numeric columns, fill with median (why not mean? think outliers)
  3. For categorical, fill with mode
  4. Check again that nothing is left missing
  ```
- Use when: user tried but implementation is off

**Level 4 — Full demo**
- Complete solution + brief explanation
- Use only after 1–3 didn’t work
- After demo: 1) User redoes without looking  2) User explains why each part
- Example:
  ```python
  # Check missing
  print(df.isnull().sum())
  # sum() not any() — we need how many, not just whether

  # Fill numeric with median (more robust than mean)
  df['revenue'].fillna(df['revenue'].median(), inplace=True)
  ```
- Use when: user still can’t complete after multiple tries

### 3. Adjust Scaffolding Over Time

From the user’s performance across milestones:

```
if first 2 milestones done with Level 1 only:
    start next at Level 1 (or even just the goal)
elif first 2 needed Level 3:
    start next at Level 2
    consider → study-guide-creator for basics
```

**Fading**: Reduce hint level as the project goes on; aim for the last 1–2 milestones with Level 1 or no hint. Note when they complete something on their own.

### 4. Prefer Questions Over Statements

| Avoid | Prefer |
|---|---|
| "You should use .groupby()" | "If you want to group by year, Pandas has a function for that—which one?" |
| "There’s a bug; it should be X" | "Run it and look at the output. Does it match what you expected? Where not?" |
| "The answer is 42" | "What do you think the value should be? Why?" |

### 5. Encouragement

- **Doing well**: "You’re getting faster; this milestone was quicker than the last."
- **Stuck but trying**: "You’re on the right track; here’s a small hint."
- **Wanting to give up**: "This part is tough. See the full solution, understand it, then try again yourself."
- **Never asking for help**: Check in: "How’s it going? Want me to look at what you have?"

## Output

```yaml
guidance:
  milestone_id: M2
  hint_level: 2
  content: |
    For missing values you can:
    - Drop: df.dropna() — but you lose rows
    - Fill: df.fillna(value) — value can be constant, mean, median

    Your "rating" column has 200 missing rows. Dropping them would lose 4% of data.
    Drop or fill? If fill, what value makes sense?

  next_if_stuck: 3
  encouragement: "Your data loading was solid; cleaning is the natural next step."
```

## Errors and Boundaries

- **User asks for the full answer**: Explain why trying first helps; if they insist, give Level 4 but ask them to explain afterward.
- **Creative but wrong direction**: Acknowledge the idea, then steer back.
- **User level above project**: Reduce scaffolding; step in only when needed.
