---
name: mastery-diagnosis
description: Use quick questions to diagnose mastery level (1–5) for a concept; distinguish "don't remember" from "don't understand" and output obstacle type and intervention suggestions. Called by memory-comprehension-coach in step 1.
tags: [diagnosis, mastery, bloom, solo, assessment, comprehension-level]
parent: memory-comprehension-coach
---

# Mastery Diagnosis

> Subskill of `memory-comprehension-coach` — called in step 1

## When to Use

- Called by `memory-comprehension-coach` in step 1 "Diagnose mastery."
- Called by `exam-mode-tuner` before a diagnostic to estimate level.
- When the user says "I don't know if I get it," "Test my understanding of X."

## Input

- **concept**: Concept or topic to diagnose.
- **document_id** (optional): Related material for full definition.
- **prior_data** (optional): Past performance from `performance-analytics`.

## Steps

### 1. Design Diagnostic Questions

3–5 short questions by Bloom level:

```yaml
diagnostic_questions:
  - level: 1  # Remember
    question: "Can you state the definition of eigenvalue? Even roughly."
    pass_criteria: "Mentions at least 2 of: matrix, vector, scaling"

  - level: 2  # Understand
    question: "How do eigenvalues and eigenvectors relate? Why do they come in pairs?"
    pass_criteria: "Explains Ax=λx: direction unchanged, only scaled"

  - level: 3  # Apply
    question: "For matrix [[2,1],[0,3]], can you find its eigenvalues?"
    pass_criteria: "Gets λ=2, λ=3 (or describes correct method)"

  - level: 4  # Analyze
    question: "Why are eigenvalues of a symmetric matrix real? Can you give an intuitive reason?"
    pass_criteria: "Reasonable geometric or algebraic explanation"

  - level: 5  # Evaluate/Create
    question: "In PCA, why use eigenvectors for largest eigenvalues? What if we used smallest?"
    pass_criteria: "Explains variance maximization and consequence of using smallest"
```

**Design rules**:
- Start at lowest level; only go up if they pass
- Stop at first wrong or "don't know" (that level = ceiling)
- Keep questions short (< 30 sec); tone supportive: "Any impression is fine," "Guessing is ok"

### 2. Mastery Level

| Level | Name | Criteria | Bloom |
|---|---|---|
| **1** | No recall | Cannot recall anything | Below L1 |
| **2** | Vague | Some keywords but can't organize | Partial L1 |
| **3** | Recall but not apply | Can define/explain but not solve | L1–L2 |
| **4** | Apply but not transfer | Can solve but not explain or use in new context | L3–L4 |
| **5** | Deep, transferable | Can explain, apply, analyze, evaluate, create | L5–L6 |

### 3. Obstacle Type

"Don't remember" vs "don't understand" need different strategies.

| Obstacle | Signal | Intervention |
|---|---|---|
| **Decay** | Used to get it right; now forgot; says "I used to know" | Spaced repetition, active recall |
| **Shallow** | Can recite definition but can't give own example | Feynman, elaborative encoding |
| **Confusion** | Mix similar concepts (stack/queue, eigenvalue/singular value) | Contrast, interleaving |
| **Abstraction** | Understand examples but not general case | Multiple examples → abstraction, progressive build |
| **Missing prerequisite** | Lacks prior knowledge for this concept | Fill prerequisite first `→ study-guide-creator` |
| **Encoding failure** | First exposure was passive (read without processing) | Relearn + elaborative encoding |

### 4. Solo Cross-Check

Use Solo taxonomy to cross-validate Bloom:

| Solo level | Behavior | Example |
|---|---|---|
| **Prestructural** | Irrelevant answer | "Eigenvalue… something about matrices?" |
| **Unistructural** | One relevant element | "Eigenvalue is a number" |
| **Multistructural** | Several elements, no link | "Matrix, vector, lambda" |
| **Relational** | Elements connected | "Matrix acts on eigenvector: only length changes, not direction" |
| **Extended abstract** | Transfer to new situation | "So in PCA we use eigenvalues because…" |

## Output

```yaml
diagnosis:
  concept: "Eigenvalues and eigenvectors"
  mastery_level: 2
  solo_level: "Multistructural"

  obstacle_type: "Shallow understanding"
  obstacle_detail: "User can say Ax=λx but not explain each symbol and their relation"

  evidence:
    - question: "Define eigenvalue"
      response: "It's a number for the matrix... related to vectors"
      level_achieved: 2
    - question: "What does Ax=λx mean"
      response: "A times x equals lambda times x... equality?"
      level_achieved: 2
    - question: "Find eigenvalues of [[2,1],[0,3]]"
      response: "...I don't know how"
      level_achieved: 0

  recommendation:
    primary_strategy: "feynman_technique"
    secondary_strategy: "elaborative_encoding"
    reason: "Fragmented knowledge; Feynman to expose gaps, elaborative to connect"
    estimated_sessions_to_level_4: 2-3
    prerequisite_check: "Matrix multiplication OK; determinant — confirm"
```

## Errors and Boundaries

- **Nerves affect performance**: Say "This isn't a test; it's to pick the best method." Use a warm-up question they can answer.
- **Diagnosis conflicts with history**: Trust current diagnosis (knowledge can decay); use history to tell decay vs never learned.
- **User won't answer**: Respect that; infer level from their usual questions instead.
