---
name: exam-mode-tuner
description: Simulate exam conditions; generate multi-format questions by Bloom level, adapt difficulty, and analyze weak points with links to other skills. Use when the user asks for "practice exam," "give me a quiz," or "test me."
tags: [exam, quiz, test, assessment, adaptive, tutor, study, bloom]
subskills:
  - question-generation
  - adaptive-difficulty
  - performance-analytics
---

# Exam Mode Tuner

## When to Use

- User asks for a practice exam: "Give me a practice test," "Test how well I've learned."
- User is preparing for an exam and wants timed practice and immediate feedback.
- User finishes a module and wants to check mastery.
- User says "I think I've got it—verify," "Give me some hard questions."
- Called by `→ study-guide-creator` in step 7: diagnostic quiz to find weak spots.
- Called by `→ memory-comprehension-coach` in step 5: spaced review quizzes.
- Called by `→ project-based-tutor` after milestones: verify mastery.

## Steps

### 1. Set Exam Parameters

**Scope**:
- If document ID: fetch from `viking://resources/users/{user_id}/documents/{doc_id}`.
- If topic: use conversation and learning history.
- If called by another skill: use the scope and concept list passed in.

**Parameters** (if user doesn’t specify):
- Question count: default 10; quick quiz 5; full practice 20–30
- Question type mix: recommend by subject (see step 2)
- Time limit: from count × average time, or user-specified
- Difficulty: `fixed` or `adaptive` (default)
- Feedback: `immediate` (per question) or `batch` (after all)

### 2. Question Generation → `question-generation`

Call subskill `→ question-generation/question-generation.md` to:
- Generate questions distributed across Bloom levels
- Ensure concept coverage ≥ 80% (core concepts must appear)
- Attach metadata per question: concept, Bloom level, estimated difficulty, estimated time
- Quality check: unambiguous, single correct answer (objective) or clear rubric (subjective)

### 3. Exam Flow

**Per-question mode (immediate)**:
```
→ Show question 1
← User answers
→ Immediate feedback (correct/incorrect + explanation + correct answer)
→ Adjust next question difficulty (→ adaptive-difficulty)
→ Show question 2
... repeat to end
```

**Batch mode**:
```
→ Show all questions
→ (Optional) Start timer; remind at 50% and 80% of time
← User answers one by one or submits all
→ Grade all + summary feedback
```

**During exam**:
- Timed: Remind at 50% and 80% ("X minutes left; you've done Y questions.")
- User stuck: Gentle "Want to skip this one?" (don’t give the answer)
- User quits: Save progress and partial answers for later

### 4. Grading

**Objective (choice/fill/true-false)**:
- Auto grade
- Per question: correct answer + why it’s correct + concept
- For wrong options: possible misconception

**Subjective (short answer/essay)**:
- Score by rubric dimensions, e.g.:
  - Accuracy (40%)
  - Completeness (25%)
  - Clarity (15%)
  - Depth/insight (20%)
- Provide model answer (labeled "Sample; yours need not match exactly")
- Note strengths and gaps in the user’s answer

### 5. Adaptive Difficulty → `adaptive-difficulty`

Call subskill `→ adaptive-difficulty/adaptive-difficulty.md` to:
- Track accuracy and speed in real time
- Adjust Bloom level and difficulty of later questions
- Keep questions in the "zone of proximal development": slightly above current level

### 6. Post-Exam Analysis → `performance-analytics`

Call subskill `→ performance-analytics/performance-analytics.md` to:
- Produce multi-dimensional report
- Identify weak concepts and error patterns
- Compare to past tests if available
- Suggest next steps and skill links

### 7. Follow-up Paths

From `performance-analytics`, recommend:

| Post-exam state | Action | Target skill |
|---|---|---|
| Score < 60%, multiple weak areas | Restudy | `→ study-guide-creator` (focus weak modules) |
| Same concept wrong repeatedly | Deepen / consolidate | `→ memory-comprehension-coach` |
| Score 60–80%, weak on essays | Argument/expression | `→ debate-roleplay-learning` / `→ writing-coach` |
| Score > 80%, want more | Apply | `→ project-based-tutor` |
| Score > 90% | Congratulate + harder test or new chapter | `→ exam-mode-tuner` (raise difficulty) |

## Input

- **Document/topic**: Document ID or user-defined scope.
- **concept_list** (optional): From `knowledge-extraction` when called by another skill.
- **Optional**:
  - `question_count`: default 10
  - `question_types`: e.g. ["choice", "fill_blank", "short_answer", "true_false", "essay"]
  - `difficulty`: easy / medium / hard / adaptive (default adaptive)
  - `bloom_distribution`: e.g. {remember: 2, understand: 3, apply: 3, analyze: 2}
  - `time_limit`: minutes, or null for untimed
  - `mode`: immediate / batch
  - `history_id` (optional): Previous test ID for comparison and avoiding repeats

## Output

- **Question list**: Stem, options, metadata (concept, Bloom, difficulty).
- **Per-question feedback**: Correct/incorrect + explanation.
- **Performance report** (from performance-analytics): see subskill output.
- **Personalized suggestions**: Next learning steps from performance.

## Subskill References

| Subskill | Path | When to call |
|---|---|---|
| question-generation | `./question-generation/question-generation.md` | Step 2: Generate questions |
| adaptive-difficulty | `./adaptive-difficulty/adaptive-difficulty.md` | Step 5: Adjust difficulty in real time |
| performance-analytics | `./performance-analytics/performance-analytics.md` | Step 6: Post-exam report |

## External Skill Linkage

| Trigger | Target skill | Note |
|---|---|---|
| Multiple weak areas, need structured review | `→ study-guide-creator` | Focus on weak modules |
| Same concept wrong repeatedly | `→ memory-comprehension-coach` | Deepen understanding / consolidate |
| Weak on essay/long-answer | `→ writing-coach` | Improve written argument |
| Weak on oral argument | `→ debate-roleplay-learning` | Debate practice |
| Solid base, want application | `→ project-based-tutor` | Project-based practice |

## Errors and Boundaries

- **Material too thin for many questions**: Tell user scope is narrow; suggest expanding or add only as many questions as material allows.
- **User quits mid-exam**: Save partial answers in session as "Incomplete"; allow resume or restart later.
- **Dispute over subjective grading**: Show rubric and reasoning; allow user to question; re-review and explain or adjust if appropriate.
- **Repeated tests in one session**: After 2+ tests, suggest a break or another mode.
- **Repeated questions**: Use `history_id` to avoid repeats (variants allowed).

## Example

### Example 1: Adaptive diagnostic

**User**: "Test my data structures; adaptive difficulty."

**Agent**:
1. Fetch user’s data-structures material; call `→ question-generation` for 12 mixed questions.
2. Start at medium (Bloom L2–L3): 4 choice + 4 fill + 4 short answer.
3. First 4 all correct → call `→ adaptive-difficulty`; move to L4–L5.
4. Questions 5–8 ~50% correct → hold at L3–L4.
5. After exam, call `→ performance-analytics`: e.g., 9/12 (75%); strong: arrays, linked list; weak: tree traversal (0/2), graph shortest path (0/1).
6. Suggest: "Tree traversal needs focus. Want to use the Feynman technique on recursive traversal?" → `→ memory-comprehension-coach`

### Example 2: Timed practice exam

**User**: "Linear algebra exam tomorrow. Full practice, 20 questions, 60 minutes."

**Agent**:
1. Call `→ question-generation` with Bloom mix matching real exam.
2. Batch mode; start 60-minute timer.
3. At 30 min: "Half time; you're on question 12; on track."
4. At 50 min: "10 minutes left; 3 questions unanswered."
5. Grade and run `→ performance-analytics` for full report.
