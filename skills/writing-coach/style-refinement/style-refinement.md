---
name: style-refinement
description: Improve tone, precision, sentence variety, and paragraph rhythm. Called by writing-coach in step 5.
tags: [style, tone, diction, sentence-variety, polish, voice]
parent: writing-coach
---

# Style Refinement

> Subskill of `writing-coach` — called in step 5

## When to Use

- Called by `writing-coach` in step 5 "Style refinement."
- When the user asks "Polish my wording" or "The tone feels off."
- When structure and argument are solid and the focus is language.

## Input

- **text**: Text to refine.
- **tone**: Target tone (formal / casual / academic / persuasive / creative / diplomatic).
- **audience**: Target reader.
- **language**: Language of the text (e.g., English / Chinese / bilingual).

## Steps

### 1. Tone Consistency

Check that tone matches the target:

| Target | Traits | Avoid |
|---|---|---|
| `formal` | Third person, no contractions, full sentences | Colloquialism, exclamation, emoji |
| `casual` | First/second person, natural voice, contractions ok | Overly academic terms, long complex sentences |
| `academic` | Moderate passive voice, precise terms, citations | Subjective judgment, emotional language |
| `persuasive` | Rhetoric, action verbs, emotional resonance | Overly neutral wording |
| `diplomatic` | Hedging, acknowledging others, leaving room | Direct negation, absolutes |

Flag spots where tone drifts (e.g., colloquial in an academic piece).

### 2. Precision

Scan for:

**Vague → precise**:
| Vague | More precise (example) |
|---|---|
| "many" | "73% of respondents," "over 2 million users" |
| "some" | "three main factors," "at least five cases" |
| "good/bad" | "efficient/inefficient," "beneficial/harmful" |
| "things" | Concrete noun |
| "a discussion was held" | "we discussed" (avoid weak verbs) |

**Redundancy**:
- Remove filler: "actually," "basically," "you know," "I mean"
- Compress: "at the current stage" → "now"; "as for …" → direct subject
- Avoid repetition: "very very important" → "critical"

**Voice**:
- Academic: Some passive is fine ("Experiments show…"); avoid overuse
- Other genres: Prefer active ("Researchers found…" not "…was found")
- Flag awkward passive and suggest active alternatives

### 3. Sentence Variety

Analyze sentence types and suggest balance:

**Types**: Simple (S-V-O), compound (A and/but/or B), complex (clauses), rhetorical (question, parallel), short (for emphasis)

**Typical balance (argumentative)**: ~30% simple, ~25% compound, ~30% complex, ~15% rhetorical/short. Avoid 3+ same type in a row. Vary paragraph openings (not every "First…" "Second…").

**Fixes**:
- Long run of short sentences → Combine some into complex
- Long run of long sentences → Insert a short sentence for rhythm
- All declarative → Add a rhetorical question where it fits

### 4. Paragraph Rhythm

**Opening sentences**: First sentence should convey the paragraph’s main point (for skimming). Avoid starting with pronouns or pure transitions.

**Length**: Avoid all paragraphs the same length. Key paragraphs can be longer; transitions can be 1–2 sentences. One-sentence paragraphs for emphasis are fine.

**Closing sentences**: End with a clear wrap or transition. Avoid ending on hedges ("maybe," "perhaps").

### 5. Revision Suggestions

Format each suggestion:

```
📍 Location: Paragraph X, sentence Y
🏷️ Type: Precision / Tone mismatch / Monotony / Redundancy
📝 Original: "In many cases, AI can basically achieve pretty good results."
✏️ Option A: "In 73% of test scenarios, AI reached human-level accuracy."
✏️ Option B: "AI outperformed traditional methods on most standard benchmarks."
💡 Reason: Original is vague (many, basically, pretty good); quantifying or specifying strengthens.
```

Offer 2–3 alternatives; do not replace for the user—explain why the change helps.

## Output

```yaml
tone_issues:
  - paragraph: 3
    sentence: 2
    current_tone: casual
    expected_tone: academic
    fix: "Change 'this thing is amazing' to 'the technology demonstrates significant performance advantages'"

diction_fixes:
  - location: "¶2, S1"
    type: vague_word
    original: "many studies show"
    options:
      - "Several meta-analyses show (Smith et al., 2024)"
      - "More than 30 independent studies consistently show"
    reason: "Quantify and cite source"

variety_analysis:
  simple_ratio: 0.55  # too high
  compound_ratio: 0.15
  complex_ratio: 0.25
  rhetorical_ratio: 0.05  # too low
  suggestion: "Paragraphs 4–5 have four simple sentences in a row; consider combining two and adding one rhetorical question"

overall_polish_score: 6.5
```

## Errors and Boundaries

- **Creative writing**: Rules are looser; don’t over-correct intentional "incorrect" usage (dialect, fragments for effect).
- **Non-native writers**: Fix issues that affect clarity first; don’t demand perfect idiom. Note "good usage here" to build confidence.
- **Strong personal style**: Respect it; only fix clear grammar and clarity issues.
