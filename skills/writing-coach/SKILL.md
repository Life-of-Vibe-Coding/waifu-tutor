---
name: writing-coach
description: Coach the user through writing tasks (essays, reports, emails, etc.) with structure advice, argument strengthening, style polish, and iterative revision. Use when the user asks for "help revising my essay," "polish my paper," or "writing guidance."
tags: [writing, coach, essay, feedback, tutor, revision, academic, rhetoric]
subskills:
  - structure-analysis
  - argument-strengthening
  - style-refinement
---

# Writing Coach

## When to Use

- User asks for writing help: "Help me revise this," "I don't know how to organize my paper," "Polish my email."
- User shares or submits a draft and wants structural feedback, grammar fixes, or argument strengthening.
- User needs to plan an essay from scratch (outline and main points).
- User asks "How do I write a good X?" or "How should I structure my paper?"
- Called by `→ project-based-tutor` when a milestone deliverable is a report or essay.
- Follow-up from `→ debate-roleplay-learning` when the user wants to turn debate points into a written piece.

## Steps

### 1. Clarify Genre and Evaluation Framework

Confirm writing context and load the right evaluation framework:

| Genre | Main dimensions | Typical structure |
|---|---|---|
| **Academic paper** | Originality, evidence, citations, logic | Intro–Literature–Methods–Results–Discussion–Conclusion (IMRaD) |
| **Essay/Argument** | Clear claim, logic, rebuttal, persuasiveness | Hook–Thesis–Evidence×3–Counterargument–Conclusion |
| **Report** | Accuracy, completeness, actionable advice | Summary–Background–Analysis–Conclusion–Recommendations |
| **Email/Business** | Clear purpose, tone, brevity | Purpose–Key info–Call to action |
| **Creative** | Tension, character, imagery, pace | Varies by genre |

Ask if missing: target audience (professor / colleagues / public / client), purpose (persuade / inform / explain / entertain), word limit, rubric.

### 2. Assess Current State

**If the user has a draft**:

Run a four-part scan:

1. **Structure** → `→ structure-analysis/structure-analysis.md`
   - Overall organization and logic
   - Paragraph roles and flow
   - Transitions

2. **Argument** → `→ argument-strengthening/argument-strengthening.md`
   - Clear, debatable claim
   - Sufficient, relevant evidence
   - Complete chain (evidence → reasoning → claim)

3. **Style** → `→ style-refinement/style-refinement.md`
   - Tone fit for audience and purpose
   - Precise, non-redundant wording
   - Sentence variety

4. **Mechanics** (handle directly):
   - Grammar
   - Punctuation and format
   - Citation style (for academic)

**If starting from zero**:
- Guide brainstorming (e.g., 3-minute free association)
- Help narrow to a core claim
- Use 5W1H (What, Why, Who, When, Where, How)
- Produce an initial outline for user to confirm before drafting

### 3. Structure Analysis and Reorganization → `structure-analysis`

Call subskill `→ structure-analysis/structure-analysis.md` to:
- Label paragraph roles (hook / thesis / context / evidence / reasoning / transition / counterargument / rebuttal / synthesis / conclusion / call to action / digression)
- Map logic flow (causal / progressive / parallel / contrast / elaborative)
- Diagnose: missing parts (e.g., no rebuttal), redundancy, wrong order
- Output: restructuring suggestions + paragraph-level changes

### 4. Argument Strengthening → `argument-strengthening`

Call subskill `→ argument-strengthening/argument-strengthening.md` to:
- Toulmin analysis (Claim–Data–Warrant–Backing–Qualifier–Rebuttal)
- Evidence quality (fact / statistic / case / authority / analogy; strengths vary)
- Logic gaps (non sequitur, hasty generalization, unaddressed rebuttal)
- Output: strengthening plan + alternative evidence ideas

### 5. Style Refinement → `style-refinement`

Call subskill `→ style-refinement/style-refinement.md` to:
- Check tone consistency
- Sharpen wording (vague → specific, passive → active where appropriate)
- Vary sentence structure
- Adjust rhythm within paragraphs
- Output: inline suggestions (original → 2–3 alternatives)

### 6. Feedback — Sandwich Method

Structure all feedback as:

**Layer 1: Praise**
- Name 2–3 specific strengths (not generic "good job")
- Example: "The contrast in paragraph 3 works well and makes the abstract idea concrete."

**Layer 2: Constructive critique**
- 3–5 prioritized suggestions
- Each: issue + quote from draft + concrete revision options (2–3)
- Severity: 🔴 must fix / 🟡 should fix / 🟢 nice to have

**Layer 3: Encouragement and next step**
- Brief positive on direction
- Clear next action

### 7. Iteration Loop

After the user revises, focus each round on one layer:

```
Round 1: Structure — Is the argument skeleton sound?
Round 2: Argument — Is each claim well supported and logical?
Round 3: Language — Wording, tone, flow
Round 4: Polish — Hook, conclusion, transitions
Round 5: Final pass — Full read, overall grade + comparison to first draft
```

At the end of each round, note how much that dimension improved.

### 8. Final Assessment

When done, provide:
- **Overall score** (by genre dimensions, e.g., structure 8/10, argument 7/10, language 9/10)
- **Comparison to first draft**: What improved
- **Next steps**: e.g., "To strengthen argumentation, try debate practice" → `→ debate-roleplay-learning`

## Input

- **Draft text**: Pasted text or document ID.
- **Genre**: Essay / report / email / creative / auto-detect.
- **Optional**:
  - `focus`: structure / argument / language / grammar / all
  - `tone`: formal / casual / academic / persuasive / creative
  - `word_limit`
  - `rubric`: assignment or grading criteria
  - `audience`: target reader
  - `iteration_round`: 1–5, to focus feedback

## Output

- **Diagnosis summary**: Short overview of draft and main improvement areas.
- **Four-part scorecard**: Structure / argument / style / mechanics with brief rationale.
- **Prioritized revision suggestions**: Issue + quote + options.
- **Highlighted strengths**: What works and why.
- **Next-step suggestions**: What to do next.

## Subskill References

| Subskill | Path | When to call |
|---|---|---|
| structure-analysis | `./structure-analysis/SKILL.md` | Step 3: Analyze organization and logic flow |
| argument-strengthening | `./argument-strengthening/SKILL.md` | Step 4: Assess and strengthen argument chain |
| style-refinement | `./style-refinement/SKILL.md` | Step 5: Polish wording, tone, sentences |

## External Skill Linkage

| Trigger | Target skill | Note |
|---|---|---|
| Weak argumentation | `→ debate-roleplay-learning` | Practice argumentation |
| User needs to organize topic first | `→ study-guide-creator` | Clarify knowledge before writing |
| Repeated same-type errors | `→ memory-comprehension-coach` | Consolidate writing habits |
| Writing is part of a project | `→ project-based-tutor` | As milestone deliverable |

## Errors and Boundaries

- **No draft and vague topic**: Guide brainstorming; don't demand a full draft at once.
- **Academic integrity**: Do not write full paragraphs for the user. Give suggestions and examples; user applies changes.
- **Very long text** (e.g., 10k words): Work by section; give overall structure first, then chapter-level feedback.
- **Mixed languages**: Recommend one main language; allow technical terms in original language.
- **User emotionally attached**: Increase the praise layer; introduce critique gradually.

## Example

### Example 1: Essay revision

**User**: "I wrote a 1200-word essay on AI in education. Can you review it?"

**Agent**:
1. Load framework = argumentative essay.
2. Four-part scan: structure 7/10 (clear sections but no counterargument), argument 5/10 (mostly personal experience, little data), style 8/10 (tone and flow fine), mechanics 9/10 (few errors).
3. Call `→ structure-analysis`: missing counterargument and rebuttal.
4. Call `→ argument-strengthening`: suggest adding UNESCO 2024 data and a Stanford AI-in-education case.
5. Sandwich feedback: ✅ Strong hook and conclusion; 🔴 Add a counterargument (e.g., "AI may widen the digital divide"); 🟡 Replace some personal experience with statistics; 💡 "Want to revise and resubmit, or practice argumentation first?" → `→ debate-roleplay-learning`

### Example 2: From scratch

**User**: "Help me write a polite but firm email declining an offer."

**Agent**:
1. Framework = business email, tone = formal + diplomatic.
2. Clarify: "What's your relationship with them? Why are you declining? Do you want to stay in touch?"
3. After answers, propose: Opening (thanks) → Core (clear no + brief reason) → Close (wish to stay in touch).
4. Offer 2 tone variants (warmer vs more formal) for the user to choose.
