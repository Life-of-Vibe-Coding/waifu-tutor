---
name: milestone-review
description: Review the user's deliverable for each milestone (code/text/design); give multi-dimensional constructive feedback and link to theory. Called by project-based-tutor in step 4.
tags: [review, feedback, code-review, quality, constructive]
parent: project-based-tutor
---

# Milestone Review

> Subskill of `project-based-tutor` — called in step 4

## When to Use

- Called by `project-based-tutor` in step 4 after each milestone.
- When the user submits code, text, or any deliverable and asks for feedback.

## Input

- **milestone**: Description and acceptance criteria.
- **submission**: User’s deliverable (code/text/screenshot/description).
- **submission_type**: code / text / design / data_analysis / other.
- **hint_history**: Hint levels and count used for this milestone.

## Steps

### 1. Check Acceptance Criteria

Go through each criterion:

```yaml
acceptance_check:
  - criterion: "Load data with pd.read_csv()"
    status: pass
    evidence: "Line 3 correctly calls pd.read_csv('movies.csv')"
  - criterion: "State row and column count"
    status: pass
    evidence: "User used df.shape and reported (5043, 28)"
  - criterion: "Identify at least 2 data quality issues"
    status: partial
    evidence: "Noted missing values but not duplicates"
    suggestion: "Try df.duplicated().sum() for duplicates"
```

### 2. Multi-Dimensional Review

**Code**:
| Dimension | Check | Example feedback |
|---|---|---|
| **Correctness** | Runs and output is right | "Line 7 filter is missing a parenthesis" |
| **Readability** | Names, comments, structure | "Rename `x` to `avg_rating`" |
| **Efficiency** | Obvious performance issues | "Looping over DataFrame is slow; use .apply() or vectorized ops" |
| **Style** | Idioms and best practices | "Chained Pandas calls are more Pythonic than step-by-step" |
| **Robustness** | Edge cases | "What if the file is missing? Consider try/except" |

**Text/analysis**:
| Dimension | Check |
|---|---|
| **Accuracy** | Data interpretation correct |
| **Completeness** | All required aspects covered |
| **Depth** | Explains why, not only what |
| **Clarity** | Conclusions are clear and logical |

### 3. Sandwich Feedback

```
✅ Strengths:
  • Data loading and exploration are clear and concise
  • Using .describe() for a quick summary is good practice

⚠️ Improvements:
  🔴 [Must] Line 12 df.dropna() drops any row with any missing value—you went from 5043 to 3000 rows (40% lost). Prefer handling by column.
  🟡 [Suggest] Rename `df2` to something like `df_cleaned`.
  🟢 [Nice] Add a short comment on why median instead of mean for fill.

💪 Overall:
  Milestone ~85% complete. Fix the cleaning strategy and you’re there. You needed fewer hints than last time!
```

### 4. Link to Theory

Connect what they did to concepts:

```
📚 Concepts:
  • df.groupby('genre').mean() is "grouped aggregation"
    → Textbook ch.5 GroupBy
    → Bloom: you moved from "understand" (L2) to "apply" (L3)

  • Choosing median over mean for missing values
    → Robust statistics: median less sensitive to outliers
    → Textbook ch.2 "Choosing descriptive statistics"
```

### 5. Next Step

```yaml
next_steps:
  if_pass:
    message: "Milestone passed. Ready for the next?"
    next_milestone: M3
  if_partial:
    message: "Almost there. Fix the 🔴 items and resubmit?"
    fixes_needed: ["Cleaning strategy"]
  if_fail:
    message: "Core part needs change. Want a stronger hint?"
    escalate_to: "scaffolded-guidance Level 3"
```

## Output

- Acceptance check (pass / partial / fail per criterion)
- Multi-dimensional feedback
- Sandwich feedback text
- Theory links
- Next-step message

## Errors and Boundaries

- **Incomplete submission** (e.g., only part of the code): Review what’s there and point out what’s missing.
- **Likely not original** (e.g., copy from web): Don’t accuse; ask them to explain the solution—understanding matters more than completion.
- **User upset by feedback**: Use gentler wording; keep sandwich; shift toward more praise.
