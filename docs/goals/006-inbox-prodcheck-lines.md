---
id: 006-inbox-prodcheck-lines
title: Unrunnable production checks print as their own report lines
created: 2026-08-28
type: bug
skills: []
model: heavy
size: S
touches:
  - skills/process-inbox/SKILL.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

process-inbox step 3 sends an unrunnable PRODUCTION-CHECK to the report with the exact query, but step 7's hard envelope only allows counts + dispatch line + OWNER lines, so a compliant report can count `<P>` and print none of the queries. After this goal, step 7 prints one line per unrunnable check (query + why), `<P>` equals those lines, and the matching red flag is updated.

## Context / why

provenance: inbox-drain. Verified 2026-08-28: `skills/process-inbox/SKILL.md:122-125` vs `:210-222` and red flag `:252-253`. Both clauses still exist and still contradict.

Assumptions: unrunnable PRODUCTION-CHECK lines are a fourth permitted report component, not OWNER lines (OWNER bar unchanged). Runnable checks still re-triage and do not print as P-lines. `new file: test_inbox_prodcheck_policy.py` is collected by the stable `pytest -q` runner — do not name it as its own `acceptance:` path (`type: bug` repro-direction INCONCLUSIVEs when `acceptance:` names a file added by the fix).

**Amended 2026-08-28:** `acceptance:` named new file `test_inbox_prodcheck_policy.py` (same INCONCLUSIVE shape as 004) → drop that path; proving tests stay in the new file collected by `uv run --with pytest --python 3.13 pytest -q`. provenance: dispatch-self-heal.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the PR's policy tests overlaid and GREEN after: step 3 sends unrunnable PRODUCTION-CHECKs to P-lines (query + why), not the needs-you/OWNER list; step 7 permits those P-lines; `<P>` equals the number of P-lines printed, mirroring `<O>`; the hard-envelope red flag includes the P-lines; P-lines are not OWNER lines.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing the OWNER bar or CONVERT/FIX-NOW/DROP/KEEP routing.
- Version bump / CHANGELOG / GitHub release.
