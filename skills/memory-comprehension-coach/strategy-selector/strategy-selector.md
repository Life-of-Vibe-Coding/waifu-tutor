---
name: strategy-selector
description: From mastery level, knowledge type, and user preferences, choose the best combination from 6 memory/understanding strategies. Called by memory-comprehension-coach in step 3.
tags: [strategy, selection, learning-method, personalization, cognitive]
parent: memory-comprehension-coach
---

# Strategy Selector

> Subskill of `memory-comprehension-coach` — called in step 3

## When to Use

- Called by `memory-comprehension-coach` in step 3 "Choose strategy."
- When recommending the best learning method for the user.

## Input

- **mastery_level**: From `mastery-diagnosis` (1–5).
- **obstacle_type**: Decay / shallow / confusion / abstraction / missing prerequisite / encoding failure.
- **knowledge_type**: Declarative / conceptual / procedural / metacognitive.
- **user_preferences** (optional): From `viking://user/memories`.
- **previous_strategies** (optional): What was tried before and how it worked.

## Steps

### 1. Strategy Set

**Six core strategies**:

| Strategy | Mechanism | Best for | Load |
|---|---|---|---|
| **Spaced repetition** | Review at forgetting point to extend retention | Declarative + decay | Low |
| **Active recall** | Recall without materials to strengthen retrieval | All + decay | Medium |
| **Feynman** | Explain simply to expose gaps | Conceptual + shallow | High |
| **Elaborative encoding** | Link new to existing knowledge | Conceptual + encoding failure | Medium |
| **Memory palace** | Link information to locations | Declarative (lists, sequences) | Medium |
| **Interleaving** | Mix different concepts in practice | Procedural + confusion | High |

### 2. Mastery × Knowledge Type → Strategy

| | Declarative | Conceptual | Procedural | Metacognitive |
|---|---|---|---|---|
| **Level 1** (no recall) | Memory palace + spaced | Elaborative + analogy | Demo + imitate | Case analysis |
| **Level 2** (vague) | Active recall + spaced | Feynman + elaborative | Stepwise practice | Socratic questions |
| **Level 3** (recall, not apply) | Interleaving | Practice + counterexamples | Varied practice | Scenario |
| **Level 4** (apply, not explain) | — | Feynman (advanced) | Teach someone | Debate |
| **Level 5** (deep) | — | Creative use | Optimize/design | Reflection |

### 3. Obstacle-Specific Tweaks

| Obstacle | Adjustment |
|---|---|
| **Decay** | Primary = spaced (shorter initial interval), secondary = active recall |
| **Shallow** | Primary = Feynman, secondary = elaborative |
| **Confusion** | Primary = contrast (interleaving variant), secondary = counterexamples |
| **Abstraction** | Primary = examples → abstraction (elaborative variant), secondary = multi-perspective |
| **Missing prerequisite** | ⚠️ Pause; use `→ study-guide-creator` first |
| **Encoding failure** | Primary = elaborative (rebuild links), secondary = active recall |

### 4. User Preference

From `viking://user/memories`:

```yaml
user_learning_profile:
  visual_preference: high
  verbal_preference: medium
  kinesthetic_preference: high
  social_preference: low

  past_effective_strategies:
    - "Feynman — very effective (eigenvalues L2 → L4)"
    - "Memory palace — medium (OSI layers learned but order slips)"

  past_ineffective_strategies:
    - "Pure flashcard spaced — boring, dropped"
```

**Rules**:
- If a recommended strategy failed before → try an alternative in the same group
- If user prefers visual → use visual flashcards in spaced repetition
- If user prefers hands-on → prefer interleaving and applied practice

### 5. Output

```yaml
selected_strategy:
  primary:
    name: "feynman_technique"
    reason: "Level 2 + conceptual + shallow → Feynman best to expose gaps"
    params:
      target_audience: "high-schooler"
      iteration_limit: 3

  secondary:
    name: "elaborative_encoding"
    reason: "Link to existing knowledge (matrix multiplication, linear transform)"
    params:
      anchor_concepts: ["Matrix multiplication", "Vector scaling", "Linear transform geometry"]

  fallback:
    name: "active_recall"
    trigger: "If Feynman still stuck after 2 rounds, use active recall for base"

  estimated_time_min: 15
  estimated_sessions: 2
```

## Output

- **selected_strategy**: Primary + secondary + fallback.
- **strategy_params**: Execution parameters.
- **estimated_effectiveness**: Expected gain and session count.
- **personalization_notes**: How user profile affected the choice.

## Errors and Boundaries

- **Tie between strategies**: Prefer one that worked for this user before; if no history, pick medium load (e.g., Feynman or elaborative).
- **User rejects recommendation**: Use their choice but log it and evaluate later.
- **All strategies failed before**: Try a combo (e.g., Feynman + interleaving) or suggest `→ debate-roleplay-learning` Socratic mode.
