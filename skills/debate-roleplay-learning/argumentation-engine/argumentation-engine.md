---
name: argumentation-engine
description: Build, evaluate, and rebut arguments; generate strong opposing arguments for the Tutor and analyze the user's argument quality and structure. Called continuously during debate-roleplay-learning interactions.
tags: [argumentation, rhetoric, rebuttal, counter-argument, logic]
parent: debate-roleplay-learning
---

# Argumentation Engine

> Subskill of `debate-roleplay-learning` — called continuously during the interaction

## When to Use

- Called by `debate-roleplay-learning` during debate to:
  1. Generate Tutor rebuttals and counter-arguments
  2. Analyze the user's argument quality
- Referenced by `writing-coach/argument-strengthening` for argument-building methods.

## Input

- **user_argument**: User's latest argument text.
- **debate_context**: Motion, existing points from both sides, round number.
- **tutor_stance**: Tutor's assigned stance.
- **difficulty**: Opponent strength (gentle / balanced / aggressive).
- **evidence_pool**: Available evidence from documents and knowledge base.

## Steps

### 1. Analyze User Argument Structure

Apply Toulmin analysis (reuse `writing-coach/argument-strengthening` methodology):
- Identify Claim, Data, Warrant
- Rate evidence strength (S/A/B/C/D/F)
- Check reasoning chain completeness
- Note strengths and weaknesses (do not show to user until debrief)

### 2. Generate Tutor Rebuttal

Choose rebuttal strategy from user's weaknesses and Tutor's stance:

**Strategy priority** (strongest to weakest):

1. **Direct Rebuttal**
   - Contradict the user's main claim with direct evidence
   - "You said X, but data shows Y"
   - Requires strong counter-evidence

2. **Undermining**
   - Challenge the user's premises/assumptions
   - "Your argument assumes A, but that assumption is questionable…"
   - Undercut the basis of the argument

3. **Counter-example**
   - Give a concrete case where the user's conclusion fails
   - "If your conclusion held, how would you explain situation XX?"
   - Force refinement or qualification of the claim

4. **Boundary Testing**
   - Push the conclusion to extremes to test validity
   - "By your logic, would XX also be true?"
   - Expose overgeneralization

5. **Alternative Explanation**
   - Offer a different interpretation of the same evidence
   - "The data you cited could also support…"
   - Weaken the exclusivity of the evidence

### 3. Difficulty Tuning

| Difficulty | Tutor behavior |
|---|---|
| **gentle** | Weaker strategies (counter-example, boundary); more think time; hints after rebuttal |
| **balanced** | Mix of strategies; moderate strength; no hints |
| **aggressive** | Prefer direct rebuttal and undermining; rapid follow-ups; little respite |

**Adaptive tuning**:
- User fails to rebut effectively for 2 rounds → lower difficulty one step
- User performs well (strong rebuttals, new evidence) → raise difficulty one step
- User shows frustration/anxiety → force gentle

### 4. Argument Quality Scoring

Update user argument quality after each round:

```yaml
round_assessment:
  round: 3
  user_claim_clarity: 0.8
  evidence_quality: 0.5
  reasoning_validity: 0.7
  rebuttal_effectiveness: 0.3
  new_points_introduced: true
  overall_round_score: 0.58

  highlights: ["Round 3 introduced new economic data, better than before"]
  weaknesses: ["Did not address Tutor's point on externalities"]
```

## Output

- **tutor_response**: Tutor's rebuttal text (in character).
- **strategy_used**: Rebuttal strategy used.
- **user_assessment**: Assessment of user's argument this round (internal; shown in debrief).
- **cumulative_scores**: Trend of argument quality over time.

## Errors and Boundaries

- **Evidence not in knowledge base**: Use general knowledge and label as "general evidence"; do not invent specific data.
- **User makes a point Tutor cannot rebut**: Acknowledge honestly: "That's a strong point; I'll respond from a different angle"—good debate modeling.
- **Circular debate**: When both sides repeat the same points, move to a new point or to closing.
