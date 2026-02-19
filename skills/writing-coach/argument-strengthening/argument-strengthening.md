---
name: argument-strengthening
description: Analyze argument quality using the Toulmin model; find logic gaps and suggest stronger evidence and reasoning. Called by writing-coach in step 4.
tags: [argument, logic, evidence, reasoning, toulmin, rhetoric]
parent: writing-coach
---

# Argument Strengthening

> Subskill of `writing-coach` — called in step 4

## When to Use

- Called by `writing-coach` in step 4 "Argument strengthening."
- Called in debrief by `debate-roleplay-learning` to analyze user argument quality.
- When the user asks "Check my argument logic."

## Input

- **text**: Argument-related paragraphs.
- **thesis**: Main claim (explicit or from structure-analysis).
- **genre**: Genre.

## Steps

### 1. Toulmin Breakdown

For each argument unit, identify the six elements:

```
[Data/Ground] ──→ [Warrant] ──→ [Claim]
                     ↑              ↑
                [Backing]      [Qualifier]
                                  ↓
                            [Rebuttal]
```

| Element | Meaning | Strong argument |
|---|---|---|
| **Claim** | Your conclusion | Specific, debatable, non-obvious |
| **Data/Ground** | Facts/evidence for the claim | Reliable, relevant, sufficient |
| **Warrant** | Reasoning from data to claim | Valid, stated clearly |
| **Backing** | Support for the warrant | Authority / consensus / theory |
| **Qualifier** | Scope/limit of the claim | Avoids overgeneralization |
| **Rebuttal** | Exceptions / counterpoints | Preempts objections, adds credibility |

### 2. Evidence Quality

Rate each piece of evidence:

| Grade | Type | Description | Strength |
|---|---|---|---|
| S | Statistics / experiments | Quantified, sourced | ★★★★★ |
| A | Authority | Expert / institution | ★★★★ |
| B | Case / history | Real events | ★★★ |
| C | Analogy | Explains via comparison | ★★ |
| D | Personal experience / common sense | Subjective or unverified | ★ |
| F | None | No support | ⚠️ |

Recommendation: At least one S or A per main claim; C/D only as support, not sole basis.

### 3. Logic Gap Detection

Scan for common flaws:

**Reasoning**:
- **Non sequitur**: Data and conclusion not connected by reasoning
- **Hasty generalization**: Generalizing from few cases
- **Post hoc**: Confusing order with cause
- **Slippery slope**: Unargued chain of consequences
- **Circular reasoning**: Conclusion assumed in premises

**Evidence**:
- **Insufficient evidence**: Too little or too weak
- **Cherry-picking**: Only favorable evidence
- **Outdated evidence**: Old data or studies
- **Unverified source**: No or weak citation

**Framing**:
- **Straw man**: Misrepresent then refute
- **Equivocation**: Same term, different meaning
- **Appeal to emotion**: Emotion instead of logic
- **False dichotomy**: Only two options when more exist

For each: location + type + severity (🔴 critical / 🟡 weakening / 🟢 minor) + fix suggestion.

### 4. Strengthening Suggestions

For each weak unit:

1. **Evidence**: Suggest types of data/sources to add (do not invent data)
2. **Reasoning**: Make the Warrant explicit ("Your reasoning is A → B → C; the step B→C needs…")
3. **Qualifier**: Add limits to overgeneral claims ("all" → "most," "always" → "often," "in … conditions")
4. **Rebuttal**: Suggest stating and answering a likely objection to boost credibility

### 5. Argument Strength Score

Overall score 0–10:

- 9–10: Clear claim, strong multi-layer evidence, tight logic, rebuttal addressed
- 7–8: Solid overall, minor gaps
- 5–6: Claim identifiable, but thin evidence or logic jumps
- 3–4: Weak argument, multiple logic issues
- 0–2: Little or no effective argument

## Output

```yaml
argument_units:
  - id: 1
    claim: "AI will fundamentally change education"
    data: "Personal experience using ChatGPT for learning"
    data_quality: D
    warrant: (implicit) "My experience generalizes"
    warrant_valid: false
    qualifier: null
    rebuttal: null
    issues:
      - type: hasty_generalization
        severity: 🟡
        fix: "Add large-scale evidence (e.g., UNESCO 2024 report)"
      - type: missing_qualifier
        severity: 🟢
        fix: "e.g., 'AI will likely significantly affect education in the next decade'"

overall_score: 5.5
summary: "Claim is clear but evidence is mostly personal experience; add statistics and authority to strengthen."
```

## Errors and Boundaries

- **Non-argumentative text** (narrative, expository): Skip Toulmin; assess accuracy and completeness instead.
- **Persistently weak argumentation**: Suggest `→ debate-roleplay-learning` for practice.
- **Sensitive politics/religion**: Analyze logic only; do not judge correctness of the stance.
