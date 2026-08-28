---
id: 009-resume-from-increments
title: A dead Droid worker resumes from the commits it already landed
created: 2026-08-28
type: feature
skills: []
model: heavy
size: M
touches:
  - skills/dispatch/references/escalation-and-repair.md
  - skills/dispatch/SKILL.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_resume_increments_policy.py
---

## Outcome (plain language)

DEATH NEEDS EVIDENCE detects a dead implementer but nothing recovers the work already committed. After this goal, the escalation ladder has a "resume from increments" rung: read `gate_base..HEAD`, re-brief a fresh worker with what already landed, and a missing `STATUS:` block is itself a trigger for that rung.

## Context / why

provenance: inbox-drain. Verified 2026-08-28: `escalation-and-repair.md` has warm resume + replay detection, not a "resume from increments" rung, and does not name a missing STATUS block as a trigger. Dispatch SKILL.md Phase 1 bullet 1 (work-commits-present) currently gates then `git reset --hard` on fail — that is the destructive path this goal rewrites. Re-entrancy stale-claim (`:948-950`) is the zero-commit path and is not this goal.

**Interfaces** (from `004-enforce-report-file-gate`): report path `~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md`; Arm A `FAIL_FIXABLE` on a missing/empty/stale report; Phase 1 regenerates a stub report before gating. This goal must not skip that check: resume-from-increments runs *instead of* gate-then-reset when there is no `STATUS: DONE`, and 004's report check runs only after a `STATUS: DONE` (or a regenerated stub) exists.

Assumptions: the rung is a fresh worker whose brief includes `git log gate_base..HEAD` and the diff — not a same-model-unchanged respawn of the dead turn. Missing STATUS on a returned worker is a trigger even when commits exist. `new file: test_resume_increments_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_resume_increments_policy.py` is RED at base and GREEN after: (a) Phase 1 work-commits-present with no `STATUS:`/`DONE` resumes from increments and does **not** gate-then-reset; (b) `escalation-and-repair.md` names a "resume from increments" rung (read `gate_base..HEAD`, re-brief a fresh worker with what already landed) and lists a missing `STATUS:` block on a returned implementer as a trigger.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing DEATH NEEDS EVIDENCE's two-sample rule.
- Auto-releasing (unclaiming) an `in_progress` entry.
- Version bump / CHANGELOG / GitHub release.
