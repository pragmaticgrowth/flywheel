# Code Review and Understanding

Use this for PR explainers, annotated diffs, refactor risk maps, migration writeups,
module maps, and "explain this codebase area".

## Annotated Diff

Use when reviewing a PR or branch where line context matters.

Layout:

- Header: branch/PR, author if known, files changed, one-sentence summary.
- "Where to focus" box with the highest-risk areas.
- Jump links to annotated regions.
- File sections with rendered diff lines and margin notes.
- Severity labels: blocking, question, nit, note, praise.
- Summary of required changes and tests to rerun.

The diff is the spine. Do not interleave long prose between code chunks. Pin notes to the
lines or hunk they refer to.

## PR Writeup

Use when the author needs a description reviewers will actually read.

Layout:

- Title and summary.
- Motivation and before/after behavior.
- File/theme tour grouped by purpose, not alphabetically.
- Screenshots/mockups or output examples where relevant.
- Risk and rollback.
- Test evidence.
- Reviewer focus.

For UI/output changes, show before and after side by side.

## Refactor Risk Map

Use when a change touches multiple modules or boundaries.

Layout:

- Inline SVG module graph with touched areas highlighted.
- Table of risk by area: API contract, data migration, concurrency, auth, performance,
  observability, tests.
- "Blast radius" section naming callers/users affected.
- Verification checklist ordered from cheapest to most authoritative.

## Module or Codebase Tour

Use when explaining how a subsystem works.

Layout:

- One-sentence purpose.
- Entry points by use case.
- Boxes-and-arrows module map with the common path highlighted.
- Data lifecycle trace through realistic input.
- Per-module cards: responsibility, key types/functions, gotchas, tests.
- "Where to look next" links.

Avoid drawing every import. Show structural relationships and runtime flow.

## Migration Before/After

Use when explaining replacement of a library, storage model, auth provider, API, or runtime.

Layout:

- Before/after architecture split.
- Compatibility table.
- Cutover sequence.
- Rollback plan.
- Data correctness checks.
- Residual gaps.

## Common Mistakes

- Dumping `git diff` into `<pre>` without annotation.
- Producing a prose review that hides the code.
- Ranking everything as the same severity.
- Drawing an import hairball instead of a runtime/module map.
- Omitting test evidence from PR writeups.
