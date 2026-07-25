# Design brief — close the gap between what the factory promises and what it proves

**Date:** 2026-07-25 · **Chain:** goals A → B → C (see Decomposition)
**Status:** approved design; contracts live in the goal files, not here.

## Outcome

Three defects share one root: the factory reports confidence it has not earned. The
declared local gate is never proven to run; every human decision is emitted as a
diagnosis rather than an answerable question; and a criterion class that define-goal
tells authors is handled is, in dispatch, handled nowhere. Close all three so a PASS
means what a reader thinks it means.

Scope note: this repo is used on **large projects**, not hobby repos (owner, 2026-07-25).
Test-scaffolding and a cheap/short pipeline lane were considered and **rejected** — big
repos have suites, and execution quality is the factory's product.

## Decomposition

### A — factory-doctor proves the gate by running it

`verify_check` (`skills/factory-doctor/scripts/doctor_checks.py:170`) only asks whether
`config.verify` is non-empty. In a large repo the real failure is a *declared but wrong*
gate: a renamed npm script, a wrong workspace filter, a build-only command list that
cannot catch a behavior regression. The doctor goes green and every later dispatch PASS
is unearned.

Fix: execute each `config.verify` command in order and report the first failure with its
exit code and last output lines.

- Safe on cost: **dispatch never invokes the probe** (verified — no `doctor_checks`
  reference anywhere in dispatch's 739 lines). factory-doctor is human-invoked, so this
  is one slow pass, never a per-fire tax.
- Non-zero exit → **BLOCKER**. A gate that fails is worse than no gate: it looks green
  in `index.yaml`.
- Unresolvable command (missing npm script / make target / binary) → **BLOCKER**, with
  the near-miss named. This is the fast static failure, reported before anything runs.
- Timeout (`PG_DOCTOR_VERIFY_TIMEOUT`, default 1800s, mirroring `PG_VALIDATE_TIMEOUT`)
  → **WARN**. Slow is not broken.
- `--skip-verify-run` degrades to today's static check for a fast pass.
- REPORT-only. A red suite is the repo's business — never auto-fixed, consistent with
  the skill's existing never-fix boundary.

Explicitly out: scaffolding tests; judging whether the command list is *sufficient*
(a "no test-shaped command" heuristic is too guessy to raise a BLOCKER).

### B — every human decision becomes an answerable question

`needs-you` emits diagnoses (`contract defect: criterion 3 ambiguous`), never next
actions. The escalation ladder's terminal rung is always "ask the human" — and the human
is whoever needed the factory in the first place.

Split in two, forced by unattended operation:

- **B1 · dispatch.** Every needs-you line gains a `→ <exact command>` suffix. Dispatch
  **may** ask interactively, but only on unambiguous evidence of an attended run
  (conversational `/dispatch` this session; not `/loop`, not `claude -p`, not
  `droid exec`; no batch flag active). One round, ≤2 questions, options with a
  recommended default. Unsure → do not ask. A batch run never asks. The conservative
  default is load-bearing: an AskUserQuestion in a headless fire hangs or auto-answers
  the loop.
- **B2 · define-goal `--amend <id>`.** Reads the blocked goal file, its `index.yaml`
  blocker reason, and the implementer report at
  `~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md`; runs ONE targeted round
  in plain language; rewrites only the defective criteria; re-runs `contract-red-team`
  on the amended draft; flips the entry back to `not_started` via
  `chore(goals): amend <id>`.

Amend is the single define-goal exception to "dispatch owns status writes". It is a
claim-protocol commit like any other and never touches a goal that is not `blocked`.

### C — implement `needs independent review` (bug, not enhancement)

define-goal states three times (`skills/define-goal/SKILL.md:155`, `:401`, `:481`) that a
subjective criterion marked **needs independent review** is "surfaced to a human under
needs-you at integration". Dispatch has **zero** mentions of it and `pg_validate.py` has
no concept of it. Today such a goal PASSes with that criterion verified by no one, while
define-goal's text tells authors it is handled. The contract lies.

Fix on the dispatch side: after a PASS gate, detect `needs independent review` criteria
in the goal file and surface them under needs-you as
`<id>: N criteria need your eyes → <what to check>`, rendered as **what to run and what
to look for** (drawn from the implementer's report evidence), not the criterion text
verbatim.

Bounded deliberately: PASS still completes the goal. Blocking completion on human
sign-off would break unattended drain — define-goal's promise is "surfaced", and
surfaced is exactly what gets built.

## Interfaces between the pieces

- **B1 → B2:** the needs-you suffix string `→ /define-goal --amend <id>`, and the report
  path convention `~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md`
  (`<SLUG>` = repo dir name).
- **B1 → C:** C extends the same needs-you line format B1 establishes; C's entries carry
  the `→` suffix convention rather than inventing a second shape.
- **A → nothing:** independent; may land first.

## Key decisions and why

- **Run the verify commands rather than static-check them** (owner, 2026-07-25). Static
  resolution cannot catch the wrong-filter / build-only failure, which is the actual
  large-repo defect. Affordable because the probe is human-invoked only.
- **A red gate is a BLOCKER, not a WARN.** The whole point is that a broken gate
  currently reads as green.
- **Dispatch may ask, but only when provably attended** (owner, 2026-07-25). Interactive
  questions in an unattended fire are worse than no questions.
- **C does not gate completion.** The documented promise is "surfaced"; expanding it into
  a sign-off gate would break `/loop` drain and exceed the defect.

## Verification story

- A: `python3 -m pytest -q skills/factory-doctor/scripts/test_doctor_checks.py` — cases
  for green / red / unresolved / timeout / `--skip-verify-run`.
- B: `python3 -m pytest -q test_skill_inventory.py`, plus a subagent dry-run on the
  attended-vs-unattended gate **with a RED baseline**
  (`git show HEAD:skills/dispatch/SKILL.md` must decide it differently) — compliance-
  critical per CLAUDE.md.
- C: RED baseline is trivial (the old text has no rule at all); dry-run a goal file
  carrying a subjective criterion through a PASS gate.
- All three: full suite `python3 -m pytest -q` green; docs moved in the same change
  (`README.md`, `public/index.html`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`), version
  bump + annotated tag + release, then push.

## Known drift, deliberately not fixed here

`skills/dispatch/SKILL.md` claims Phase 0 runs the read-only doctor probe each fire; it
does not (factory-doctor's own SKILL.md repeats the claim). Real documentation drift,
out of scope for this chain — recorded so it is not lost.
