---
id: 014-child-timeout-arm-a
title: Child-session timeouts respawn once; Arm A is one wait, not a poll loop
created: 2026-08-28
type: bug
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/SKILL.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_child_timeout_policy.py
---

## Outcome (plain language)

`Error running task subagent: Child session timed out due to inactivity` currently is not in the infra-class retry list, and Arm A joins have been implemented as repeated `sleep`+`ps` polls. After this goal, that timeout is a transient infra death (one unpinned/same-tier respawn), and the Arm A join wording bans repeated sleep-poll calls on Droid explicitly — one wait, then read the output.

## Context / why

provenance: inbox-drain. Fold of two related spawn/join findings (≤2). Verified 2026-08-28:

- Pin-failure / infra-class retry (`skills/dispatch/SKILL.md` ~145-158, Re-entrancy ~473-478) names stream-idle, 529, connection closed, billing/auth/overload — not `Child session timed out due to inactivity`.
- Arm A join (`:765-767`): "Read Arm A's output file (commands still running → wait on that task)" — no ban on repeated sleep-poll. Droid overlap note says run Arm A foreground when there is no reliable background-shell mode, but does not forbid a poll loop if someone backgrounds it anyway.

**Interfaces** (from `009-resume-from-increments`): a missing `STATUS:` or evidenced death with work commits uses the resume-from-increments rung, not a vanilla respawn. This goal's child-session-timeout respawn must name that rung when `gate_base..HEAD` is non-empty.

Assumptions: child-session-timeout is a same-tier transient respawn (does not burn the no-progress fail count; pin-omitted only if the error also names model/provider). Arm A on Droid stays foreground when the harness has no reliable background shell; the Arm A join explicitly bans repeated sleep-poll / task-status poll loops (one wait, then read the output). `new file: test_child_timeout_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_child_timeout_policy.py` is RED at base and GREEN after: infra/transient-death text names `Child session timed out due to inactivity` as a same-tier one-respawn transient (pin-omitted only if the error also names model/provider); Arm A join text bans repeated sleep-poll / task-status poll loops on Droid (one wait, then read the output).
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing the ~3-transient-respawn budget or the cross-fire heartbeat brake.
- Emulating Droid `--parallel`.
- Version bump / CHANGELOG / GitHub release.
