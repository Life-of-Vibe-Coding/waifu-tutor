---
name: adaptive-difficulty
description: Adjust difficulty and Bloom level of subsequent questions in real time based on accuracy, speed, and concept performance. Called by exam-mode-tuner in step 5.
tags: [adaptive, difficulty, ZPD, IRT, real-time]
parent: exam-mode-tuner
---

# Adaptive Difficulty

> Subskill of `exam-mode-tuner` — called in step 5

## When to Use

- Called by `exam-mode-tuner` in `adaptive` mode after each answer.
- After each question, use cumulative performance to set next question parameters.

## Input

- **answer_history**: List of answered questions, each with:
  - question_id, bloom_level, difficulty, concept
  - correct: bool
  - time_taken_sec, estimated_time_sec
- **remaining_questions**: Count of questions left.
- **question_pool** (optional): Pool of questions with varying difficulty and Bloom.

## Steps

### 1. Real-Time Performance Metrics

Update after each answer:

**Sliding-window accuracy** (e.g., last 5):
```
recent_accuracy = correct_in_window / window_size
```

**Weighted accuracy** (more recent = higher weight):
```
weighted_accuracy = Σ(correct_i × decay^(n-i)) / Σ(decay^(n-i))
decay = 0.8
```

**Speed factor**:
```
speed_factor = estimated_time / actual_time
# > 1.0 = faster than expected (maybe too easy)
# < 0.5 = much slower (maybe too hard or deep thought)
```

**Per-concept scores**:
```
concept_scores = { concept: (correct / total) for each concept }
```

### 2. Difficulty Adjustment

Follow Zone of Proximal Development (ZPD): questions should be "doable with effort."

**Rules**:

| Recent accuracy | Speed factor | Action |
|---|---|---|
| ≥ 90% | > 1.2 | ⬆ Raise Bloom +1 and difficulty |
| 80–89% | 0.8–1.2 | ⬆ Raise difficulty (same Bloom) |
| 60–79% | 0.5–1.2 | → Keep (sweet spot) |
| 40–59% | < 0.8 | ⬇ Lower difficulty (same Bloom) |
| < 40% | any | ⬇ Lower Bloom -1 and difficulty |

**Limits**:
- Bloom between L1 and L6
- Difficulty: easy(1) → medium(2) → hard(3) → expert(4)
- After 3 wrong in a row: extra step down + encouraging message
- After 5 right in a row: extra step up + challenging message

### 3. Concept Rotation

Avoid long runs on one concept:

- Prefer concepts where `concept_scores` are lowest (fill gaps)
- Do not ask the same concept 2 questions in a row (fatigue + cueing)
- Mix in mastered concepts (≤ 20%) to maintain confidence

### 4. Select From Pool

From `question_pool`, pick best match for adjusted params:

```
score(q) = bloom_match(q)×0.4 + difficulty_match(q)×0.3
         + concept_priority(q)×0.2 + freshness(q)×0.1

next_question = argmax(score(q) for q in pool)
```

If no exact match, pick closest and note difficulty mismatch in feedback.

### 5. Output Next-Question Params

```yaml
next_question_params:
  target_bloom: L3
  target_difficulty: medium
  preferred_concept: "Tree traversal"
  avoid_concepts: ["Array operations"]
  reasoning: "Last 5 at 60% accuracy, slower—hold level, switch to weak concept"

performance_snapshot:
  overall_accuracy: 0.67
  recent_accuracy: 0.60
  speed_factor: 0.75
  weakest_concepts: ["Tree traversal", "Graph BFS"]
  strongest_concepts: ["Array", "Linked list"]
  mood_signal: "neutral"
```

## Output

- **next_question_params**: Parameters for the next question.
- **performance_snapshot**: Current snapshot (for `performance-analytics`).
- **mood_signal**: Suggested tone (e.g., encouraging after correct streak, gentle after wrong streak).

## Errors and Boundaries

- **Pool exhausted**: Ask `question-generation` to generate more with new params.
- **Highly variable performance**: Use larger window (e.g., 8) to smooth noise.
- **All correct or all wrong**: Jump toward max or min difficulty to find level quickly.
