---
name: essay-writing
description: Guides the user to produce a structured essay (introduction, N body paragraphs, conclusion). Use when the user asks to write an essay, draft an essay, or get help with essay structure. Number of body paragraphs is configurable.
---

# Essay Writing

## When to Use

- User asks to "write an essay," "draft an essay," or "help me write an essay on X."
- User provides a topic or prompt and wants a full essay with clear structure.
- User wants a classic structure (intro, body paragraphs, conclusion) with a chosen number of body paragraphs.
- Called by other skills when written argument or long-form output is needed (e.g., after `→ exam-mode-tuner` for essay practice).

## Steps

### 1. Clarify Topic and Parameters

- **Topic/prompt**: From user message or follow-up. If vague, ask for a specific topic or question.
- **Number of body paragraphs** (optional): User may request a specific count (e.g., 3, 4, 5). If not given, choose a reasonable default (e.g., 3) or infer from the prompt (e.g., "three reasons" → 3). Total paragraphs = 1 (intro) + N (body) + 1 (conclusion).
- **Audience** (optional): e.g., teacher, exam grader, general reader. Default: general academic.
- **Stance** (optional): For persuasive/argumentative essays: position to argue (for/against, or "balanced"). If not given, infer from prompt or ask.
- **Length** (optional): "short" (3–5 sentences per paragraph), "standard" (5–7), "long" (7–10). Default: standard.
- **Style** (optional): formal / semi-formal / personal. Default: formal academic.

Confirm with the user if the topic is ambiguous or if key choices (stance, audience, number of body paragraphs) are missing.

**HITL checkpoint (before outline):** Call `request_human_approval` with a summary of the chosen topic, body_count, audience, length, and style. Include these in `params` so the user can approve or modify before you generate the outline.

### 2. Build Outline → `outline-builder`

Call load_subskill with path `essay-writing/outline-builder/outline-builder.md`, then follow its Steps with **body_count** = N (from step 1). It will:

- Produce a **thesis statement** (one or two sentences) that states the main claim or purpose.
- Produce an **(N+2)-part outline**:
  - **Paragraph 1 (Introduction)**: Hook, context, thesis.
  - **Paragraphs 2 to N+1 (Body 1 … Body N)**: One main point + supporting idea per body paragraph.
  - **Paragraph N+2 (Conclusion)**: Restate thesis, summarize points, closing thought.

Ensure the outline is coherent and each body paragraph clearly supports the thesis.

**Transition (reflect, then continue):** The outline is an intermediate artifact — the full essay is not yet complete. Do NOT return the outline as the final response. Next: call `request_human_approval` for the HITL checkpoint, then call `load_subskill(essay-writing/paragraph-generator/paragraph-generator.md)` for Step 3.

**HITL checkpoint (after outline):** Call `request_human_approval` to present the thesis and outline to the user. In the summary, offer to proceed with the full essay or let them revise the outline. Do not proceed to paragraph generation until the user approves.

### 3. Generate Paragraph 1 (Introduction) → `paragraph-generator`

Call load_subskill with path `essay-writing/paragraph-generator/paragraph-generator.md`, then follow its Steps with:

- **role**: `introduction`
- **thesis**: From outline.
- **outline_point**: Introduction outline (hook, context, thesis).
- **length**: As chosen in step 1.
- **style**: As chosen in step 1.

Output: full introduction paragraph.

### 4. Generate Body Paragraphs → `paragraph-generator`

For each body paragraph i = 1 … N, use the paragraph-generator subskill (same path as step 3) with:

- **role**: `body`
- **paragraph_index**: i (1-based index among body paragraphs).
- **thesis**: From outline (for consistency).
- **outline_point**: The corresponding body point from the outline.
- **previous_paragraph_summary** (optional): One-sentence summary of the previous paragraph for transition (omit for i = 1).
- **length**, **style**: As in step 1.

Output: N body paragraphs, each with topic sentence, support, and analysis.

### 5. Generate Conclusion → `paragraph-generator`

Use the paragraph-generator subskill (same path as step 3) with:

- **role**: `conclusion`
- **thesis**: From outline.
- **outline_point**: Conclusion outline (restate thesis, summarize, closing).
- **body_summaries** (optional): One sentence per body paragraph for recap.
- **length**, **style**: As in step 1.

Output: full conclusion paragraph.

### 6. Assemble and Present

- Concatenate the (N+2) paragraphs in order (intro, body 1 … body N, conclusion).
- Present the full essay to the user with clear paragraph breaks.
- Optionally: offer a one-line summary of the essay and suggest one revision (e.g., transition between two body paragraphs).

### 7. Optional Revision

If the user asks to revise, shorten, or expand:

- Identify which paragraph(s) to change.
- Re-use the paragraph-generator subskill with updated outline_point or length; replace only those paragraphs and re-assemble.

## Input

- **topic_or_prompt**: Required. The essay subject or question (e.g., "Should schools require uniforms?", "Causes of the Industrial Revolution").
- **Optional**:
  - `body_count` or `num_body_paragraphs`: Number of body paragraphs (e.g., 2, 3, 4, 5). If omitted, use a default (e.g., 3) or infer from the user’s request.
  - `audience`: teacher / grader / general (default: general academic).
  - `stance`: for/against/balanced (for argumentative); omit for expository.
  - `length`: short / standard / long (default: standard).
  - `style`: formal / semi-formal / personal (default: formal).
  - `document_id` or **context**: If the essay must use specific source material, pass reference or content for outline-builder and paragraph-generator.

## Output

- **thesis**: The main thesis statement.
- **outline**: The (N+2)-part outline (for reference or editing).
- **essay**: Full text of (N+2) paragraphs, clearly separated (e.g., blank line or "Paragraph 1:", …).
- **optional**: Brief reflection or revision suggestion.

## Subskill References

| Subskill | Path (relative to skills root) | When to call |
|----------|-------------------------------|--------------|
| outline-builder | `essay-writing/outline-builder/outline-builder.md` | Step 2: Create thesis and outline with body_count = N |
| paragraph-generator | `essay-writing/paragraph-generator/paragraph-generator.md` | Steps 3–5: Generate intro, then each of the N body paragraphs, then conclusion |

## External Skill Linkage

| Trigger | Target skill | Note |
|---------|--------------|------|
| User needs to improve argument or structure | `→ writing-coach` | Deeper feedback on logic and style |
| Essay for exam practice | `→ exam-mode-tuner` | Timed essay + rubric grading |
| User wants to debate the topic first | `→ debate-roleplay-learning` | Argue then write |

## Errors and Boundaries

- **Topic too broad**: Narrow with the user (e.g., "Causes of WWII" → "Role of treaty of Versailles in the outbreak of WWII").
- **Topic too narrow for requested body count**: Suggest fewer body paragraphs or expand the topic; or use sub-angles of the same theme to fill N points.
- **Very large body count**: If N is very high (e.g., > 6), confirm with the user or suggest a more focused outline to keep the essay manageable.
- **Source-based essay**: Pass document/source context into outline-builder and paragraph-generator so claims are grounded in the material.

## Example

**User**: "Write an essay on why recycling matters with four body paragraphs."

**Agent**:

1. Confirm topic (recycling importance), body_count = 4, stance (e.g., "recycling matters" — for), audience and length (standard).
2. Call `request_human_approval` with summary of params (topic, body_count=4, audience, length). Wait for user to approve.
3. Call load_subskill(`essay-writing/outline-builder/outline-builder.md`) and follow its steps with body_count = 4: thesis + outline (intro; body 1–4: e.g., environment, economy, habit, policy; conclusion).
4. Call `request_human_approval` to present the outline. Wait for user to approve before writing paragraphs.
5. Call load_subskill(`essay-writing/paragraph-generator/paragraph-generator.md`) and follow its steps for intro → then body 1, 2, 3, 4 → then conclusion.
6. Assemble and show the full essay (6 paragraphs total) with paragraph labels or spacing.
7. Offer one short revision tip if relevant.
