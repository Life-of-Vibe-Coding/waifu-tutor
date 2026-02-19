---
name: study-guide-creator
description: Create study outlines and guides from documents or topics; extract concepts, map prerequisites, and plan review.
---

# Study Guide Creator

## When to Use

- User uploads documents and asks "Help me create a study outline," "Make a study guide," or "Plan my review."
- User names a topic or subject and wants a systematic knowledge structure.
- Before an exam: extract key concepts, priorities, and time allocation from materials.
- User says "I don't know where to start," "Help me see the big picture," "This course has too many topics."
- Other skills suggest clarifying knowledge first (e.g., `→ project-based-tutor` when foundations are weak).
- User has just uploaded a lot of material and needs a global view of structure.

## Steps

### 1. Define Scope and User Profile

- Confirm documents, sections, or topic.
- If document ID: fetch L1 overview from `viking://resources/users/{user_id}/documents/{doc_id}`.
- If free topic: use conversation and long-term memory (`viking://user/memories`) for subject preferences.
- Ask if missing: stage (beginner / review / exam prep), prior knowledge (none / some / learned but forgot), goal (pass / deep understanding / application).

### 2. Knowledge Extraction and Structure → `knowledge-extraction`

Call subskill `→ knowledge-extraction/knowledge-extraction.md` to:
- Extract concept nodes from the document
- Identify hierarchy (chapter → topic → subtopic → term)
- Label cognitive level (Bloom: remember / understand / apply / analyze / evaluate / create)
- Extract a key term glossary
- Output: concept list with `name`, `level`, `bloom_level`, `importance_weight`

### 3. Prerequisite Map → `prerequisite-mapping`

Call subskill `→ prerequisite-mapping/prerequisite-mapping.md` to:
- Map prerequisite relations (A before B)
- Find concepts that can be learned in parallel
- Detect and break cycles
- Produce a topologically ordered learning path
- Output: dependency graph (DAG) + recommended order

### 4. Layered Outline

From steps 2–3, build a multi-level outline:

**Layer 1: Modules**
- Cluster concepts into 4–8 modules
- Name modules clearly (e.g., "Module 3: Memory management — virtual memory and paging")

**Layer 2: Per-module**
Each module includes:
- Core concepts (3–5) with one-sentence definitions
- Difficulty: basic ⬜ / intermediate 🟨 / challenge 🟥
- Prerequisites: which modules to do first
- Learning objectives: what the user should be able to do (Bloom verbs)
- Suggested activities: read / practice / discuss / hands-on (link to other skills)

**Layer 3: Detail** (when `depth=deep`)
- Expand each concept into 2–3 subpoints
- Add "common misconceptions" and "high-exam-frequency" tags
- Cross-references to other modules

### 5. Priorities and Strategy

For each module:
- **Importance** (★–★★★): exam frequency, foundational role, links to other concepts
- **Difficulty** (⬜🟨🟥): Bloom level + abstraction
- **Strategy**:
  - High importance + high difficulty → "Focus area"; suggest `→ memory-comprehension-coach`
  - High importance + low difficulty → "Quick review"; suggest `→ exam-mode-tuner` for quick checks
  - Low importance + high difficulty → "Strategic skip" when time is tight, or optional
  - Low importance + low difficulty → "Quick pass"; skim only

### 6. Time Planning → `time-allocation`

If user gives `time_budget` or `exam_date`:
- Call subskill `→ time-allocation/time-allocation.md` to:
  - Allocate time by module weight (importance × difficulty)
  - Produce daily/weekly plan
  - Insert review points (spaced repetition)
  - Reserve 15–20% buffer
- Output: calendar with dates + daily task list

### 7. Output and Next Steps

Present the guide in structured Markdown and suggest 2–3 next actions:

- "Start with module X; it's a prerequisite for the next three."
- "Want a diagnostic quiz to find weak spots?" → `→ exam-mode-tuner`
- "Should I turn key concepts into flashcards?" → `→ memory-comprehension-coach`
- "This module fits well with a project." → `→ project-based-tutor`

## Input

- **Document** (optional): Document ID or selected materials.
- **Topic/subject** (optional): When no document, user’s description of the topic.
- **Optional**:
  - `depth`: shallow / normal / deep (default normal)
  - `time_budget`: e.g., "10 hours," "3 days"
  - `exam_date`: for backward planning
  - `focus_areas`: weak spots or priorities
  - `prior_knowledge`: already mastered (skip those modules)
  - `goal`: pass_exam / deep_understanding / practical_application

## Output

- **Study guide** (Markdown):
  - Overview (short summary + module count + estimated total time)
  - Learning path (tree with dependency arrows)
  - Per-module cards (concepts, difficulty, priority, objectives, strategy)
  - Key term glossary (term + one-sentence definition + module)
  - Optional: time table, daily plan, review points
- **Next-step menu**: 2–3 concrete recommendations

## Subskill References

| Subskill | Path | When to call |
|---|---|---|
| knowledge-extraction | `./knowledge-extraction/knowledge-extraction.md` | Step 2: Extract concept structure from document/topic |
| prerequisite-mapping | `./prerequisite-mapping/prerequisite-mapping.md` | Step 3: Build concept dependencies |
| time-allocation | `./time-allocation/time-allocation.md` | Step 6: Allocate time to modules |

## External Skill Linkage

| Trigger | Target skill | Note |
|---|---|---|
| User wants a diagnostic first | `→ exam-mode-tuner` | Quiz then plan |
| Module marked "focus" | `→ memory-comprehension-coach` | Deep understanding |
| Module suits hands-on | `→ project-based-tutor` | Design a project |
| User wants argument/debate practice | `→ debate-roleplay-learning` | Deepen via debate |
| User asks for "flashcards for key points" | `→ memory-comprehension-coach` | Spaced repetition cards |

## Errors and Boundaries

- **Empty or very short document**: Ask for more material or topic description; for free topic, produce a generic outline and note "Refine after uploading specific materials."
- **Topic too broad** (e.g., "Help me learn math"): Narrow with 1) branch (algebra/geometry/calculus/stats?), 2) level (high school/undergrad/contest?), 3) goal (exam/interest/work).
- **Time too short for full coverage**: Set priorities; label "must learn," "recommended," "optional."
- **User has partial background**: Mark skippable modules as "Already mastered (optional review)."
- **Multiple documents**: Merge concept nodes, deduplicate, rebuild dependency graph.

## Example

### Example 1: Exam review

**User**: "I uploaded an OS textbook PDF. Exam next week. I have about 15 hours. Make a review plan."

**Agent**:
1. Call `→ knowledge-extraction`; get document overview; extract ~28 concept nodes.
2. Call `→ prerequisite-mapping`: e.g., process management → sync → deadlock; memory basics → virtual memory → paging.
3. Form 6 modules with difficulty and importance: e.g., process ★★★ ⬜, memory ★★★ 🟥, deadlock ★★ 🟥, file system ★★ 🟨, I/O ★ ⬜, security ★ ⬜.
4. Call `→ time-allocation`: 15h → memory 4h, process 3h, deadlock 2.5h, file system 2h, I/O 1.5h, security 1h, buffer 1h.
5. Produce 7-day plan (~2h/day), review on days 4 and 7.
6. Ask: "Start with process management (prerequisite for three modules), or take a diagnostic quiz first?"

### Example 2: Free topic

**User**: "I want to learn machine learning but don’t know where to start."

**Agent**:
1. Narrow: "What’s your math background (linear algebra, probability, calculus)? Theory or applied?"
2. From answers, build a generic roadmap: Module 1 Python basics → Module 2 Math (linear algebra + probability) → Module 3 Classic ML → Module 4 Project.
3. Note: "If your math is strong, you can skim Module 2 and start at Module 3."
4. Suggest: "Want to learn by doing a small project?" → `→ project-based-tutor`