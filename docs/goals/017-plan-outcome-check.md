---
id: 017-plan-outcome-check
title: A 3+-phase plan carries an executable outcome check as its final phase
created: 2026-08-29
type: feature
skills: []
model: heavy
size: M
touches:
  - skills/ideate/references/plan-template.md
  - skills/ideate/SKILL.md
  - test_outcome_check_policy.py
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

A plan's phases tick off one by one and the plan is stamped done when the last one checks — nothing ever asks whether the thing the plan set out to deliver actually works. After this goal, a plan of 3 or more phases carries an outcome check as its own final phase: `## What will be true when done` stops being prose and becomes bullets that each name an exact command, every command must fail at the plan's base commit and pass only once all phases have landed, and each command must be a drivable-surface check reachable by `config.verify` as written. The outcome check inherits the whole existing pipeline — contracted, red-teamed, claimed, gated — so dispatch needs no new machinery.

## Context / why

Plan: docs/goals/plans/2026-08-28-standard-of-completion.md — Phase 2

Verified against HEAD `cc6a924` (line numbers shifted in v12.3.0 — anchor on the quoted text):

- `skills/ideate/references/plan-template.md:51` — `## What will be true when done` already exists and is already the right section; today its bullets are inert prose and nothing runs them.
- `skills/dispatch/SKILL.md:812` — `status: done` "when the last open phase checks. A DISPLAY mirror only". Recon confirmed no plan-level gate, check, or report exists anywhere in dispatch.
- Phases already map 1:1 onto goals through a `Plan: … — Phase <N>` Context line, so a plan-level check can be an ordinary goal.
- `docs/goals/plans/` holds exactly one plan — this chain's own — and it already conforms (5 phases, final phase is an outcome check running every bullet).

**Interfaces** (consumed by 019 and 020): `test_outcome_check_policy.py` is created here and EXTENDED by 019. It must contain at least one test whose name contains `committed` — goal 020's outcome check runs `pytest -q test_outcome_check_policy.py -k committed`, which exits 5 if nothing matches. Goal 019 adds names containing `report_only`. The template shape this goal writes is what goal 019's define-goal fast path reads.

Two rules carry the weight and must both be stated in the template:

1. **Fail-at-base.** A check that already passes before any phase lands is measuring a piece, not the whole. This mirrors the reality check's existing fail-at-base/pass-at-head item rather than inventing a new idea.
2. **Committed-test form.** The outcome check must land as a committed test the repo's own suite discovers (here a root `test_*_policy.py`; in a target repo whatever `config.verify` discovers), never an ad-hoc command run once at settle. Committed means every later goal's gate re-runs it, so a late phase that breaks an early phase's outcome fails a gate; ad-hoc means the plan is stamped done against evidence that is already stale. An outcome bullet whose command is not reachable by `config.verify` as written is a contract defect the reality check's existing acceptance-runnability item already catches — state the requirement, add no new check.

Corollary the template must also state: outcome bullets are DRIVABLE-SURFACE checks, never code-reading checks. Phase implementers read the plan by design (`skills/dispatch/references/implementer-brief.md:12`; owner-resolved 2026-08-28), so the sample is visible — and if the only way to pass it is to drive the real surface, then targeting the sample IS building the behavior.

Assumptions: (1) the 3+-phase threshold is on PHASE count, and a 1–2-phase plan is unaffected; (2) a subjective outcome keeps the existing `**needs independent review**` escape hatch rather than being forced into a command; (3) `new file: test_outcome_check_policy.py` is collected by the stable `pytest -q` runner and never named as its own `acceptance:` path.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the new policy tests overlaid and GREEN after (RED output recorded in the goal's report file), for each of: (a) each outcome bullet names an exact command **or** carries the `**needs independent review**` marker — subjective outcomes keep the existing hatch; (b) the fail-at-base rule is stated; (c) the committed-test form is required and the ad-hoc-command shape is named as the thing it replaces, proven by at least one test function in `test_outcome_check_policy.py` whose name contains `committed` (goal 020 selects it with `-k committed`, which exits 5 on no match); (d) outcome bullets are required to be drivable-surface checks, and the template carries the one-line contrast that defines the term (drives the real surface vs. reads or greps source); (e) a 3+-phase plan carries the outcome check as its own final phase.
- [ ] `skills/ideate/SKILL.md`'s step 2 scope check mints the outcome phase at 3+ phases, and its step 6 self-review verifies fail-at-base before the plan is presented.
- [ ] A subagent dry-run produces a plan for a 3-phase idea that carries a conforming outcome check — conforming = every outcome bullet names an exact command or the review marker, the final phase is the outcome check, and each command is reachable by `config.verify` as written — RED-baselined against `git show HEAD:skills/ideate/references/plan-template.md`, with both transcripts written into the goal's report file.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 360 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches other than the repo's own pre-authorized `origin main`.

## Out of scope

- `CLAUDE.md`'s ideate bullet and any other doc restatement — that is goal 020. Editing it here puts a path outside `touches:` into the diff and fails blast-radius.
- Retrofitting plans written before this rule; it applies to plans written from here on.
- Ratcheting the outcome bullets against a previous commit — that is goal 018.
- define-goal's handling of the outcome phase and what `status: done` means — that is goal 019.
- Expansion-on-saturation and differential testing, which need an oracle flywheel does not have.
- Version bump / CHANGELOG / GitHub release — that is goal 020.
