---
id: 019-done-means-passed
title: define-goal contracts the outcome phase, done means passed, and a whole-outcome gap always surfaces
created: 2026-08-29
type: feature
skills: []
model: heavy
size: M
touches:
  - skills/define-goal/SKILL.md
  - skills/dispatch/SKILL.md
  - test_outcome_check_policy.py
  - test_capture_bar_policy.py
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
  - uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py -k report_only
  - uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py -k test_plan_status_done_means_outcome_check_passed
---

## Outcome (plain language)

Three things close the loop the plan opens. define-goal's plan-backed fast path must know how to contract a verification-only final phase (and the red-team must stop rejecting it for lacking a "no behavior change" proof). `status: done` on a plan must mean its outcome check PASSED, not that its pieces got built. And settle triage must stop burying whole-outcome gaps: v12.3.0 made Report-only the default with "unsure lands here", which is right for nits and backwards for exactly the failure this chain exists to catch — so an item that would falsify a plan outcome bullet is never Report-only, regardless of how unsure the implementer is.

## Context / why

Plan: docs/goals/plans/2026-08-28-standard-of-completion.md — Phase 4

Verified against HEAD `cc6a924` (line numbers shifted in v12.3.0 — anchor on the quoted text):

- `skills/dispatch/SKILL.md:812` — `status: done` is stamped "when the last open phase checks. A DISPLAY mirror only". With goal 017 landed the last phase IS the outcome check, so the meaning is fixed by construction; this goal makes the mirror text SAY so.
- `skills/dispatch/SKILL.md:871` — "**unsure → Report-only**: Report-only is the DEFAULT"; `:899` — "**Report-only** (the DEFAULT — unsure lands here)". Both shipped in v12.3.0, the day after this plan was drafted.
- `skills/define-goal/SKILL.md` type-shape rule requires a chore to prove "no behavior change" plus one mechanical check — a verification-only goal has no behavior to hold constant, which is why the owner-resolved question grants it `type: chore` plus one admitting sentence.
- The capture bar's three earning shapes already include "genuinely NEW work", so an outcome-falsifying item does technically earn a line today; the defect is the DEFAULT and the "unsure" tiebreak, not the bar itself.

**Interfaces** (produced by 017, consumed by 020): `test_outcome_check_policy.py` is created by 017 and EXTENDED here. Two test names are contractual, because goal 020's outcome check selects them and a `-k` matching nothing exits 5: at least one name containing `report_only`, and one named EXACTLY `test_plan_status_done_means_outcome_check_passed`. The plan template shape that the fast path reads is 017's.

The carve-out is deliberately narrow, and the skill text must keep it that way:

> An item that would falsify a plan outcome bullet is never Report-only. It is a live defect by definition and earns its inbox line regardless of the implementer's certainty — "unsure → Report-only" does not apply to the whole.

Nits, latent or unreachable-today findings, fail-safe residuals, contract-mandated tradeoffs, and caption/wording items stay Report-only exactly as v12.3.0 has them. This is a carve-out, not a rollback of the capture bar.

Assumptions: (1) the carve-out is stated where the four dispositions are defined, so it is read at the moment of the decision; (2) "would falsify" means the item, if true, makes an outcome bullet's command fail — not merely that it is topically related to one; (3) a verification-only goal is `type: chore` stamped medium by the existing rubric, and the admitting sentence is added to the type-shape rule rather than creating a new type.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the new policy tests overlaid and GREEN after, for each of: (a) settle triage states that an item falsifying a plan outcome bullet is never Report-only regardless of certainty, and defines the operative test — the item qualifies when, if true, it would make an outcome bullet's command fail, or make a `**needs independent review**` bullet false (topical relation to a bullet is NOT enough); (b) the carve-out names the earning token such an item carries — `live-defect` — so the capture item's "if you cannot honestly name one shape … → Report-only" cannot re-route it, and the carve-out sits alongside the four disposition definitions where the decision is made; (c) the carve-out is explicitly narrow and the other Report-only classes are named as unchanged; (d) dispatch's plan mirror states that `status: done` means the outcome check passed; (e) define-goal's plan-backed fast path contracts a verification-only final phase and its type-shape rule admits a verification goal as `type: chore` without a no-behavior-change proof.
- [ ] Both selectors goal 020's outcome check depends on resolve and pass, each exiting 0 rather than 5: `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py -k report_only` selects at least one test, and a test named EXACTLY `test_plan_status_done_means_outcome_check_passed` exists and passes.
- [ ] Two subagent dry-runs, each RED-baselined against the file its scenario actually exercises: the plan-conversion dry-run against `git show HEAD:skills/define-goal/SKILL.md`, and the triage dry-run (an outcome-falsifying finding the implementer flagged as unsure) against `git show HEAD:skills/dispatch/SKILL.md`, whose pre-change text routes it to Report-only by default. Baselining conversion against dispatch would produce a vacuous RED — dispatch's old text does not decide plan conversion at all. Transcripts in the goal's report file.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 360 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- The carve-out is ADDITIVE: these four v12.3.0 strings stay byte-identical — `Report-only is the DEFAULT`, `(the DEFAULT — unsure lands here)`, `an item that does not clearly meet one of the capture bar's three earning shapes is under the bar`, and the `cannot honestly name one shape` sentence. Their existing order in `test_capture_bar_policy.py` holds. Rewriting them instead of adding beside them is a rollback of v12.3.0, not a carve-out.
- Never push protected branches other than the repo's own pre-authorized `origin main`.

## Out of scope

- `CLAUDE.md`'s dispatch and define-goal bullets and any other doc restatement — that is goal 020. Editing it here puts a path outside `touches:` into the diff and fails blast-radius.
- Loosening the v12.3.0 capture bar for anything other than outcome-falsifying items.
- Auto-fixing a failed outcome check — owner decision 2026-08-28: a whole-outcome miss is a design fault and design faults stop for the owner.
- Introducing a `type: verify`, which would ripple through define-goal, the red-team, `pg_validate.py`, and every rule keyed on the three existing types.
- Version bump / CHANGELOG / GitHub release — that is goal 020.
