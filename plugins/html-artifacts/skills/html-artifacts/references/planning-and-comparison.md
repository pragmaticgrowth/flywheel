# Planning and Comparison

Use this for alternatives, brainstorm grids, specs, RFCs, and implementation plans.

## Side-by-Side Options

Use when the user asks for approaches, alternatives, tradeoffs, or "what are the ways".

Layout:

- One column/card per option, using identical internal sections.
- Each option includes: summary, small concrete example, tradeoff table, hard metrics, and
  adoption cost.
- A recommendation block at the bottom that picks one option and explains why.

Hard rules:

- Generate meaningfully different options. If two options share most of the implementation,
  merge them or make the difference explicit as a parameter.
- Compare horizontally. Do not stack long option essays.
- Use hard criteria when possible: migration risk, time, testability, performance, UX,
  rollback, operational load.

## Brainstorm Grid

Use when the user is still deciding or asks for visual/design/copy/architecture
directions.

Layout:

- 3-6 options in a grid.
- Each cell renders an actual example, not a paragraph describing it.
- Each cell has a short caption naming the tradeoff it makes.
- Optional "choose this" button if the artifact is interactive; export the selected option,
  notes, and rationale.

Avoid six cosmetic variations of the same thing. Vary layout, density, workflow, and
information hierarchy before color.

## Implementation Plan

Use HTML by default for any stakeholder-ready or handoff-ready implementation plan.
This is the baseline failure the skill exists to fix: markdown plans become long linear
documents when the user needs a navigable artifact.

Required sections:

1. **Problem framing** - one paragraph.
2. **Recommended path** - a clear choice, not only options.
3. **Phase timeline** - visual strip with phases, gates, and owners/roles if known.
4. **Architecture/data-flow diagram** - inline SVG when more than two components interact.
5. **Implementation slices** - each slice with goal, files/areas, tests, and rollback.
6. **Risk table** - risk, likelihood, impact, mitigation, detection signal.
7. **Validation plan** - exact commands/checks where known, manual smoke where needed.
8. **Out of scope** - what this plan explicitly does not include.
9. **Open questions** - only the questions that change implementation.

Useful layouts:

- Timeline across the top, details below.
- Sticky side navigation for long plans.
- Data-flow SVG beside the implementation slices.
- Risk table with severity colors plus text labels.

Do not list every file in the repo. Name ownership areas and load-bearing files only.

## Spec or RFC

Use a document layout with sticky nav and sections:

- Context.
- Goals and non-goals.
- User/system behavior.
- Data model or API shape.
- Alternatives considered.
- Rollout and rollback.
- Test/verification strategy.
- Decision log.

For UI specs, include embedded mockups or state diagrams. For backend specs, include request
flow and failure paths.

## Common Mistakes

- Wrapping a markdown outline in a styled page.
- Comparing options with different criteria in each column.
- Refusing to recommend.
- Omitting the data-flow diagram because prose "explains it".
- Making the plan look like a marketing page instead of an implementable handoff.
