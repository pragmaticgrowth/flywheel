---
id: 003-surface-subjective-criteria
title: Criteria marked "needs independent review" actually reach a human
created: 2026-07-25
type: bug
skills: []
model: heavy
size: S
touches: ["skills/dispatch/SKILL.md", "README.md", "public/index.html"]
acceptance: ["python3 -m pytest -q"]
---

## Outcome (plain language)

`define-goal` tells goal authors three times that a subjective criterion marked **needs
independent review** will be "surfaced to a human under needs-you at integration". Dispatch
does not do this — the phrase appears nowhere in its 739 lines, and the deterministic gate
has no concept of it. So a goal with a subjective criterion PASSes today with that criterion
verified by nobody, while the authoring skill says it is handled. After this goal, a PASS on
such a goal surfaces those criteria to the human as a concrete "run this, look for that"
item.

## Context / why

Design brief: `docs/goals/briefs/2026-07-25-close-the-gap.md` (piece C).

This is a documented-but-unimplemented behavior — a contract lie, not a missing feature.

Evidence (the promise):

- `skills/define-goal/SKILL.md:155` — "keep it as a criterion marked **needs independent
  review** so `dispatch` surfaces it to a human under needs-you at integration; it is a
  human-verification item, NOT something the gate decides, and never the implementer's own
  self-grade."
- `skills/define-goal/SKILL.md:401` — the goal-file template's criterion line: "**needs
  independent review** (surfaced to a human under needs-you at integration, never the
  implementer's self-grade)".
- `skills/define-goal/SKILL.md:481` — "any subjective dimension stays **needs independent
  review**".

Evidence (the gap):

- `grep -c "needs independent review" skills/dispatch/SKILL.md` → **0**.
- `grep -n "independent\|subjective" skills/dispatch/scripts/pg_validate.py` → **no
  matches**. The gate has no concept of the marker.
- Consequence: dispatch's PASS path (`skills/dispatch/SKILL.md:365-367`) squashes, marks
  `completed`, and reports — with no step that reads the goal file for these criteria.

**Gate mechanics, already traced — do not "fix" the type.** `type: bug` is correct and the
repro-direction check passes as written: the new test file matches `is_test_path`
(`pg_validate.py:303-304`), gets overlaid onto the base worktree (`:676`), fails there because
base's `skills/dispatch/SKILL.md` lacks the marker, and passes on head — giving
`base_any_red=True, head_all_green=True` at `repro_direction` (`:147,165-169`). `already_correct:
true` would be WRONG here: it suppresses a genuine red-on-base proof (`:170-173`). The repo has
no `node_modules`/`.venv`, so the dep-link INCONCLUSIVE guard (`:701`) cannot fire.

The failing-test direction for this bug is documentary, not runtime: the proving check is
that dispatch's text contains the rule, and the RED baseline is trivially available since the
current text contains nothing at all.

**Amended 2026-07-25:** the original regression-test criterion asked for the marker and
`never a completion gate` to appear in the same `## ` section, while declaring its purpose as
"so the test cannot be satisfied by pasting a string". It did not achieve that purpose.
Reproduced against the rolled-back implementation (`d93133f`), two mutation shapes matter and
they behave differently — the distinction is the whole lesson:

- Inversion by **addition**, which RETAINS the phrase ("This BLOCKS completion until a human
  signs off. (Historically it was an observation, never a completion gate — a PASS still
  completes the goal…") → **9/9 passed.** The rule asserts the opposite of the contract and
  the suite is blind to it. This is what blocked the goal.
- Inversion by **replacement**, which DELETES the phrase → 3 failed. Caught, but only
  incidentally: the assertion notices the missing string, not the reversed meaning.
- A glossary paragraph carrying all required phrases and ending "Dispatch does none of this",
  with the PASS path untouched → **9/9 passed.**

A first amendment tried to fix this by binding the assertions to structural LOCATION. Verified
by running it: the inversion-by-addition still passed, and the prescribed step-4 span turned
out to be 58 lines wide (swallowing the Windows note), contradicting its own promise that a
paste elsewhere would fail. → **Resolved reading:** stop trying to make a text-presence test
verify meaning. Two rounds of finer string matching failed, and the third would too — a
substring assertion cannot detect negation at any granularity. The test is now scoped
honestly to what it CAN do: pin the placement of required text (narrow step-4 span with a
width bound, goal 002's table row, the Phase 4 contents paragraph) as a guard against
regression and accidental deletion, with an explicit instruction NOT to claim semantic
detection. Meaning is verified by the dry-run and by the orchestrator's gate reviewer — a
human-judgment surface, which is exactly what this goal is about in the first place.
The first implementation's rule TEXT and surfacing logic were correct — only this criterion
was defective; work commit `d93133f` is recoverable and is a valid starting point.

**Interfaces consumed from 002-answerable-needs-you** (its dependency): 002 establishes the
single canonical needs-you format section in `skills/dispatch/SKILL.md`, defining the line
shape `<id or item> — <reason> → <command>` and a blocker-class → command table. This goal
adds ONE row/class to that existing table and reuses the established line shape — it must not
introduce a second needs-you format.

## Acceptance criteria

- [ ] A regression test in the repo's pytest suite pins the rule's PLACEMENT — and claims
  nothing more. Scope note, binding on the implementer: a text-presence test cannot verify
  that prose MEANS what it should; it can only verify that required text sits where it
  belongs. Two rounds of trying to close that gap with finer string matching failed (see the
  Amended note in Context). So this test is explicitly a placement guard against regression
  and accidental deletion, NOT a semantic check — the dry-run in the criterion below and the
  orchestrator's own gate reviewer are what verify meaning. Do not add assertions that claim
  to detect a negated or contradicted rule. Assert exactly:
  (a) **PASS-path span.** Slice `skills/dispatch/SKILL.md` from the line beginning
  `## Working a goal` to the next line beginning `## `; within that slice, take from the line
  beginning `4. PASS →` up to (exclusive) the first subsequent non-blank line that starts at
  column 0 (i.e. is not an indented continuation of step 4). Against the current text that
  span ends just before the `anchor`/`gate_base` paragraph and excludes the Windows note.
  Assert the span is **at most 45 lines** — a bound with headroom for this goal's own
  additions, whose purpose is to fail loudly if a future restructuring silently widens the
  span to the whole section (the first amendment's span was 58 lines and swallowed unrelated
  prose). Assert the literal marker `needs independent review` occurs in THAT span.
  (b) **Table-row span.** Slice from the table header line `| class | trigger | what to run |`
  inside the `## needs-you — the canonical format` section to the first following blank line.
  Assert exactly one row in THAT span begins with `` | `needs independent review` `` and has
  4 pipes. A row appended elsewhere in the file must NOT satisfy this.
  (c) **Contents-rules span.** Slice the Phase 4 paragraph that begins
  `needs-you lists everything currently waiting on the human` up to `**Stalled factory`.
  Assert the class is enumerated in THAT span.
  (d) **Placement proof, run and shown — two transcripts.** (i) Paste a paragraph containing
  the marker plus the phrases the rule uses into an UNRELATED part of the file (the Windows
  note is a good target, and an orphan table row at end-of-file), leaving step 4 untouched;
  run the test file and show it FAILS. (ii) Show it passes on the real tree. Attach the
  mutation as a `git diff` and both pytest outputs — a described mutation is a claim, not
  evidence. This proves the placement guard works; it deliberately does NOT claim to prove
  negation-resistance.
  Shown red before the change and green after — the red/green transcript is evidence, and the
  subagent dry-run below is the PRIMARY evidence that the behavior is correctly specified.
- [ ] `skills/dispatch/SKILL.md` states that after a PASS gate the orchestrator reads the
  goal file for criteria marked `needs independent review`, and when any exist surfaces them
  under needs-you using the canonical format section from goal 002.
- [ ] The rule states that each such criterion is rendered as **what to run and what to look
  for**, drawn from the implementer's report evidence — not the criterion text repeated
  verbatim.
- [ ] The rule states explicitly that a PASS still completes the goal: these criteria are
  surfaced, never a completion gate — so an unattended `/loop /dispatch` drain is not
  blocked by them.
- [ ] The rule states that a goal with no such criteria surfaces nothing (no empty item).
- [ ] The needs-you contents rules in `skills/dispatch/SKILL.md` (~`:696-703`) list this as a
  needs-you item class, and it is added as a row/class to goal 002's blocker-class table
  rather than as a new format.
- [ ] A subagent dry-run: given a goal file carrying one `needs independent review` criterion
  and a PASS gate, the agent cites the section deciding whether it is surfaced and whether
  the goal completes. A RED baseline against `git show HEAD:skills/dispatch/SKILL.md` shows
  the pre-change text leaves it undecided. Both transcripts quoted in the report.
- [ ] `README.md` and `public/index.html` mention that subjective criteria are surfaced for
  human review at integration (per CLAUDE.md's docs-move-with-the-skills rule).
- [ ] `python3 -m pytest -q` (full suite) passes.

## Constraints (hard rules)

From CLAUDE.md, verbatim:

- **Skills-first (formerly skills-only).** Don't add MCP servers, commands, agents, or hooks
  here without an explicit ask.
- **Portability.** Skills must not contain user-specific absolute paths (`/Users/...`) for
  either harness.
- **Docs move with the skills.** Changing what a skill does, how it's invoked, plugin
  boundaries, install, or the queue/config model means updating `README.md` AND
  `public/index.html` in the SAME change.
- **Skill edits are tested.** New or changed skill mechanics get a subagent dry-run before
  shipping; for compliance-critical rules, add a RED baseline.
- **Push every time — on every completion, the FULL tree.**
- Never push protected branches.

Plus:

- Surfacing must NOT block completion or the unattended drain — PASS still completes.
- Do NOT teach `pg_validate.py` about subjective criteria; the deterministic gate stays
  deterministic. This is orchestrator-side reporting only.
- Do NOT change `define-goal`'s three existing statements — they are the specification this
  goal implements.
- Do NOT change this goal's `type: bug` and do NOT set `already_correct: true` — see Context.
- Keep the tier vocabulary in any new prose: the docs model-policy test requires every line
  naming a legacy model in an active doc to also name its tier or say alias/maps.

## Out of scope

- Any human sign-off gate, approval state, or new status value.
- Persisting review outcomes anywhere (status stays only in `index.yaml`).
- Version bump, `CHANGELOG.md` entry, git tag, and GitHub release. Goals 001-003 ship as ONE
  release performed by the repo owner after all three complete. Do NOT edit
  `.claude-plugin/plugin.json`, `CHANGELOG.md`, the site `.ver-pill`, or the README version
  badge.
- Changing how subjective criteria are authored or detected at define time.

## If blocked

Stop and report attempted paths, evidence, the blocker, and what would unlock you.
If the same acceptance command fails the same way twice in a row, or after ~3 honest
attempts a criterion can be neither satisfied nor shown measurable, declare
GOAL_UNREACHABLE with evidence and stop — never retry the identical failing approach.

## Goal contract

/goal Implement the documented-but-missing behavior for criteria marked `needs independent
review`, per the Acceptance criteria of docs/goals/003-surface-subjective-criteria.md.
define-goal states three times (SKILL.md:155, 401, 481) that dispatch surfaces such criteria
to a human under needs-you at integration; dispatch contains the phrase zero times and
pg_validate.py has no concept of it, so those criteria are currently verified by nobody.
Add a regression test asserting `skills/dispatch/SKILL.md` contains the literal marker
(red before, green after — show both), then add the rule to dispatch: after a PASS gate,
read the goal file for these criteria and surface them under needs-you using the canonical
format section from goal 002, rendered as what to run and what to look for from the
implementer's report evidence; PASS still completes the goal (never a completion gate); no
criteria means nothing surfaced. Add it as a class in goal 002's blocker-class table and to
the needs-you contents rules. Run a subagent dry-run with a RED baseline against `git show
HEAD:skills/dispatch/SKILL.md`, quoting both transcripts, and update README.md and
public/index.html. Done when `python3 -m pytest -q` passes and the red/green plus RED-baseline
transcripts are shown. Before stopping on success, re-print the final acceptance-command
outputs. Stop when every criterion verifiably passes, or when blocked or a criterion proves
unreachable (follow "If blocked"). Stop after 20 turns.
