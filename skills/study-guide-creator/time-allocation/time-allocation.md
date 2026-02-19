---
name: time-allocation
description: Generate a dated study calendar and daily task list from module weights, difficulty, and available time. Called by study-guide-creator in step 6.
tags: [time, scheduling, planning, calendar, study-plan]
parent: study-guide-creator
---

# Time Allocation

> Subskill of `study-guide-creator` — called in step 6

## When to Use

- Called by `study-guide-creator` in step 6 "Time planning."
- When the user provides `time_budget` (total time) or `exam_date` (deadline).
- Standalone: user says "Plan my study schedule for the next week."

## Input

- **modules**: List with `name`, `importance_weight`, `difficulty`, `concept_count`, `depends_on`.
- **time_budget**: Total time (hours or days).
- **exam_date** (optional): Deadline.
- **daily_capacity** (optional): Time per day; default from `time_budget / days`, cap e.g. 4h/day to avoid overload.
- **user_preferences** (optional): Preferred time of day, rest days.
- **prior_knowledge** (optional): Already mastered modules (allocate 0 or review only).

## Steps

### 1. Raw Time Weights

Per module:

```
raw_weight(m) = importance_weight(m) × difficulty_factor(m) × concept_count_factor(m)
```

- `difficulty_factor`: basic=1.0, intermediate=1.5, challenge=2.0
- `concept_count_factor`: max(1.0, concept_count / 3)
- Mastered modules: raw_weight = 0.15 (review only)

### 2. Normalize and Allocate

```
allocated_hours(m) = (raw_weight(m) / sum(raw_weights)) × usable_time
usable_time = time_budget × 0.85   # 15% buffer
```

Constraints:
- Minimum 30 min per module
- No single module > 35% of total (avoid imbalance)
- Redistribute if constraints are violated

### 3. Calendar Placement

Place modules on the calendar by dependency order and daily capacity:

**Rules**:
- Respect prerequisites: prerequisite before dependent
- Daily total ≤ daily_capacity (default ≤ 4h)
- At most 2 new modules per day
- Put harder modules in high-energy slots (e.g., morning)
- Lighter or review in low-energy slots

**Review points** (spaced repetition):
- Day after module: 15 min quick review
- 3 days after: 10 min self-test (e.g., short quiz via `→ exam-mode-tuner`)
- After all modules: 2h full practice (e.g., mock exam via `→ exam-mode-tuner`)

### 4. Daily Task List

Format per day:

```
📅 Day 3 (Wed) — ~2.5h
━━━━━━━━━━━━━━━━━━━━━━━━
📖 [New] Module 2: Memory management (1.5h)
   • Read: Virtual memory, address translation
   • Practice: 3 page-table calculation problems
   • Goal: Explain how virtual address maps to physical

🔄 [Review] Module 1: Process management (30min)
   • Self-test: List 5 process states without notes
   • Flashcards: Review 8 cards from yesterday

💪 [Challenge] (30min)
   • If a process is waiting for I/O, can its pages be swapped out?
```

### 5. Flexibility

- **Behind**: Identify low-priority modules; shrink their time and reschedule.
- **Ahead**: Add depth or start next module early.
- **Module takes longer**: Use buffer; if buffer gone, suggest "Focus on core 60% of this module."
- **User skips a day**: Reschedule without blame.

## Output

```yaml
schedule:
  total_days: 7
  total_hours: 15
  buffer_hours: 2.25
  daily_plans:
    - day: 1
      date: "2025-03-10 (Mon)"
      sessions:
        - type: new
          module: "Process management"
          duration_min: 120
          tasks: ["Read process concepts", "3 scheduling-algorithm problems"]
          goal: "Compare FCFS / SJF / RR"
    - day: 4
      date: "2025-03-13 (Thu)"
      sessions:
        - type: review
          module: "Process management"
          duration_min: 20
          tasks: ["Self-test: list 5 process states"]
        - type: new
          module: "Deadlock"
          duration_min: 90
          tasks: ["Read four conditions", "Banker's algorithm example"]
  review_nodes:
    - day: 2
      modules: ["Process management"]
      method: "Self-test + flashcards"
    - day: 7
      modules: ["All"]
      method: "Mock exam"
      skill_ref: "→ exam-mode-tuner"
```

## Errors and Boundaries

- **Very little time** (e.g., 3h for a full course): Say coverage is impossible; output "Emergency exam strategy"—top 30% by importance only; skip derivations and detail.
- **No deadline**: Schedule at a comfortable 1–2h/day; no forced end date.
- **Variable daily time**: Ask for daily availability and allocate unevenly if needed.
