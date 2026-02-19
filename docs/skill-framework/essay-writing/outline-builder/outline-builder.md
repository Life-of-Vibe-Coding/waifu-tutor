---
name: outline-builder
description: Produce a thesis statement and an (N+2)-part outline (introduction, N body points, conclusion) for an essay. Called by essay-writing in step 2. N is given by body_count.
tags: [outline, thesis, structure, planning]
parent: essay-writing
---

# Outline Builder

> Subskill of `essay-writing` — called in step 2

## When to Use

- Called by `essay-writing` in step 2 "Build Outline."
- When the user only wants an outline or thesis before writing full paragraphs.
- When another skill needs a structured essay outline for a given topic and body count.

## Input

- **topic_or_prompt**: Required. Essay subject or question (e.g., "Should voting be mandatory?", "Effects of social media on teens").
- **body_count**: Required. Number of body paragraphs (e.g., 2, 3, 4, 5). Determines how many body_* entries the outline has.
- **stance** (optional): For argumentative/persuasive essays: `for` / `against` / `balanced`. Omit for expository.
- **audience** (optional): teacher / grader / general. Default: general academic.
- **source_context** (optional): If essay must be grounded in a document or reading, pass key claims or quotes to weave into the outline.

## Steps

### 1. Thesis Statement

- One or two sentences that state the main claim or purpose of the essay.
- For **argumentative**: Clear position (e.g., "Voting should be mandatory because it strengthens democracy, increases representation, and encourages civic habit.").
- For **expository**: Central idea or scope (e.g., "Social media affects teenagers’ mental health, relationships, and self-image in both positive and negative ways.").
- Thesis must be specific enough to drive **body_count** distinct body points; avoid overly broad or vague statements.

### 2. Introduction Outline

Define what the introduction paragraph will do:

- **Hook**: How to open (question, statistic, quote, or scenario) to engage the reader.
- **Context**: One or two sentences of background so the reader understands the topic.
- **Thesis**: Restate the thesis (it will appear verbatim or in close form in the final intro paragraph).

### 3. Body Outlines (N points)

For each of the **body_count** body paragraphs (i = 1 … N):

- **Main point**: One clear claim that supports the thesis (topic sentence idea).
- **Support**: Type of support (example, statistic, quote, comparison) and brief note on content.
- **Analysis**: How this point connects back to the thesis or why it matters.

Rules:

- Each body point must be distinct (no overlap).
- Logical order: e.g., strongest last, or chronological, or problem → causes → solutions.
- Balance: no one body point should dominate; similar depth for all.

### 4. Conclusion Outline

Define what the conclusion paragraph will do:

- **Restate thesis**: Rephrase the thesis (do not copy-paste; show synthesis).
- **Summarize**: One sentence recalling the N body points.
- **Closing thought**: Call to action, implication, question, or forward-looking statement.

### 5. Quality Check

- [ ] Thesis is debatable or informative (not a fact or tautology).
- [ ] All N body points directly support the thesis.
- [ ] Body points are parallel in structure (e.g., all "reasons" or all "effects").
- [ ] Conclusion does not introduce new arguments; it only restates and closes.

## Output

Produce **outline.introduction**, **outline.body_1** … **outline.body_N** (where N = body_count), and **outline.conclusion**. Example for body_count = 3:

```yaml
thesis: "One or two sentences stating the main claim or purpose."
outline:
  introduction:
    hook: "Opening idea (e.g., question or statistic)."
    context: "Background in one or two sentences."
    thesis: "Same as thesis above (for placement in intro)."
  body_1:
    main_point: "First supporting claim."
    support: "Example/evidence note."
    analysis: "Link back to thesis."
  body_2:
    main_point: "Second supporting claim."
    support: "Example/evidence note."
    analysis: "Link back to thesis."
  body_3:
    main_point: "Third supporting claim."
    support: "Example/evidence note."
    analysis: "Link back to thesis."
  # ... body_4, body_5, ... as needed for body_count
  conclusion:
    restate_thesis: "Rephrased thesis."
    summarize: "One sentence for the N body points."
    closing: "Final thought or call to action."
```

## Errors and Boundaries

- **Topic too broad**: Narrow to a specific angle (e.g., "Climate change" → "Role of carbon taxes in reducing emissions").
- **Topic too narrow for requested body_count**: Suggest a smaller body_count or expand to a larger theme with more sub-angles.
- **User gives conflicting stance**: Use the most recent or explicit stance and note the choice.
- **Source-based essay**: Weave source_context into body support notes so paragraph-generator can cite or paraphrase.
