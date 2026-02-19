---
name: scenario-builder
description: Build debate motions or roleplay scenarios from the user's topic and learning goals; prepare evidence pool and interaction rules. Called by debate-roleplay-learning in step 2.
tags: [scenario, debate-topic, roleplay-scene, world-building, context]
parent: debate-roleplay-learning
---

# Scenario Builder

> Subskill of `debate-roleplay-learning` — called in step 2

## When to Use

- Called by `debate-roleplay-learning` in step 2 "Scenario building."
- When the user gives a vague topic that must be turned into a concrete motion or scenario.

## Input

- **topic**: User's topic or debate direction.
- **mode**: debate / socratic / roleplay.
- **document_id** (optional): Related document for evidence.
- **difficulty**: Opponent strength.
- **user_stance** (optional): User's desired side.

## Steps

### 1. Motion / Scenario Design

**Debate mode — motion design**:
- Turn the topic into a debatable proposition (two defensible sides, not a matter of fact)
- Good motion criteria:
  - ✅ Controversial (reasonable people can disagree)
  - ✅ Scoped (can be discussed in ~5 rounds)
  - ✅ Tied to learning content (uses target concepts)
  - ❌ Not factual ("Earth is round" — no debate)
  - ❌ Not purely value ("X is good/bad" — too subjective)

- Motion templates:
  - Policy: "Should [policy] … / Should not …"
  - Comparison: "[A] is more [criterion] than [B]"
  - Causal: "[Cause] led to [effect]"
  - Definition: "[X] should be defined / classified as [Y]"

**Roleplay mode — scenario design**:

```yaml
scenario:
  title: "1929 Wall Street crisis — President Hoover's cabinet meeting"
  setting: "October 29, 1929, White House cabinet room"
  background: |
    The stock market has just crashed; Dow fell 12% in a day.
    Bank runs are spreading. Unemployment is rising.
    The president must decide today.

  roles:
    user:
      character: "Herbert Hoover, US President"
      goal: "Stabilize without violating laissez-faire principles"
      knowledge_needed: ["Classical economics", "Laissez-faire", "Fed role"]
    tutor:
      character: "Treasury Secretary Andrew Mellon"
      stance: "Liquidationist — let the market correct"
      hidden_agenda: "Expose limits of laissez-faire through dialogue"

  learning_objectives:
    - "Understand 1929 policy responses"
    - "Compare laissez-faire vs interventionist thinking"
    - "Analyze decision-making under uncertainty"

  key_decision_points:
    - turn: 3
      question: "Should interest rates be lowered?"
    - turn: 5
      question: "Should a public works program be launched?"
```

### 2. Evidence Pool

Extract usable evidence from documents and general knowledge:

```yaml
evidence_pool:
  pro_stance:
    - type: statistic
      content: "US GDP grew ~4.2% annually in the 1920s, free-market period"
      strength: A
      source: "Economic history data"
    - type: theory
      content: "Adam Smith's invisible hand"
      strength: B
      source: "Wealth of Nations"

  contra_stance:
    - type: case_study
      content: "2008 crisis: government intervention (TARP) stabilized finance"
      strength: S
      source: "Fed reports"
    - type: statistic
      content: "Nordic countries: high tax, high welfare, high GDP and well-being"
      strength: A
      source: "OECD 2023"

  common_ground:
    - "Markets allocate resources well in most cases"
    - "Unregulated markets have periodic crises"
```

### 3. Interaction Rules

```yaml
rules:
  rounds: 5
  format:
    opening: "Each side 2–3 sentences stating position"
    exchange: "Each side 3–5 sentences per round"
    closing: "Each side 2–3 sentences summary"

  scoring_dimensions:
    - name: "Logic"
      weight: 0.3
      description: "Clear structure, valid reasoning"
    - name: "Evidence use"
      weight: 0.25
      description: "Relevant, strong, sourced evidence"
    - name: "Rebuttal"
      weight: 0.25
      description: "Effective response to opponent's points"
    - name: "Clarity and civility"
      weight: 0.2
      description: "Clear expression, respectful tone"

  tutor_behavior:
    difficulty_mapping:
      gentle:
        max_arguments_per_turn: 1
        uses_questions: true
        acknowledges_user_points: always
      balanced:
        max_arguments_per_turn: 2
        uses_questions: sometimes
        acknowledges_user_points: sometimes
      aggressive:
        max_arguments_per_turn: 3
        uses_questions: rarely
        acknowledges_user_points: rarely
        uses_rapid_fire: true
```

## Output

- **scenario_config**: Full scenario (motion/scene + roles + rules).
- **evidence_pool**: Categorized evidence.
- **learning_objectives**: Learning goals for this session.
- **scoring_rubric**: Scoring dimensions and weights.

## Errors and Boundaries

- **Topic is purely factual**: Suggest Socratic mode (deepen understanding) instead of debate.
- **Sensitive politics/religion**: Use a neutral frame; ensure both sides have a reasonable basis; state educational purpose.
- **User unfamiliar with topic**: Give a short background (2–3 paragraphs) so they can participate.
