---
name: knowledge-extraction
description: Extract core concept nodes, hierarchy, key terms, and cognitive levels from document content or a given topic. Called by study-guide-creator in step 2.
tags: [extraction, concepts, taxonomy, bloom, document-analysis]
parent: study-guide-creator
---

# Knowledge Extraction

> Subskill of `study-guide-creator` — called in step 2

## When to Use

- Called by `study-guide-creator` in step 2 "Knowledge extraction and structure."
- Can be called by `exam-mode-tuner` to define scope and concept coverage.
- Can be called by `project-based-tutor` to define concepts to cover in a project.

## Input

- **source**: One of:
  - Document ID → fetch L1 overview + L2 detail from `viking://resources/users/{user_id}/documents/{doc_id}`
  - Raw text (pasted or chunk list)
  - Topic description (no document; use general knowledge)
- **depth**: shallow / normal / deep
- **subject_hint** (optional): Subject hint for domain terms

## Steps

### 1. Document Parsing and Segmentation

- If document ID: fetch L1 overview for structure, then L2 detail by section as needed.
- If raw text: segment by natural paragraphs / headings.
- If topic only: build a standard knowledge framework from domain knowledge.

### 2. Concept Node Identification

For each paragraph/section:

1. **Entity extraction**: Identify terms, concept names, theories, formulas, theorems.
2. **Deduplication**: Merge same concept under different names (e.g., "linked list" and "链表").
3. **Hierarchy**:
   - Level 0: Subject/course (e.g., "Data structures")
   - Level 1: Chapter/major topic (e.g., "Linear structures," "Trees," "Graphs")
   - Level 2: Core concept (e.g., "Binary search tree," "AVL," "Red-black tree")
   - Level 3: Sub-concept/detail (e.g., "Left rotation," "Balance factor")

### 3. Bloom Level Labeling

Label each concept by target cognitive level:

| Bloom level | Verbs | Example |
|---|---|---|
| L1 Remember | List, define, identify | List names of sorting algorithms |
| L2 Understand | Explain, compare, summarize | Explain divide-and-conquer in quicksort |
| L3 Apply | Use, implement, compute | Sort an array with quicksort |
| L4 Analyze | Analyze, distinguish, infer | Analyze quicksort worst-case time |
| L5 Evaluate | Evaluate, choose, justify | Justify when to use quicksort vs mergesort |
| L6 Create | Design, construct, optimize | Design a hybrid sorting strategy |

### 4. Importance Weight

Each concept gets `importance_weight` (0.0–1.0) from:

- **Frequency** (0.3): How often it appears (normalized)
- **Structure** (0.3): How many other concepts depend on it
- **Exam signal** (0.2): In "summary," "review," "key point" sections
- **Bloom** (0.2): Higher Bloom often higher importance

Formula: `weight = 0.3×freq_norm + 0.3×dependency_out_degree_norm + 0.2×exam_signal + 0.2×bloom_norm`

### 5. Glossary

Output a term list: term (and English if relevant), one-sentence definition, concept node, first occurrence (section/page/URI).

## Output

```yaml
concepts:
  - name: "Binary Search Tree"
    name_en: "Binary Search Tree"
    level: 2
    parent: "Trees"
    bloom_level: 3
    importance_weight: 0.82
    definition: "Binary tree where left subtree < root < right subtree"
    source_uri: "viking://resources/users/.../documents/ds-textbook#chapter-5"
    sub_concepts: ["Insert", "Delete", "Search", "Inorder traversal"]
    common_misconceptions:
      - "BST is always balanced"  # It is not; can degenerate to list
    exam_frequency: high
glossary:
  - term: "Inorder traversal"
    term_en: "Inorder Traversal"
    definition: "Visit left, then root, then right recursively"
    belongs_to: "Binary Search Tree"
    first_seen: "chapter-5, page 102"
```

## Errors and Boundaries

- **Mixed language in document**: Output in one main language; keep terms in both languages if needed.
- **Unstructured material** (e.g., transcript): Cluster by topic first, then extract; allow more noise.
- **Cross-domain material**: Group by domain; mark cross-cutting concepts.
- **Too many concepts** (> 100): Keep top 50–80 by importance; put the rest in "Further reading."
