---
name: spaced-repetition-scheduler
description: Based on Ebbinghaus curve and an SM-2–style algorithm, compute next review time and format from each review; called by memory-comprehension-coach in step 6.
tags: [spaced-repetition, scheduling, ebbinghaus, SM-2, forgetting-curve, flashcard]
parent: memory-comprehension-coach
---

# Spaced Repetition Scheduler

> Subskill of `memory-comprehension-coach` — called in step 6

## When to Use

- Called by `memory-comprehension-coach` in step 6 "Schedule review."
- Referenced by `study-guide-creator/time-allocation` for review nodes.
- When the user asks "When should I review?" or "Plan my review."

## Input

- **concepts**: List of concepts to schedule, each with:
  - name
  - mastery_level (1–5)
  - knowledge_type
  - last_review_date (optional)
  - review_history (optional)
- **user_schedule** (optional): Daily time available for review.
- **priority** (optional): Concept priority from `study-guide-creator`.

## Steps

### 1. Initial Interval

SM-2–style initial interval by mastery:

| Mastery | First interval | Rationale |
|---|---|---|
| Level 1 | 4 hours | No recall → same-day review |
| Level 2 | 1 day | Vague → overnight consolidation |
| Level 3 | 2 days | Can recall → slightly longer |
| Level 4 | 4 days | Can apply → longer |
| Level 5 | 7 days | Deep → mainly check retention |

### 2. Interval Growth

After each successful review:

```
next_interval = previous_interval × ease_factor

ease_factor from review quality (user or system):
  quality = 5 (perfect)     → ease_factor = 2.5
  quality = 4 (hesitant but right) → ease_factor = 2.0
  quality = 3 (hard but right)     → ease_factor = 1.5
  quality = 2 (wrong but close)    → ease_factor = 1.0
  quality = 1 (forgot)            → ease_factor = 0.5
  quality = 0 (don't recognize)   → reset to initial
```

**Limits**:
- Min interval: 4 hours
- Max interval: 90 days (then "maintenance": every 90 days)
- 3 reviews in a row with quality ≤ 2 → mark "needs relearn" and return to memory-comprehension-coach steps 4–5

### 3. Review Format by Interval

Vary format by interval to keep engagement:

| Interval | Format | Time | Note |
|---|---|---|---|
| First (< 1 day) | Active recall | 2 min | "Without notes, state the definition of X" |
| Short (1–3 days) | Flashcards | 1 min/card | Question → answer in head → flip |
| Medium (4–14 days) | Self-test | 5 min | 2–3 questions (→ exam-mode-tuner) |
| Long (15–30 days) | Feynman recap | 3 min | "Explain in one sentence" |
| Maintenance (30–90 days) | Application | 5 min | Use concept in a new scenario |

### 4. Multi-Concept Scheduling

When several concepts need review:

**Rules**:
- Daily review time ≤ user capacity (default 15 min)
- At most 5 concepts per day
- Higher priority first
- If a day is full, shift lower priority by 1 day (mark "delayed")
- First review for new concepts is never delayed (steepest forgetting)

**Interleaving**:
- Similar concepts on the same day (e.g., stack and queue) when it helps
- Don’t do the same type back-to-back; alternate

### 5. Review Calendar

```yaml
review_calendar:
  concepts_tracked: 5
  total_days: 30

  schedule:
    - date: "2025-03-11 (Tue)"
      reviews:
        - concept: "Eigenvalue definition"
          form: "Active recall"
          time: 2min
          mastery_at_schedule: 2
        - concept: "Matrix multiplication"
          form: "Flashcards ×3"
          time: 3min
          mastery_at_schedule: 3
      total_time: 5min

    - date: "2025-03-13 (Thu)"
      reviews:
        - concept: "Eigenvalue definition"
          form: "Flashcards ×2"
          time: 2min
        - concept: "Determinant"
          form: "Self-test ×2"
          time: 5min
          skill_ref: "→ exam-mode-tuner"
      total_time: 7min

    - date: "2025-03-18 (Tue)"
      reviews:
        - concept: "Eigenvalue definition"
          form: "Feynman recap"
          time: 3min
          prompt: "Explain eigenvalue in one sentence"
        - concept: "Eigenvalue computation"
          form: "Practice ×2"
          time: 5min
      total_time: 8min

    - date: "2025-03-25 (Tue)"
      reviews:
        - concept: "Eigenvalues and PCA"
          form: "Application"
          time: 5min
          prompt: "Why does PCA use largest eigenvalues?"
      total_time: 5min

  milestones:
    - day: 7
      checkpoint: "Mid-point check"
      action: "→ exam-mode-tuner: 5 linear algebra questions"
    - day: 30
      checkpoint: "Monthly check"
      action: "→ exam-mode-tuner: 10 questions for retention"

  adaptive_notes: |
    If 3/11 active recall fails → shorten next to 1 day (3/12)
    If 3/18 Feynman goes well → lengthen next to 14 days
```

### 6. Update After Each Review

```
AFTER each review:
  record(concept, date, quality, time_taken)

  IF quality >= 4:
    next_interval *= ease_factor
    IF consecutive_successes >= 3:
      form = upgrade(current_form)

  ELIF quality == 3:
    next_interval *= 1.0

  ELIF quality <= 2:
    next_interval *= 0.5
    IF consecutive_failures >= 2:
      trigger → memory-comprehension-coach
      reset interval to initial

  reschedule_remaining(calendar)
```

## Output

- **review_calendar**: Dates, formats, and durations.
- **daily_reminders**: What to review each day and estimated time.
- **milestone_checkpoints**: When to run a short quiz or check.
- **adaptive_rules**: When to shorten/lengthen or change format.

## Errors and Boundaries

- **User skips many days**: Don’t punish. Re-diagnose mastery (`→ mastery-diagnosis`) and reschedule from current level.
- **Too many concepts** (> 20): Prioritize; schedule only high priority or near-forgetting; put the rest on hold.
- **Very little time** (< 5 min/day): Schedule only top priority; use shortest format (1 min flashcard per concept).
- **All concepts at Level 5**: Switch to maintenance (e.g., every 30–90 days) and free time for new content.
