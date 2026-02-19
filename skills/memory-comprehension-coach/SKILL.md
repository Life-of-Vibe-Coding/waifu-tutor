---
name: memory-comprehension-coach
description: Use evidence-based methods (spaced repetition, active recall, Feynman technique, elaborative encoding, etc.) to strengthen memory and deep understanding; diagnose mastery level and plan review. Use when the user asks to "remember," "consolidate," or "I don’t get it."
tags: [memory, comprehension, spaced-repetition, recall, understanding, tutor, review, feynman, bloom]
subskills:
  - mastery-diagnosis
  - strategy-selector
  - spaced-repetition-scheduler
---

# Memory & Comprehension Coach

## When to Use

- User says "I keep forgetting this," "I forget right after learning," "Help me consolidate."
- User needs to understand, not just memorize, a complex concept ("I’ve read it several times and still don’t get it").
- After learning or an exam, user wants a long-term retention strategy.
- User asks "When should I review?" "Plan my review," "What’s the best way to remember?"
- Recommended by `→ exam-mode-tuner`'s `performance-analytics` when the same concepts are wrong repeatedly.
- Recommended by `→ study-guide-creator` when a module is marked "Focus."
- Recommended by `→ project-based-tutor` when the user is stuck on a concept.

## Steps

### 1. Diagnose Mastery → `mastery-diagnosis`

Call subskill `→ mastery-diagnosis/mastery-diagnosis.md` to:
- Use 3–5 quick questions to assess mastery level
- Use Bloom + Solo taxonomy to classify
- Separate "don’t remember" vs "don’t understand" (different interventions)
- Output: mastery level (1–5) + evidence + obstacle type

### 2. Classify Knowledge Type

Match the target knowledge to the best strategy:

| Type | Definition | Example | Best strategy direction |
|---|---|---|---|
| **Declarative** | Facts, definitions, terms | "HTTP 200 means success" | Spaced repetition, memory palace |
| **Conceptual** | Principles, relations, models | "Encapsulation in OOP" | Feynman, elaborative encoding |
| **Procedural** | Steps, methods, algorithms | "Quicksort steps" | Practice, interleaving |
| **Metacognitive** | When to use what | "When to use mergesort vs quicksort" | Case analysis, debate |

### 3. Choose Strategy → `strategy-selector`

Call subskill `→ strategy-selector/strategy-selector.md` to:
- From mastery × knowledge type × user preferences, pick best strategy mix
- Choose 1 primary + 1 secondary strategy
- Output: strategy choice + rationale + parameters

### 4. Guided Practice — Execute Strategy

**Strategy A: Spaced repetition**
- Generate flashcards (front: question/term; back: answer/definition)
- Schedule by forgetting curve
- Record difficulty (easy / medium / hard / forgot) each time
- Call `→ spaced-repetition-scheduler` to update intervals

**Strategy B: Active recall**
```
Tutor: "Without looking, what are the three parts of recursion?"
User: (may be incomplete)
Tutor: "You said base case and recursive call; the third is 'smaller problem'—
        each call must shrink the problem or you get infinite recursion.
        Now say the full three in your own words?"
User: (tries again)
Tutor: "Good. I’ll ask again tomorrow to see what sticks."
```

**Strategy C: Feynman technique**
```
Step 1: "Explain eigenvalues in your own words, as if to a high-schooler."
Step 2: User tries → Tutor marks unclear parts
Step 3: "You said 'multiply by a number'—more precisely, an eigenvalue is
        the scale factor when the transformation only scales (doesn’t change direction)."
Step 4: "Try again with that in mind?"
Step 5: User improves → confirm or iterate
```

**Strategy D: Elaborative encoding**
```
Tutor: "How do stack and queue differ? Think of real-life analogies—stack like what? queue like what?"
User: "Stack like plates, queue like a line?"
Tutor: "Right. Now: browser Back button—why stack and not queue?"
User: (thinks and answers)
Tutor: "Yes—you want the most recent page (LIFO), not the oldest. So you’ve
        not only remembered the difference but when to use which."
```

**Strategy E: Memory palace / association**
```
Tutor: "OSI layers bottom to top: Physical–Data link–Network–Transport–Session–Presentation–Application.
        Map them to rooms at home:
        🚪 Door (Physical) → you physically open it
        🛋️ Living room (Data link) → links rooms
        🗺️ Hall (Network) → network of paths
        🚚 Elevator (Transport) → transports you
        💬 Meeting room (Session) → session
        🎨 Gallery (Presentation) → present/display
        📱 Study (Application) → apps
        
        Walk from door to study and name each layer?"
```

**Strategy F: Interleaving**
- Mix related but different concepts (e.g., stack and queue problems together)
- Forces discrimination and deepens understanding
- Call `→ exam-mode-tuner` for mixed question sets

### 5. Deepen Understanding (when the block is "don’t get it")

When the obstacle is comprehension, not recall:

1. **Decompose**: Break concept into 3–5 smaller parts
2. **Analogize**: Compare to everyday objects or situations
3. **Multi-perspective**: Give at least 2 different explanations
4. **Counter-example**: Use "what is not X" to bound the concept
5. **Progressive build**: Start from the simplest case and add complexity

Example for "virtual memory":
- Decompose: address space + page mapping + demand loading + page replacement
- Analogy: Library (disk), desk (RAM); you can’t hold all books; the "librarian" brings the one you need and takes back others
- Perspectives: programmer (each process thinks it has full memory), OS (maintains the illusion), hardware (MMU, TLB)
- Counter-example: Many embedded systems use physical addresses only
- Progressive: one process one page → one process many pages → many processes sharing RAM → page replacement

### 6. Schedule Review → `spaced-repetition-scheduler`

Call subskill `→ spaced-repetition-scheduler/spaced-repetition-scheduler.md` to:
- Use Ebbinghaus curve + SM-2–style algorithm
- Set initial interval from current performance
- Produce dated schedule
- Per review: format (flashcard / self-test / Feynman / short quiz)
- Link to `→ exam-mode-tuner` for key review quizzes

### 7. Track and Adapt

Track each review/practice:

```yaml
tracking:
  concept: "Eigenvalues and eigenvectors"
  history:
    - date: "2025-03-10"
      method: "Feynman"
      mastery_level: 2
      notes: "Could analogize but not formal definition"
    - date: "2025-03-11"
      method: "Active recall"
      mastery_level: 3
      notes: "Could state Ax=λx and explain"
    - date: "2025-03-14"
      method: "Practice"
      mastery_level: 4
      notes: "Could compute for 2×2"
    - date: "2025-03-21"
      method: "Application"
      mastery_level: 5
      notes: "Could explain why PCA uses eigenvalues"

  current_interval: 14 days
  next_review: "2025-04-04"
  strategy_effectiveness: "Feynman + elaborative encoding worked best"
```

**Adaptation**:
- Accuracy > 90% → double interval
- 60–90% → keep interval
- < 60% → halve interval + consider strategy change
- 3 reviews in a row < 40% → trigger deeper intervention (back to step 5)

## Input

- **Concept(s)**: What to remember or understand.
- **Document** (optional): Material ID for definitions.
- **Optional**:
  - `goal`: memorize / understand (default auto)
  - `strategy`: specific strategy or auto
  - `review_schedule`: whether to generate schedule (default true)
  - `difficulty_history`: from `→ exam-mode-tuner` for weak spots
  - `concepts_list`: multiple concepts (batch)

## Output

- **Mastery diagnosis**: Level 1–5 + obstacle type + evidence.
- **Strategy recommendation**: Primary + secondary + rationale.
- **Practice interaction**: Log of the session.
- **Review schedule** (from spaced-repetition-scheduler): Dated plan.
- **Progress**: Change in mastery over time.

## Subskill References

| Subskill | Path | When to call |
|---|---|---|
| mastery-diagnosis | `./mastery-diagnosis/mastery-diagnosis.md` | Step 1: Diagnose level |
| strategy-selector | `./strategy-selector/strategy-selector.md` | Step 3: Choose strategy |
| spaced-repetition-scheduler | `./spaced-repetition-scheduler/spaced-repetition-scheduler.md` | Step 6: Build schedule |

## External Skill Linkage

| Trigger | Target skill | Note |
|---|---|---|
| Need mixed quiz | `→ exam-mode-tuner` | Interleaving or review check |
| Need knowledge structure first | `→ study-guide-creator` | Then tackle concepts one by one |
| Concept suits debate | `→ debate-roleplay-learning` | Socratic deepening |
| Need hands-on to solidify | `→ project-based-tutor` | Apply in practice |
| Want to write it out | `→ writing-coach` | Written Feynman |

## Errors and Boundaries

- **User won’t try recall** ("Just tell me"): Gently encourage a guess ("Wrong guesses stick better"); if they insist, give the answer and schedule more frequent review.
- **Material has errors**: Note "Per your material"; correct when possible and suggest verification.
- **User ignores schedule long-term**: Don’t blame; propose a more realistic plan (e.g., 2 minutes/day).
- **Too many concepts** (> 10): Work in batches of 3–5; set priority.
- **Concepts confused** (e.g., stack vs queue): Use contrast—same first, then differences, then when to use which.

## Example

**User**: "I’ve read about eigenvalues and eigenvectors in linear algebra many times and still don’t get them."

**Agent**:
1. Call `→ mastery-diagnosis`: 3 quick questions → Level 2 (vague).
2. Knowledge type = conceptual.
3. Call `→ strategy-selector`: Primary = Feynman, secondary = elaborative encoding.
4. Guide: analogy (spring door → eigenvector = unchanged direction, eigenvalue = scale); Feynman "Explain Ax = λx"; counter-example "If the direction changes, it’s not an eigenvector."
5. Confirm improvement to Level 3–4.
6. Call `→ spaced-repetition-scheduler`: tomorrow write definition; in 3 days 2 calculation problems (→ exam-mode-tuner); in 7 days explain one application (e.g., PCA).
7. Add 3 flashcards to the schedule.
