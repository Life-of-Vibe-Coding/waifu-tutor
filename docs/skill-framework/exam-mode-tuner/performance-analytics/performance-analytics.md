---
name: performance-analytics
description: Post-exam analysis by dimension; identify weak concepts, error patterns, and trends; produce personalized improvement path. Called by exam-mode-tuner in step 6.
tags: [analytics, performance, weakness, report, learning-gap]
parent: exam-mode-tuner
---

# Performance Analytics

> Subskill of `exam-mode-tuner` — called in step 6

## When to Use

- Called by `exam-mode-tuner` in step 6 "Post-exam analysis."
- Standalone when the user asks "Show my last exam report."
- Called by `memory-comprehension-coach` to get weak-point data.

## Input

- **answer_records**: Per question:
  - question_id, bloom_level, difficulty, concept, type
  - correct, user_answer, correct_answer
  - time_taken_sec, estimated_time_sec
  - explanation_given
- **exam_metadata**: Count, time limit, scope, etc.
- **history** (optional): Prior tests for trend comparison.

## Steps

### 1. Basic Stats

```yaml
basic_stats:
  total_questions: 15
  correct: 10
  incorrect: 5
  accuracy: 0.667
  total_time_min: 28
  avg_time_per_question_sec: 112
  time_utilization: 0.93
```

### 2. Scores by Dimension

**By concept**:
```yaml
concept_scores:
  - concept: "Array operations"
    correct: 3
    total: 3
    accuracy: 1.0
    status: mastered
  - concept: "Tree traversal"
    correct: 0
    total: 2
    accuracy: 0.0
    status: critical_gap
  - concept: "Graph shortest path"
    correct: 0
    total: 1
    accuracy: 0.0
    status: gap
  - concept: "Sorting"
    correct: 2
    total: 3
    accuracy: 0.67
    status: developing
```

**By Bloom**:
```yaml
bloom_scores:
  L1_remember: { correct: 3, total: 3, accuracy: 1.0 }
  L2_understand: { correct: 3, total: 4, accuracy: 0.75 }
  L3_apply: { correct: 3, total: 4, accuracy: 0.75 }
  L4_analyze: { correct: 1, total: 3, accuracy: 0.33 }
  L5_evaluate: { correct: 0, total: 1, accuracy: 0.0 }
```

**By question type**:
```yaml
type_scores:
  choice: { correct: 4, total: 5, accuracy: 0.8 }
  fill_blank: { correct: 3, total: 5, accuracy: 0.6 }
  short_answer: { correct: 3, total: 5, accuracy: 0.6 }
```

### 3. Error Pattern Analysis

**Misconception detection**:
- Look for shared misunderstanding in wrong answers
- E.g., "Chose O(n) option 3 times when answer was O(nlogn) → possible confusion about divide-and-conquer complexity"

**Error type**:
| Type | Description | Suggestion |
|---|---|---|
| **Concept confusion** | Similar concepts mixed (e.g., stack vs queue) | `→ memory-comprehension-coach` contrast |
| **Calculation error** | Right method, wrong computation | More practice, focus on detail |
| **Wrong method** | Method doesn’t fit problem | Review when to use which method |
| **Understanding gap** | Concept not fully understood | `→ memory-comprehension-coach` |
| **Misread** | Missed condition or requirement | Highlight key conditions before solving |
| **Time** | No answer but others correct | Improve pacing / time allocation |

### 4. Time Efficiency

```yaml
time_analysis:
  fast_correct: 6
  fast_incorrect: 1
  slow_correct: 4
  slow_incorrect: 4

  slowest_questions:
    - question_id: "q007"
      concept: "AVL rotation"
      time_sec: 300
      correct: false
      insight: "Concept may be unfamiliar"
```

### 5. Trend (if history exists)

```yaml
trend:
  tests_compared: 3
  accuracy_trend: [0.45, 0.60, 0.667]
  improving_concepts: ["Linked list", "Sorting"]
  stagnant_concepts: ["Tree traversal"]
  new_gaps: ["Graph shortest path"]
  message: "Overall improving; tree traversal failed 3 times—consider a different strategy."
```

### 6. Personalized Next Steps

From the analysis, output concrete actions:

```yaml
action_plan:
  priority: high
  immediate_actions:
    - action: "Deepen: tree traversal"
      skill: "→ memory-comprehension-coach"
      params: { goal: understand, concepts: ["Preorder", "Inorder", "Postorder", "Level order"] }
      reason: "Failed 3 times; try different strategy (e.g., Feynman)"
    - action: "Review: sorting complexity"
      skill: "→ memory-comprehension-coach"
      params: { goal: memorize, strategy: spaced_repetition }
      reason: "Errors from concept confusion; contrast and consolidate"

  next_test:
    recommended_timing: "In 3 days"
    focus: ["Tree traversal", "Graph shortest path"]
    question_count: 8
    difficulty: adaptive
```

## Output

Full report in a user-friendly format:

- Total score + grade (e.g., A/B/C/D/F)
- Concept-level summary (text or simple “radar” description)
- Weak areas + concrete suggestions
- Trend (if available)
- Next-step list with skill references

## Errors and Boundaries

- **Too few questions** (< 5): Only basic stats; skip pattern analysis (sample too small).
- **User discouraged** (repeated low scores): Use encouraging tone; emphasize what improved; soften criticism.
- **No history**: Skip trend; note "First test; we can track trends from here."
