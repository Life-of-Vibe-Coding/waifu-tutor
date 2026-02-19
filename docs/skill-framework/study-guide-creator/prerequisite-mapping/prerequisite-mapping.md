---
name: prerequisite-mapping
description: Analyze prerequisite relations between concepts, build a DAG, and output a topologically sorted learning path. Called by study-guide-creator in step 3.
tags: [prerequisite, dependency, DAG, topological-sort, learning-path]
parent: study-guide-creator
---

# Prerequisite Mapping

> Subskill of `study-guide-creator` — called in step 3

## When to Use

- Called by `study-guide-creator` in step 3 "Build prerequisite map."
- When the optimal learning order for any set of concepts is needed.
- Called by `project-based-tutor` to check if the user has prerequisites for a project.

## Input

- **concept_nodes**: From `knowledge-extraction`: list with `name`, `level`, `bloom_level`, `importance_weight`.
- **source_context** (optional): Document text or L2 detail to infer implicit dependencies.

## Steps

### 1. Dependency Detection

For each pair (A, B) decide if A is a prerequisite of B:

**Explicit** (high confidence):
- Text says "Before B you need A," "B builds on A," "See A"
- A appears before B in the document and B's definition uses A's terms
- A's result is used in B's derivation

**Implicit** (medium confidence):
- B's definition uses A's terms without explicit reference
- A and B in same section; A is Level 3 (sub-concept), B is Level 2 — sub-concept depends on parent
- Common-sense dependency (e.g., calculus depends on limits)

**No dependency**:
- A and B in different branches
- Same level and no term overlap

### 2. Build DAG

- Nodes = concept nodes
- Edge A → B = "A is prerequisite for B"
- Edge weight = strength: strong / recommended / optional
  - **strong**: Cannot understand B without A
  - **recommended**: A helps but not strictly required
  - **optional**: A deepens B (optional supplement)

### 3. Cycle Detection and Resolution

- Run cycle detection on the DAG.
- If cycle (e.g., A → B → C → A):
  - Find weakest edge (often optional/recommended)
  - Downgrade or remove to break the cycle
  - Tell user: "A and B are related; suggest learning A basics first, then B, then returning to A."

### 4. Topological Sort and Path

- Topologically sort the DAG to get a linear order.
- If multiple valid orders, prefer:
  1. Higher `importance_weight` first
  2. Lower `bloom_level` first (remember/understand before apply/analyze)
  3. Concepts on strong dependency chains first
- Identify concepts that can be learned in parallel (no dependency between them).

### 5. Path Description

Output a text path, e.g.:

```
Learning path:
Phase 1 (Foundation):
  [Concept A] → [Concept B]  (Can learn together: [C], [D])
Phase 2 (Core):
  [Concept E] → [Concept F]  (Depends on Phase 1)
Phase 3 (Advanced):
  [Concept G]  (Depends only on E)
  [Concept H]  (Depends on F and G)
```

## Output

```yaml
dependency_graph:
  edges:
    - from: "Arrays"
      to: "Linked list"
      strength: recommended
      reason: "Understanding array layout helps contrast with linked storage"
    - from: "Recursion"
      to: "Tree traversal"
      strength: strong
      reason: "Tree traversal is typically implemented recursively"
  cycles_resolved:
    - cycle: ["A", "B", "C"]
      removed_edge: "C → A"
      suggestion: "Learn A basics → B → C → return to deepen A"

learning_path:
  phases:
    - phase: 1
      label: "Foundation"
      concepts: ["Arrays", "Pointers basics"]
      parallel_ok: true
    - phase: 2
      label: "Core"
      concepts: ["Linked list", "Stack", "Queue"]
      parallel_ok: true
      depends_on: [1]
    - phase: 3
      label: "Advanced"
      concepts: ["Recursion", "Binary tree"]
      depends_on: [1, 2]

total_phases: 3
critical_path: ["Arrays", "Pointers", "Linked list", "Recursion", "Binary tree", "BST", "AVL"]
critical_path_length: 7
```

## Errors and Boundaries

- **Very few concepts** (< 5): Output a simple linear order; skip heavy dependency analysis.
- **Very many concepts** (> 80): First order at Level 1, then order within each module.
- **Cross-domain** (e.g., ML needs linear algebra + probability + coding): Mark external dependencies as "Prerequisite courses," not inside the DAG; mention in output.
- **Uncertain dependency**: Label medium/low confidence edges as recommended or optional so the user can choose to skip.
