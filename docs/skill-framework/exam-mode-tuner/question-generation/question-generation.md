---
name: question-generation
description: Generate high-quality questions from documents/concepts by Bloom level and question type, with balanced concept coverage and difficulty. Called by exam-mode-tuner in step 2.
tags: [question, generation, bloom, taxonomy, quiz, assessment]
parent: exam-mode-tuner
---

# Question Generation

> Subskill of `exam-mode-tuner` — called in step 2

## When to Use

- Called by `exam-mode-tuner` in step 2 "Question generation."
- Called by `memory-comprehension-coach` for review self-tests.
- When batch practice questions are needed for specific concepts.

## Input

- **knowledge_source**: One of:
  - Document ID → fetch content
  - concept_list → from `knowledge-extraction`
  - topic_description → free-form topic
- **question_count**: Number of questions.
- **question_types**: Allowed types.
- **bloom_distribution** (optional): Proportion per Bloom level.
- **difficulty**: Initial difficulty (easy / medium / hard).
- **exclude_ids** (optional): Already-used question IDs to avoid repeats.

## Steps

### 1. Concept List for Questions

From the knowledge source, list concepts to assess:

- Per concept: name, module, Bloom range, suitable question types
- Coverage target: core concepts ≥ 80%
- Order by importance; prioritize high-importance concepts

### 2. Bloom × Question Type Matrix

Match question types to Bloom level:

| Bloom | Suitable types | Example stems |
|---|---|---|
| **L1 Remember** | Choice, true-false, fill | "Which is the definition of…?" "___ is a property of…." |
| **L2 Understand** | Choice, short answer, match | "Explain… in your own words." "What is the difference between A and B?" |
| **L3 Apply** | Fill, short answer, calculation | "Given…, compute…." "Solve using method X…." |
| **L4 Analyze** | Short answer, case | "Analyze the time complexity of this code." "What are the pros and cons of this approach?" |
| **L5 Evaluate** | Essay, comparison | "When should you choose A over B? Justify." |
| **L6 Create** | Design, open-ended | "Design a…." "How would you improve…?" |

**Default Bloom mix** (if not specified):
- Diagnostic: L1(20%) L2(30%) L3(30%) L4(15%) L5(5%)
- Midterm-style: L1(10%) L2(20%) L3(30%) L4(25%) L5(10%) L6(5%)
- Challenge: L3(20%) L4(30%) L5(30%) L6(20%)

### 3. Question Generation

Per question, follow templates:

**Choice**:
```yaml
type: choice
bloom: L2
concept: "Hash collision handling"
stem: "Which is correct about chaining vs open addressing?"
options:
  A: "Chaining load factor cannot exceed 1"     # Wrong
  B: "Open addressing degrades badly at high load"  # Right
  C: "Chaining needs no extra space"           # Wrong
  D: "Open addressing is better for frequent insert/delete"  # Wrong
answer: B
distractors_rationale:
  A: "Chaining can have load > 1 (unbounded chains)"
  C: "Pointers need extra space"
  D: "Deletion in open addressing is trickier (lazy delete)"
estimated_time_sec: 90
difficulty: medium
```

**Fill-in**:
```yaml
type: fill_blank
bloom: L1
concept: "Time complexity"
stem: "Quicksort average time is ___, worst case is ___."
answer: ["O(n log n)", "O(n²)"]
accept_variants: ["O(nlogn)", "O(n^2)"]
estimated_time_sec: 30
difficulty: easy
```

**Short answer**:
```yaml
type: short_answer
bloom: L4
concept: "Sorting comparison"
stem: "When would you choose mergesort over quicksort? Give at least two reasons."
rubric:
  - dimension: "Accuracy"
    weight: 0.4
    criteria: "Correctly state mergesort advantages (stable, worst O(nlogn))"
  - dimension: "Completeness"
    weight: 0.3
    criteria: "At least 2 scenarios/reasons"
  - dimension: "Depth"
    weight: 0.3
    criteria: "Tradeoff analysis, not just list"
reference_answer: "1) Need stable sort (e.g., sort by grade then name); 2) Need guaranteed worst-case O(nlogn); 3) Linked list (mergesort fits; quicksort random access is bad)."
estimated_time_sec: 180
difficulty: hard
```

### 4. Quality Check

Per question:

- [ ] Stem is unambiguous; a prepared student can understand what is asked
- [ ] Choice distractors are plausible (from common errors/misconceptions)
- [ ] Single correct answer (objective) or clear rubric (subjective)
- [ ] Stem matches stated Bloom level (e.g., if only recall needed, don’t label L4)
- [ ] Not duplicate of `exclude_ids` (same concept with different type/angle is ok)
- [ ] Estimated time fits exam limit

### 5. Question Order

- **Fixed difficulty**: Easy → medium → hard to reduce early frustration
- **Adaptive**: Start at medium; order then adjusted by `→ adaptive-difficulty`
- Avoid same concept in consecutive questions (reduce cueing)
- Vary types (choice → fill → short → choice…) for variety

## Output

```yaml
questions:
  - id: "q001"
    type: choice
    bloom: L2
    concept: "Hash collision handling"
    difficulty: medium
    estimated_time_sec: 90
    stem: "..."
    options: { A: "...", B: "...", C: "...", D: "..." }
    answer: "B"
    explanation: "..."
    distractors_rationale: { ... }

metadata:
  total_questions: 12
  bloom_distribution: { L1: 2, L2: 3, L3: 4, L4: 2, L5: 1 }
  concept_coverage: 0.85
  estimated_total_time_min: 35
  type_distribution: { choice: 4, fill_blank: 4, short_answer: 4 }
```

## Errors and Boundaries

- **Too few concepts** (< 3): Reduce count or go deeper (multiple Bloom levels on same concept).
- **Question type doesn’t fit subject** (e.g., true-false for math): Adjust type mix and explain.
- **Weak distractors**: Each distractor should reflect a real misconception.
