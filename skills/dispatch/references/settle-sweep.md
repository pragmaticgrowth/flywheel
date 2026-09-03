# The settle sweep — fix what the goal surfaced, in-run, behind the same gate

Read when Settle triage routes ≥1 item to **Sweep**, and from process-inbox's FIX
step (same procedure, the cluster's items as input). Nothing from a settle is ever
parked for a later goal: it is repaired, swept, dismissed, reported, or handed to the
owner as a decision — `docs/goals/inbox.md` is never written by dispatch.

## Where it runs

In the canonical sequence the sweep is step 4's SECOND half: after the goal's own
gate PASSed and its commits are squashed to `feat(goal <id>)`, BEFORE
`chore(goals): complete <id>`. "Completed" therefore means the goal passed AND its
sweep settled — zero left behind. In parallel mode the sweep runs on the working
branch (the primary checkout) right after the lane fast-forwards, under the same
integration lock and before the next integration — never inside a lane. One writer in
the tree at a time holds: the orchestrator only reads while the fixer works.

## Admission — what the sweep takes

An item enters the sweep ONLY when it is a live defect — wrong behavior reachable on
current code, with `path:line` evidence (a verified reviewer finding, a Follow-ups
line, a plan-outcome falsifier) — outside this goal's contract, and a code change one
fixer sitting can land and Arm A can verify. Nits, caption/doc/config wording, missing
wiring that nothing yet calls, and new work never enter (v16.0.0: Report-only or
`fyi: follow-up`). Refusals, decided by the orchestrator before spawning, each
recorded in the goal's report file under `## Sweep`:

- **Owner decision** (spend, data loss, irreversible or externally visible) →
  `needs-you:` class `owner decision`, with a recommendation. Never swept.
- **Goal-sized** — a schema/migration change, a lockfile or CI/config change (the
  conflict domains), a new drivable surface, anything needing its own contract → an
  `fyi:` line, class `follow-up`, `<gist> → /define-goal <one-line want>`. The owner
  decides whether it becomes a goal; the factory never mints one from a settle.
- **Cap ~5 items per sweep**; the overflow is `fyi: follow-up`. Report-only and
  Dismiss stay exactly as Settle triage defines them.
- The one-sitting test is Settle triage's (disposition 3): inside the evidence's
  files plus their tests, no conflict-domain file, no new drivable surface.

**Before spawning, write the admitted list** — item, shape, tier — under `## Sweep`
in the goal's report file. That record is what survives a crash (below).

## Tier — one fixer, the strongest any item needs

Every admitted item is a live defect, so the fixer is **heavy** (a config-value or
constant fix with no logic change may run medium; **light** never). One sweep spawns
ONE fixer; never two writers. Map the tier at spawn exactly as the implementer's (opus/sonnet
pin on Claude Code, `complexity` on Droid). Name the tier per item in the report
file.

## The fixer brief (plain spawn, foreground, no `name:`; Droid `worker`, `await: true`)

Verbatim skeleton, items filled in:

```
You are the settle-sweep fixer for goal <id> on branch <branch> in <absolute checkout>.
The goal itself is finished and gated; you fix the follow-ups it surfaced. Items:
  1. [<live-defect|new-work>] <description> — evidence: <path:line or report path>
  ...
Rules: TDD for any behavior change (failing test first, then the fix; commit each
green cycle as `chore(sweep <id>): <gist>` — ONE item per commit, so a bad item can be
reverted alone; a gist never contains the text ` items — `, which marks the squash). Stay inside the files each item's evidence names plus their tests;
an item that needs more than that, needs an owner's word, or resists ~3 honest
attempts is SKIPPED with a one-line why — never widened, never guessed. Never touch
docs/goals/**, migrations, lockfiles, or CI/config. Before you finish run the tests
covering the files you changed — NOT the repo's full verify/preflight pipeline (the
sweep gate runs that once after you return), and never wait by `sleep`; a test file
re-run more than twice with no edit in between is churn. Append your evidence under
`## Sweep` in ~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md. Kill any
background watcher you started. End with, ≤10 lines:
SWEEP:
  <n>. FIXED <short sha> | SKIPPED <why>
Tests: <one line>
```

The wait obeys Spawning-and-waiting (let the turn end; death needs the transcript).
A fixer that returns no `SWEEP:` block → read `sweep_base..HEAD`; commits present →
gate them as below; none → every item Report-only, `sweep: fixer died`.

## The gate — Arm A only

`sweep_base` = HEAD before the fixer spawn (the `feat(goal <id>)` commit, or the
fast-forwarded branch tip). Over `sweep_base..HEAD` run Arm A exactly as the goal
gate does — the same ONE tracked, `timeout`-bounded background script: every
`config.verify` command with echoed exit codes and the `=== ARM A COMPLETE ===`
sentinel, plus `git diff --name-only <sweep_base>..HEAD -- docs/goals/` (any output =
FAIL, the fixer touched the queue), plus `git diff --name-only <sweep_base>..HEAD`
read against the admitted items' evidence files (a file outside them = FAIL). No Arm
B and no repair round (v16.0.0): a sweep fixes a defect the goal's own reviewer
already described, so a second reviewer bought nothing measurable, and the flake and
wedged rules apply unchanged.

PASS → `git reset --soft <sweep_base>` and commit ONE
`chore(sweep <id>): <n> items — <gists>`; then `chore(goals): complete <id>` as step 4
continues (plan mirror inside it). The sweep commit stays separate from the goal's
`feat` commit — out-of-contract work never widens the goal's own diff.

FAIL, plainly localized to ONE item's commit → `git revert` that commit, mark the
item `SKIPPED: failed the gate — <finding>`, re-run Arm A ONCE; anything else →
`git reset --hard <sweep_base>`, every item Report-only with `sweep failed:
<reason>`, one `fyi:` line class `sweep failed`. The goal still completes: the sweep
never changes a goal's own verdict or status.

## Reporting

The goal's report line carries `swept: <fixed>/<items>` inside the `last:` field
(omitted when the sweep had no items). SKIPPED items are Report-only (their why in
`## Sweep`) unless their why is an owner decision (→ `needs-you`), goal-sized (→
`fyi: follow-up`), or the item is a whole-outcome falsifier — that one is
`fyi: follow-up` naming the outcome bullet it threatens, whatever the skip reason
(Settle triage's carve-out outranks this default). The report file's `## Sweep` section holds everything else — the
closing turn never narrates a sweep.

## Crash rule (Phase 1)

An `in_progress` claim whose `gate_base..HEAD` already holds a `feat(goal <id>)`
commit passed its own gate before the session died mid-sweep. `git reset --hard` to
the LATER of that commit and the sweep's SQUASH commit — recognizable by its subject
`chore(sweep <id>): <n> items — …` (per-item commits are `chore(sweep <id>): <gist>`
and never carry ` items — `); a squash means the sweep passed, and loose per-item
commits after the reset point are un-gated and are discarded. Then
`chore(goals): complete <id>` — the sweep is never resumed, and the goal gate never
re-runs on a range that contains sweep work. The discarded items are not lost: they
are listed under `## Sweep` in the report file (written before the spawn), so emit
ONE `fyi:` line, class `sweep failed`, `sweep discarded at crash — <n> items, see
<report path>`; a whole-outcome falsifier among them gets its own `fyi: follow-up`.
