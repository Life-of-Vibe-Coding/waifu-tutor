---
name: structure-analysis
description: Analyze paragraph organization, logic flow, and structural completeness; label paragraph functions and diagnose structure issues. Called by writing-coach in step 3.
tags: [structure, paragraph, coherence, organization, logical-flow]
parent: writing-coach
---

# Structure Analysis

> Subskill of `writing-coach` — called in step 3

## When to Use

- Called by `writing-coach` in step 3 "Structure analysis and reorganization."
- When the user explicitly asks "Review my essay structure."
- Referenced by `argument-strengthening` to see where arguments sit in the text.

## Input

- **text**: Full draft (or document ID).
- **genre**: Genre (determines expected structure template).
- **rubric** (optional): Structure-related criteria from the assignment.

## Steps

### 1. Paragraph Segmentation and Function Labels

Label each paragraph by function:

| Label | Meaning | Typical position |
|---|---|---|
| `HOOK` | Hook / attention grabber | Opening |
| `THESIS` | Main claim / central idea | End of intro |
| `CONTEXT` | Background / setup | Intro or second paragraph |
| `EVIDENCE` | Evidence / data / examples | Body |
| `REASONING` | Reasoning / link from evidence to claim | After EVIDENCE |
| `TRANSITION` | Transition between sections | Between main points |
| `COUNTERARGUMENT` | Counterargument / objection | Mid-to-late body |
| `REBUTTAL` | Response to counterargument | After COUNTERARGUMENT |
| `SYNTHESIS` | Synthesis of multiple points | Near end |
| `CONCLUSION` | Conclusion / summary | End |
| `CALL_TO_ACTION` | Call to action / outlook | In or after conclusion |
| `DIGRESSION` | Off-topic | Any (flag as issue) |

### 2. Logic Flow Map

Analyze logical relations between paragraphs and build a flow:

**Relation types**:
- `→ CAUSAL`: Because A, therefore B
- `→ PROGRESSIVE`: Not only A but also B
- `→ PARALLEL`: A and B are both important
- `→ CONTRASTIVE`: Although A, B
- `→ ELABORATIVE`: A, specifically B
- `✗ DISCONNECTED`: No clear link (flag as issue)

Output a text flow, e.g.:
```
¶1 [HOOK] → ¶2 [CONTEXT] →(CAUSAL)→ ¶3 [THESIS]
                                    ↓
¶4 [EVIDENCE-1] →(ELABORATIVE)→ ¶5 [REASONING-1]
                                    ↓ (PROGRESSIVE)
¶6 [EVIDENCE-2] →(ELABORATIVE)→ ¶7 [REASONING-2]
                                    ↓ (CONTRASTIVE)
¶8 [COUNTERARGUMENT] → ¶9 [REBUTTAL]
                                    ↓
¶10 [SYNTHESIS] → ¶11 [CONCLUSION + CALL_TO_ACTION]
```

### 3. Structural Completeness

Check required components for the genre:

**Argumentative essay checklist**:
- [ ] Clear THESIS paragraph?
- [ ] At least 2–3 EVIDENCE + REASONING pairs?
- [ ] COUNTERARGUMENT + REBUTTAL?
- [ ] CONCLUSION that ties back to THESIS?
- [ ] HOOK or other opening strategy?
- [ ] Transitions between sections (explicit or implicit)?

**Academic paper checklist**:
- [ ] Full IMRaD (or equivalent)?
- [ ] Literature review adequate?
- [ ] Methods reproducible?
- [ ] Results and discussion separated or clearly combined?
- [ ] Abstract complete (purpose–methods–results–conclusion)?

### 4. Diagnosis and Restructuring Suggestions

Common issues and fixes:

| Issue | Symptom | Suggestion |
|---|---|---|
| **Missing counterargument** | No COUNTERARGUMENT | Add "Some might say…" + REBUTTAL before conclusion |
| **Scattered thesis** | THESIS vague or repeated inconsistently | Single clear THESIS at end of intro |
| **Evidence dump** | EVIDENCE without REASONING | Add analysis after each evidence block |
| **Weak ending** | Short or repetitive conclusion | Expand: restate claim + significance + call to action |
| **Long paragraphs** | Single paragraph > 250 words | Split by sub-claims |
| **Logic gap** | DISCONNECTED between paragraphs | Add transition or reorder |
| **Repetition** | Same idea in multiple paragraphs | Merge or keep strongest version |

## Output

```yaml
paragraph_annotations:
  - index: 1
    function: HOOK
    summary: "Personal story opening on AI in education"
    quality: good
  - index: 4
    function: EVIDENCE
    summary: "Cites a 2023 survey"
    quality: weak
    issue: "No REASONING paragraph following"

logic_flow:
  connections:
    - from: 1
      to: 2
      type: ELABORATIVE
    - from: 3
      to: 4
      type: DISCONNECTED
      issue: "Jump from claim to evidence without bridge"

completeness:
  missing: [COUNTERARGUMENT, REBUTTAL]
  redundant: [¶5 and ¶7 repeat same point]

restructure_suggestion:
  moves:
    - action: add
      position: after_paragraph_7
      content_hint: "Add counterargument: e.g., AI may widen digital divide"
    - action: merge
      paragraphs: [5, 7]
      reason: "Redundant; merge into one stronger paragraph"
    - action: expand
      paragraph: 9
      reason: "Conclusion too short; restate claim and add outlook"
```

## Errors and Boundaries

- **Non-argumentative text** (e.g., fiction, poetry): Use narrative labels (setup / conflict / climax / resolution) instead.
- **Fragmented text** (notes, outline): Reorganize by intended structure rather than strict analysis.
- **Very long text** (> 5000 words): Do section-level analysis first; go paragraph-level only where needed.
