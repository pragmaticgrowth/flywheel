# Reports and Research

Use this for research synthesis, concept explainers, feature deep-dives, status reports,
incident reports, post-mortems, and recurring updates.

## Research Synthesis

Use when multiple sources need to become a navigable artifact.

Layout:

- TL;DR with the answer and confidence.
- Source map/table: claim, evidence, source, date, caveat.
- Thematic sections with jump links.
- Comparison table when sources disagree.
- Decision implications or recommended next step.

For time-sensitive topics, include source dates and the date you checked them.

## Concept Explainer

Use when teaching a topic.

Layout:

- Title and one-paragraph TL;DR.
- Core insight as a highlighted sentence.
- Interactive demo if the concept is spatial/stateful/parameterized.
- Comparison to the naive approach with concrete numbers or properties.
- Glossary in margin or side panel.
- Tabbed examples if multiple languages/frameworks matter.

Do not write a Wikipedia page. Answer the user's likely question sharply, then expand.

## Feature or Repo Explainer

Use when explaining how a feature works in a codebase.

Layout:

- TL;DR: what it does, where it lives, key files.
- Request/data lifecycle with diagram.
- Collapsible phases.
- Annotated code snippets for load-bearing lines.
- FAQ.
- Where to look next.

## Status Report

Use for weekly/monthly updates or team status.

Layout:

- Header with team, date range, author.
- Shipped / in flight / blocked sections.
- Small chart, sparkline, or count strip.
- Asks separated visually.
- Risks and changes since last update.
- Footer with timestamp.

Items should be one line unless context is necessary.

## Incident Report or Post-Mortem

Layout:

- Header: incident name, severity, duration, customer impact.
- Timeline as the document spine.
- Root cause.
- Detection and response.
- What worked / what did not.
- Action items with owners and deadlines.
- Evidence appendix with logs or links.

Keep timestamps visible. Leadership should be able to read customer impact and action
items in under a minute.

## Common Mistakes

- Long linear prose without navigation.
- Unsupported claims in research.
- Burying the punchline below background.
- Incident reports without owners on follow-ups.
- Status reports where asks are mixed into general updates.
