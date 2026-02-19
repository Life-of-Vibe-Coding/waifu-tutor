---
name: paragraph-generator
description: Generate a single essay paragraph (introduction, body, or conclusion) from an outline point and thesis. Called by essay-writing.
tags: [paragraph, writing, introduction, body, conclusion]
parent: essay-writing
---

# Paragraph Generator

> Subskill of `essay-writing` — called in steps 3–5 for each paragraph

## When to Use

- Called by `essay-writing` once per paragraph (intro, body 1, body 2, body 3, conclusion).
- When the user wants only one paragraph expanded from an outline (e.g., "Write just the introduction").
- When revising a single paragraph within an existing 5-paragraph essay.

## Input

- **role**: Required. One of `introduction` | `body` | `conclusion`.
- **thesis**: Required. The essay’s thesis statement (for consistency and transitions).
- **outline_point**: Required. The outline content for this paragraph (structure depends on role; see Steps).
- **paragraph_index** (for role=body): 1-based index among body paragraphs (1 = first body, 2 = second, …). Total body count is determined by the outline from outline-builder.
- **previous_paragraph_summary** (optional, for body): One-sentence summary of the previous paragraph for transition.
- **body_summaries** (optional, for conclusion): One sentence per body paragraph for recap.
- **length**: short (3–5 sentences) | standard (5–7) | long (7–10). Default: standard.
- **style**: formal | semi-formal | personal. Default: formal.
- **source_context** (optional): If the essay uses sources, pass relevant quotes or claims for this paragraph.

## Steps

### 1. Role-Specific Structure

**Introduction (role=introduction)**:

- **Hook**: First 1–2 sentences — question, statistic, quote, or scenario to engage.
- **Context**: 1–2 sentences of background.
- **Thesis**: Place thesis at or near the end of the paragraph (last 1–2 sentences).
- No new arguments; set up the essay only.

**Body (role=body)**:

- **Topic sentence**: First sentence states the main point (from outline_point.main_point).
- **Support**: 2–4 sentences — evidence, example, or explanation (from outline_point.support).
- **Analysis**: 1–2 sentences linking evidence to the thesis (from outline_point.analysis).
- **Transition** (if paragraph_index > 1): Use previous_paragraph_summary to lead into this paragraph smoothly. For paragraph_index = 1, no transition from a prior body paragraph is needed.

**Conclusion (role=conclusion)**:

- **Restate thesis**: Rephrase the thesis (do not copy verbatim).
- **Summarize**: Briefly recall the body points (use body_summaries if provided; count matches the number of body paragraphs in the essay).
- **Closing**: One sentence — implication, call to action, or forward-looking thought.
- No new arguments or evidence.

### 2. Writing Rules

- **Length**: Respect the `length` parameter (sentence counts as in Input).
- **Style**: Match `style` (formal: no contractions, neutral tone; semi-formal: some contractions; personal: first person allowed if appropriate).
- **Consistency**: Vocabulary and tone should match the thesis and the rest of the essay; avoid shifting stance or scope.
- **Transitions**: For body 2 and 3, include a clear transition from the previous paragraph.
- **Source use**: If source_context is provided, paraphrase or briefly quote; do not invent sources.

### 3. Quality Check

- [ ] Paragraph has one main idea (intro: setup + thesis; body: one point; conclusion: restate + close).
- [ ] No off-topic sentences.
- [ ] Sentences are varied in length and structure.
- [ ] For body: topic sentence is clear; support and analysis are present.

## Output

- **paragraph**: Full text of the single paragraph, ready to insert into the essay.
- **word_count** (optional): Approximate word count for the paragraph.

## Errors and Boundaries

- **Outline point too thin**: Expand from thesis and role to fill the requested length without inventing unrelated content.
- **Redundant with previous paragraph**: If paragraph_index > 1 and content overlaps, rephrase to focus on the distinct point and strengthen the transition.
- **Conclusion introduces new ideas**: Restrict to restating thesis, summarizing body points, and one closing thought; remove any new arguments.
