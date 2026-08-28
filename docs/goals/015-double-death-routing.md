---
id: 015-double-death-routing
title: A second STATUS-less death resumes again or blocks without destroying increments
created: 2026-08-28
type: bug
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/references/escalation-and-repair.md
  - skills/dispatch/SKILL.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

When the resume-from-increments respawn itself dies STATUS-less, the ladder today falls through to rung 5's "roll back any work commits and block", destroying the increments the rung exists to protect. After this goal, a second consecutive STATUS-less death re-fires the resume rung while the transient-death budget has headroom (the re-brief is changed by the larger landed-so-far set — never a same-model-unchanged respawn), and only when that budget is spent does the goal block as repeated-transient-death and roll back there. The rule is death-mode generic: 014's child-timeout clause becomes an instance of it, not the special case.

## Context / why

provenance: inbox-drain (captured at 009's settle; verified CONFIRMED 2026-08-28 by read-only verification against HEAD):

- `skills/dispatch/references/escalation-and-repair.md:81-84` — preamble once-per-rung law; `:105-122` — rung 4 closes "Once per goal per session, like every rung"; `:119-120` — the resumed worker's "routes normally" sentence covers status-bearing returns only; `:123-124` — rung 5 catch-all "roll back any work commits and block".
- `skills/dispatch/SKILL.md:979-987` — Phase 1 bullet 1 has no repeat branch; `:484-494` — 014's child-timeout repeat clause is class-scoped and collides with the spent-rung reading; `:505-510` — the ~3 transient-respawn budget.
- No test pins the double-death path (test_resume_increments_policy.py, test_child_timeout_policy.py checked).

**Interfaces** (from 009/014): rung name "resume from increments"; trigger "missing `STATUS:` block on a returned implementer"; 014's clause "re-enters these stale-claim rules" must remain true — this goal generalizes it to all STATUS-less transient deaths.

Assumptions (drain-waiver reading): (1) within the same session, a second STATUS-less death re-fires the resume rung while the ~3-transient-respawn budget has headroom — the re-brief is changed by the larger landed-so-far set; (2) the once-per-rung law (preamble + rung 4's close) gains an explicit carve-out for evidenced transient STATUS-less deaths; (3) rung 5 gains the guard: a STATUS-less death never routes to "Anything else" while transient budget remains — after the budget is spent the goal blocks (reason "repeated transient death") and the rollback fires there; (4) the general clause is added ALONGSIDE 014's class-scoped sentence, which survives with its pinned phrases ("not a second free respawn", "re-enters these stale-claim rules") verbatim, generalized as the named instance — never substituted; (5) `new file: test_double_death_policy.py` is collected by the stable `pytest -q` runner — never named as its own `acceptance:` path (the 004/006/008/011/012/014 lesson). Existing policy-test span guards must stay green: ladder ≤70 lines, Phase-1 bullet-1 span ≤40 lines, child-timeout ONCE-before-ban ordering — edits are additive and compact.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the new policy tests overlaid and GREEN after: (a) escalation-and-repair.md states a second consecutive STATUS-less death re-fires the resume-from-increments rung while the transient-death budget has headroom (re-brief changed by the larger landed-so-far set) and never routes to rung 5's rollback while budget remains; (b) when the budget is spent the goal blocks as repeated-transient-death and rolls back there; (c) SKILL.md Phase 1 bullet 1 names the repeat branch; (d) the rule is death-mode generic with 014's child-timeout clause as an instance.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 351 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing the ~3-transient-respawn budget's number or the cross-fire heartbeat brake.
- Changing DEATH NEEDS EVIDENCE's two-sample rule.
- Auto-releasing (unclaiming) an `in_progress` entry.
- Version bump / CHANGELOG / GitHub release.
