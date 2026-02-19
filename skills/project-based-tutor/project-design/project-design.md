---
name: project-design
description: Design a stepwise learning project from subject, concepts, and user level; split into milestones and map concepts. Called by project-based-tutor in step 2.
tags: [project, design, milestone, deliverable, curriculum-design]
parent: project-based-tutor
---

# Project Design

> Subskill of `project-based-tutor` — called in step 2

## When to Use

- Called by `project-based-tutor` in step 2 "Project design."
- When a hands-on project is needed for a set of concepts.

## Input

- **subject**: Subject or topic.
- **target_concepts**: Concepts to cover (from `knowledge-extraction` or user).
- **difficulty**: Project difficulty.
- **project_type**: coding / analysis / design / writing / research / engineering.
- **time_budget**: Total time the user can spend.
- **tools**: Available tools/languages.
- **user_level**: Current level estimate.

## Steps

### 1. Ideate Projects

From concepts and project type, generate 2–3 options and pick the best:

**Criteria**:
| Dimension | Good project | Bad project |
|---|---|---|
| **Coverage** | ≥ 70% of target concepts | Only 1–2 concepts |
| **Deliverable** | Clear, meaningful output | Unclear what was done |
| **Progression** | Simple → complex | Hardest step first |
| **Splittable** | 3–7 checkable steps | All-or-nothing |
| **Relevance** | Real-world or engaging | Purely academic |
| **Feasible** | MVP in time budget | Too large |

**Templates by subject**:
| Subject | Example types |
|---|---|
| Programming | CLI tool, web app, API, data pipeline, algorithm viz |
| Data science | Dataset report, prediction model, dashboard |
| Engineering | System design, performance report, architecture doc |
| Business | Business plan, market analysis, case study |
| Humanities | Research paper, comparison, digital humanities |
| Science | Experiment design, simulation, literature review |

### 2. Split Into Milestones

Break the project into 3–7 milestones. Each milestone:

```yaml
milestone:
  id: M1
  title: "Load and explore data"
  description: "Load movie dataset from CSV; inspect size, columns, quality"
  target_concepts: ["Pandas read", "DataFrame attributes", "Descriptive stats"]
  bloom_level: L3
  estimated_time_min: 30

  deliverable:
    type: code
    description: "Jupyter cell with load and 5 exploratory commands"

  acceptance_criteria:
    - "Load data with pd.read_csv()"
    - "State row and column count"
    - "Identify at least 2 data quality issues"

  dependencies: []

  knowledge_link: "Textbook ch.3 'Loading and exploration'"
```

**Principles**:
1. **Progressive**: Each milestone adds 1–2 new concepts
2. **Testable**: Each has a verifiable deliverable
3. **Failure-safe**: Stuck on one milestone doesn’t invalidate earlier work
4. **Theory link**: Each milestone points to material/concept

### 3. Resources

Per milestone:
- **Data/artifacts**: Datasets, templates, starter code
- **References**: Relevant doc excerpts (from `viking://resources/`)
- **Environment**: Required tools and libraries (prefer what the user already has)

### 4. Calibrate Difficulty

Compare to user level:
- **Too hard**: Split milestones further or add more starter code
- **Too easy**: Merge simple milestones or add optional stretch
- Include at least one optional "challenge" milestone

## Output

```yaml
project:
  title: "Movie dataset analysis — from cleaning to insights"
  description: "Use Python + Pandas on a 5000+ movie dataset; clean, aggregate, visualize, and write short conclusions."
  target_concepts: ["Pandas", "Data cleaning", "GroupBy", "Matplotlib", "Analysis writing"]
  difficulty: intermediate
  estimated_time_min: 210
  deliverable: "Jupyter notebook + ~500-word analysis"
  tools_required: ["Python 3.x", "Pandas", "Matplotlib"]

milestones:
  - { id: M1, title: "Load and explore", time: 30min, concepts: [...], ... }
  - { id: M2, title: "Data cleaning", time: 45min, concepts: [...], ... }
  - { id: M3, title: "GroupBy analysis", time: 45min, concepts: [...], ... }
  - { id: M4, title: "Visualization", time: 45min, concepts: [...], ... }
  - { id: M5, title: "Write conclusions", time: 30min, concepts: [...], ... }
  - { id: "M-stretch", title: "(Optional) Prediction model", time: 60min, optional: true }

concept_coverage:
  total_target: 8
  covered: 7
  coverage_rate: 0.875
  uncovered: ["Advanced indexing (MultiIndex)"]
```

## Errors and Boundaries

- **Concepts don’t fit a project** (e.g., pure theory): Mark as "Learn outside project."
- **Tools unavailable**: Suggest alternatives (e.g., Google Colab if no local Jupyter).
- **Time too short for all milestones**: Label must-have vs nice-to-have and focus on core.
