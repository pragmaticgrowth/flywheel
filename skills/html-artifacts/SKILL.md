---
name: html-artifacts
description: Use when the user asks for a non-trivial plan, spec, report, explainer, research synthesis, comparison, PR/code-review writeup, diagram, flowchart, timeline, roadmap, dashboard-like data view, slide deck, visual design exploration, prototype, playground, or one-off editor where spatial layout, color, interaction, or export back to the agent would beat markdown. Stay in markdown for short chat replies, code-only answers, command snippets, and tiny summaries.
---

# HTML Artifacts

Use HTML when the deliverable is something a person will inspect, compare, share,
present, manipulate, or hand to another agent. Markdown is still fine for quick chat
answers. The point is not "always output HTML"; the point is to use the medium that
makes the shape of the work visible.

This skill produces a single self-contained `.html` file unless the user explicitly asks
for a different file type. Do not inline-render the HTML in chat.

## First Move

1. Decide whether HTML is warranted:
   - Use HTML for comparisons, plans/specs, code review maps, diagrams, timelines,
     reports, research explainers, decks, prototypes, data explorers, and custom editors.
   - Use markdown for short answers, code/config-only output, shell-command instructions,
     or content the user will skim once and discard.
2. Read `references/foundation.md` before drafting any artifact.
3. Read the reference(s) that match the artifact type:

| Request shape | Read |
|---|---|
| Alternatives, brainstorm grids, specs, implementation plans, RFCs | `references/planning-and-comparison.md` |
| PR reviews, annotated diffs, PR descriptions, codebase tours, module maps | `references/code-review-and-understanding.md` |
| Design tokens, component variant sheets, UI mockups, motion or interaction prototypes | `references/design-and-prototypes.md` |
| Flowcharts, architecture maps, SVG figures, ERDs, timelines, roadmaps, data explorers | `references/diagrams-and-data.md` |
| Research synthesis, concept explainers, feature deep-dives, status reports, incidents | `references/reports-and-research.md` |
| One-off editors, triage boards, prompt tuners, config editors, dataset curators | `references/custom-editors.md` |
| Slide decks or meeting presentations | `references/decks.md` |
| Updating this skill, checking source coverage, or comparing prior art | `references/source-map.md` |

If the request spans categories, read all relevant references. For example, an
implementation plan with UI mockups and a data-flow diagram needs
`planning-and-comparison.md`, `design-and-prototypes.md`, and
`diagrams-and-data.md`.

## Output Contract

Every generated artifact must have:

- A descriptive kebab-case filename ending in `.html`.
- A clear title and one short framing paragraph at the top.
- Layout that uses the medium: side-by-side where comparison matters, real diagrams
  where relationships matter, controls where interaction matters.
- Inline CSS and JavaScript. No build step, no package install, no server.
- A responsive layout that works on narrow screens.
- A print/PDF fallback for durable documents.
- An export/copy button whenever the user manipulates state or chooses an option.
- A short final message with the saved path and what the user should do next.

For durable artifacts in a repo, prefer `docs/artifacts/<topic>.html` if that folder
exists or fits the repo. For throwaway editors or secret-adjacent data, use a temp file
or a gitignored path and say where it is.

## Core Decisions

### When HTML Is Mandatory

Use HTML by default for:

- A stakeholder-ready implementation plan. The artifact must include a phase timeline,
  data/control-flow diagram when more than two components exist, risk table, validation
  checklist, and explicit out-of-scope section.
- A comparison between named or generated options. Render options side by side with
  identical structure and a recommendation.
- A diagram request. Use inline SVG rather than ASCII art or a Mermaid block unless the
  user explicitly wants Mermaid.
- A one-off editor. The editor is not complete until it exports structured output back
  to the user.
- A deck. Build a real browser presentation with keyboard navigation.

### When Markdown Is Better

Stay in markdown for:

- A short direct answer in the conversation.
- A code snippet, config block, or command sequence.
- A review that only needs a few findings in chat.
- A document that must be hand-edited and diffed frequently in git.
- A user request that explicitly says not to create an HTML file.

## Anti-Patterns

- Wrapping markdown sections in HTML without using layout.
- Producing a generic dashboard of rounded cards and gradients.
- Building a product app. These are artifacts: one file, no backend, no auth.
- Making an editor without export.
- Embedding secrets in HTML source or copied payloads.
- Using browser storage as the only persistence layer.
- Setting `innerHTML` from variable data.
- Letting SVG labels overflow boxes.

## Source Grounding

This skill is informed by:

- Anthropic's "Using Claude Code: The unreasonable effectiveness of HTML" article.
- Thariq Shihipar's HTML effectiveness gallery.
- f-labs-io's `agent-html-skills` plugin and its split of sixteen HTML patterns.
- The standalone `html-artifacts` skill that uses one skill with reference files.

Read `references/source-map.md` when maintaining this skill or auditing coverage.
