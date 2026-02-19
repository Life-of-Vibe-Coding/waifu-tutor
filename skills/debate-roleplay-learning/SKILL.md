---
name: debate-roleplay-learning
description: Deepen understanding through debate, Socratic questioning, and roleplay; train critical thinking and argumentation. Use when the user requests "debate/roleplay/simulation learning."
tags: [debate, roleplay, socratic, argumentation, simulation, tutor, critical-thinking]
subskills:
  - argumentation-engine
  - fallacy-detection
  - scenario-builder
---

# Debate & Roleplay Learning

## When to Use

- User requests debate-style learning: "Debate this with me," "Play devil's advocate."
- User wants to understand history, business, or social issues through roleplay.
- User needs to practice critical thinking, argumentation, or oral expression.
- User says "I think I get it—challenge me," "Simulate a scenario so I can practice."
- Recommended by `→ writing-coach` when the user's argumentation is weak and needs focused practice.
- Recommended by `→ exam-mode-tuner`'s `performance-analytics` when essay/long-answer performance is poor.

## Steps

### 1. Choose Mode and Build Scenario

**Three interaction modes**:

| Mode | Core mechanism | Best for | Learning goal |
|---|---|---|---|
| **Debate** | Tutor plays opposing side, structured back-and-forth | Controversial topics | Building arguments, handling rebuttals |
| **Socratic** | Tutor only asks questions, no assertions | Deepening concepts, exposing gaps | Deep thinking, self-correction |
| **Roleplay** | Both sides play defined roles | History/business/social scenarios | Situational understanding, applying knowledge |

If the user does not specify a mode, recommend one from context.

### 2. Scenario Building → `scenario-builder`

Call subskill `→ scenario-builder/scenario-builder.md` to:
- Extract debatable propositions or simulatable scenarios from the user's topic/documents
- Define roles, positions, and background for both sides
- Prepare an evidence pool (key arguments from documents and general knowledge)
- Set rules (rounds, scoring dimensions, difficulty)
- Output: full scenario + evidence pool + rules

### 3. Run the Interaction

**Debate mode**:
```
Round 1: Opening statements
  → User states position (2–3 main points)
  ← Tutor calls → argumentation-engine to build rebuttal

Round 2–N: Exchange
  → User rebuts Tutor's points
  ← Tutor calls → fallacy-detection on user's argument
  ← Tutor calls → argumentation-engine for new rebuttal
  ← Adjust rebuttal strength based on user performance

Final Round: Closing
  → User summarizes position
  ← Tutor summarizes → move to debrief
```

**Difficulty adaptation**:
| User performance | Tutor strategy |
|---|---|
| Strong arguments, precise rebuttals | Increase challenge; introduce harder counterexamples and edge cases |
| Reasonable but with gaps | Target gaps; hint at how to strengthen |
| Weak or off-topic | Lower intensity; use Socratic questions to steer back |
| Frustrated or emotional | Pause debate; switch to Socratic mode |

**Socratic mode**:
```
→ User states view
← Tutor asks deeper questions:
   - Premise: "What must be true for your claim to hold?"
   - Boundary: "What if X? Does your conclusion still hold?"
   - Counterexample: "Can you think of a case where it doesn't?"
   - Causation: "Is this causation or just correlation?"
   - Definition: "What do you mean by 'fair' here?"
→ User answers → Tutor follows up or confirms
→ Repeat until user reaches deeper understanding or revises view
```

**Roleplay mode**:
```
→ scenario-builder sets scene and roles
→ Tutor opens in character
← User responds in character
→ Weave in learning points naturally
→ At key decisions: "At this point X did Y. Why do you think so?"
→ After scene: step out of character → knowledge recap
```

### 4. Live Argument Analysis → `argumentation-engine` + `fallacy-detection`

Run continuously during the interaction:

- `→ argumentation-engine`: Analyze both sides' argument quality; build Tutor's replies
- `→ fallacy-detection`: Detect logical fallacies in the user's arguments in real time
- Do not interrupt to point out fallacies; log them for the debrief

### 5. Summary and Debrief

**Argument debrief report**:

```
📊 Debate debrief: Free market vs government intervention
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Argument comparison:
┌─────────────┬──────────────────┬──────────────────┐
│             │ Your points (free market) │ Tutor (intervention) │
├─────────────┼──────────────────┼──────────────────┤
│ Point 1     │ Market efficiency │ Market failure counterexamples │
│ Point 2     │ Innovation incentives │ Public goods underprovision │
│ Point 3     │ Consumer sovereignty │ Information asymmetry │
└─────────────┴──────────────────┴──────────────────┘

🎯 Argumentation assessment:
  • Logic:        ★★★★☆ (Clear structure, valid reasoning)
  • Evidence use: ★★★☆☆ (More theory than data)
  • Rebuttal:     ★★☆☆☆ (Did not address "externalities" well)
  • Clarity:      ★★★★☆ (Clear expression)
  • Acknowledging opposition: ★★☆☆☆ (Little recognition of valid counterpoints)

⚠️ Logical issues detected:
  1. [Round 2] False dichotomy — framed as "free market vs full central planning"
  2. [Round 3] Cherry-picking — only cited free-market success cases

💡 Suggestions:
  1. Acknowledge valid counterpoints ("Although market failure is real…") to strengthen credibility
  2. Add data (indicators, cross-country studies) to support theoretical points
  3. Address "externalities" — this was your main gap

📚 Concepts covered:
   Market failure · Externalities · Public goods · Keynesian multiplier · Invisible hand · Information asymmetry
```

### 6. Follow-up Paths

| Debrief finding | Recommendation | Target skill |
|---|---|---|
| Weak argumentation | More debate practice | Another round `→ debate-roleplay-learning` |
| Want to turn arguments into an essay | Writing support | `→ writing-coach` |
| Concepts not mastered | Concept reinforcement | `→ memory-comprehension-coach` |
| Want a structured guide | Study guide | `→ study-guide-creator` |
| Want to test mastery | Quiz/test | `→ exam-mode-tuner` |

## Input

- **Topic/motion**: Debate proposition or roleplay scenario description.
- **Document** (optional): Related material ID.
- **Optional parameters**:
  - `mode`: `debate` / `socratic` / `roleplay`.
  - `stance`: Tutor's position (`for` / `against` / `auto`).
  - `role_description`: Role setup in roleplay mode.
  - `rounds`: Number of rounds (default 5).
  - `difficulty`: Opponent strength (`gentle` / `balanced` / `aggressive`).
  - `language`: Language of the interaction.
  - `focus_skills`: Focus areas (`argumentation` / `rebuttal` / `evidence_use` / `critical_thinking`).

## Output

- **Interaction log**: Structured full transcript.
- **Argument debrief**: Comparison + assessment + logical issues + suggestions.
- **Concepts covered**: List of concepts used in the interaction.
- **Progress tracking** (if history exists).

## Subskill References

| Subskill | Path | When to call |
|---|---|---|
| argumentation-engine | `./argumentation-engine/argumentation-engine.md` | Build Tutor arguments + assess user argument quality |
| fallacy-detection | `./fallacy-detection/fallacy-detection.md` | Detect logical fallacies in real time |
| scenario-builder | `./scenario-builder/scenario-builder.md` | Step 2: Build debate/roleplay scenario |

## External Skill Linkage

| Trigger | Target skill | Note |
|---|---|---|
| Turn debate points into an essay | `→ writing-coach` | Argumentation → written expression |
| Concepts not mastered | `→ memory-comprehension-coach` | Concept reinforcement |
| Want a study guide for the domain | `→ study-guide-creator` | Generate study guide |
| Want to test mastery | `→ exam-mode-tuner` | Generate quiz |

## Errors and Boundaries

- **Sensitive topics**: Stay neutral and educational; base discussion on logic and facts; avoid extreme positions. State clearly: "The position I play is for practice, not my own view."
- **User upset**: Lower intensity; switch to Socratic mode; use questions to cool down.
- **Roleplay drifts from learning**: Pause the scene, remind of learning goals, then continue.
- **Content beyond materials**: Note "The following is general knowledge; check authoritative sources."
- **User cannot argue effectively**: Switch from debate to Socratic (softer), or suggest learning argumentation basics first.

## Example

**User**: "I'm learning economics and think free markets are always better than government intervention. Play a Keynesian and challenge me, aggressive difficulty."

**Agent**:
1. Call `→ scenario-builder` to set motion and evidence pool.
2. Debate mode, aggressive, 5 rounds.
3. During the session, keep calling `→ argumentation-engine` and `→ fallacy-detection`.
4. Produce full debrief.
5. Suggest: "Want to try Socratic mode on externalities, or turn your arguments into an essay?" → `→ writing-coach`
