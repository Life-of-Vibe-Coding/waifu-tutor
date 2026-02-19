---
name: fallacy-detection
description: Detect logical fallacies in debate and argumentation in real time; classify and annotate them, and provide teaching explanations in the debrief. Called continuously by debate-roleplay-learning during the interaction.
tags: [fallacy, logic, critical-thinking, reasoning-error, detection]
parent: debate-roleplay-learning
---

# Fallacy Detection

> Subskill of `debate-roleplay-learning` — called continuously during the interaction

## When to Use

- Called by `debate-roleplay-learning` throughout the debate.
- Called by `writing-coach/argument-strengthening` when analyzing arguments.
- When the user asks "Check this argument for logical problems."

## Input

- **text**: Argument text to analyze.
- **context**: Debate context (to avoid flagging reasonable rhetoric as fallacies).

## Steps

### 1. Fallacy Taxonomy

Scan for these four categories:

#### A. Formal Fallacies

Conclusion does not follow logically from premises:

| Fallacy | Pattern | Example |
|---|---|---|
| **Affirming the consequent** | If P then Q; Q; therefore P | "If it rains the ground is wet; ground is wet; so it rained" (could be sprinklers) |
| **Denying the antecedent** | If P then Q; not P; therefore not Q | "If it's a cat it's an animal; it's not a cat; so not an animal" |
| **Fallacy of composition** | What holds for the whole holds for each part | "The company is profitable, so every department is profitable" |

#### B. Informal — Relevance

Evidence is irrelevant to the conclusion:

| Fallacy | Description | Detection cues |
|---|---|---|
| **Ad hominem** | Attack the person, not the argument | "You're not an expert," "You don't practice what you preach" |
| **Appeal to authority** | Appeal to authority in the wrong domain | "Famous person X thinks so" (X not expert in the field) |
| **Appeal to emotion** | Emotion replaces logic | "Think of the children!" (no logical argument) |
| **Bandwagon** | Everyone believes it so it's true | "Most people agree" |
| **Red herring** | Introduce irrelevant topic | Answering A by talking about unrelated B |
| **Straw man** | Misrepresent then refute | "So you're saying…" (but that wasn't the claim) |

#### C. Informal — Inference

Errors in reasoning:

| Fallacy | Description | Detection |
|---|---|---|
| **Hasty generalization** | Generalize from few cases | Small sample + absolute conclusion |
| **Post hoc** | Temporal order ≠ causation | "A happened then B, so A caused B" |
| **Slippery slope** | Unargued chain of consequences | "If A then B then C then doom" |
| **False dichotomy** | Only two options when more exist | "Either X or Y" (ignoring Z) |
| **Circular reasoning** | Conclusion assumed in premises | Nested definitions or tautology |
| **Appeal to ignorance** | No evidence against = true | "You can't prove X is false, so X is true" |

#### D. Informal — Ambiguity

Ambiguity that misleads:

| Fallacy | Description |
|---|---|
| **Equivocation** | Same term used with different meanings |
| **Composition** | Properties of parts ≠ properties of whole |
| **Division** | Properties of whole ≠ properties of parts |

### 2. Detection Flow

For each argument segment:

1. **Sentence-level scan**: Check for the patterns above
2. **Argument-level**: Check whether the overall reasoning chain is valid
3. **Context check**: Exclude legitimate rhetoric (e.g., deliberate exaggeration in creative writing)
4. **Confidence**: Label each detection as high / medium / low to reduce false positives

### 3. Output Format

For each detected fallacy:

```yaml
fallacies_detected:
  - id: F1
    type: "false_dichotomy"
    category: "inference"
    location: "Round 2, user sentence 2"
    original_text: "The economy is either fully free or fully government-controlled"
    severity: 🟡  # 🔴 critical / 🟡 weakening / 🟢 minor
    confidence: high

    explanation: |
      This is a false dichotomy. Real economies lie on a spectrum from
      free market to central planning (e.g., Nordic model, Singapore).
      Limiting to two extremes rules out more plausible middle positions.

    teaching_moment: |
      💡 Debate tip: When you frame things as "either A or B," ask whether
      there are really only two options. Acknowledging a spectrum often
      makes your argument more nuanced and persuasive.

    fix_suggestion: "Reframe as: 'Where is the best balance between freer markets and more intervention?'"
```

### 4. Teaching Presentation in Debrief

In the debrief, present fallacies in a teaching way:

- Not "You made a mistake" but "Here's a common reasoning trap"
- For each: name → your wording → why it's a fallacy → how to fix → short tip
- If the same fallacy appears repeatedly, merge into one teaching unit and suggest focused practice

## Output

- **fallacies_detected**: List with type, location, explanation, fix suggestion.
- **fallacy_summary**: Counts by type (which fallacies appear most).
- **critical_thinking_score**: Score 0–10.

## Errors and Boundaries

- **False positives**: Some rhetoric (deliberate exaggeration, irony) may be misclassified. Use context to reduce; confidence helps filter in debrief.
- **Cultural differences**: Some patterns are more acceptable in some cultures (e.g., appeal to authority).
- **Over-annotation**: Report at most 2–3 most important fallacies per round to avoid overload.
