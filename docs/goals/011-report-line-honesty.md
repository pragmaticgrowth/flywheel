---
id: 011-report-line-honesty
title: The closing turn stays last and counters come from one index read
created: 2026-08-28
type: bug
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/SKILL.md
  - CLAUDE.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_report_line_honesty_policy.py
---

## Outcome (plain language)

Droid drains currently let plan-tool acknowledgement prose land after the report line, and mid-drain report-line counters have drifted by remembered increments. After this goal, the envelope names the plan-tool update as a pre-closing action so the closer stays last, and Phase 4 requires deriving done/ready/blocked/total from ONE `index.yaml` read at settle time — never an incremented remembered count.

## Context / why

provenance: inbox-drain. Fold of two inbox lines (plan-tool closer leak; counter drift). Verified 2026-08-28: `skills/dispatch/SKILL.md` OUTPUT ENVELOPE (`:1011-1034`) says the closing turn is "the report line, the summary line, one bullet per needs-you item, one bullet per fyi item. Nothing else" and "The counts come from the index after this iteration's mutations" — but it does not sequence a plan-tool update as a pre-closing action, and it does not forbid deriving counters by incrementing a remembered count.

Assumptions: "plan-tool" means any harness plan/artifact status acknowledgement (including "Plan is up-to-date."). The pre-closing action is still allowed; it must happen before the closer, not after. `new file: test_report_line_honesty_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_report_line_honesty_policy.py` is RED at base and GREEN after: the envelope rule in `skills/dispatch/SKILL.md` and the matching CLAUDE.md restatement name the plan-tool update as a pre-closing action so the closer stays last; Phase 4 requires done/ready/blocked/total from ONE `index.yaml` read at settle, never an incremented remembered count.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing the report-line field set or the two-channel needs-you/fyi split.
- Version bump / CHANGELOG / GitHub release.
