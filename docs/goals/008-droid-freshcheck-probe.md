---
id: 008-droid-freshcheck-probe
title: Droid fresh-check probes droid and loads filesystem tools
created: 2026-08-28
type: bug
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/references/implementer-brief.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_droid_freshcheck_policy.py
---

## Outcome (plain language)

The Droid fresh-check path can claim "no fresh-context mechanism" while `droid` is on PATH, and a `droid exec -f` lens can return UNVERIFIABLE because no filesystem tools loaded. After this goal, every sanctioned `droid exec` lens command includes `--enabled-tools "Read,Grep,Glob,LS,Execute"`, and `Fresh-check: not run (no fresh-context mechanism available)` is honest only after `command -v droid` fails.

## Context / why

provenance: inbox-drain. Fold of two inbox lines (missing `--enabled-tools`; missing `command -v droid` probe). Verified 2026-08-28:

- `implementer-brief.md` names `droid exec -f <prompt-file>` (or `droid exec "<prompt>"`) with no `--enabled-tools`.
- `grep -n "enabled-tools" skills/` is empty.
- `grep -n "command -v droid" skills/dispatch` is empty.
- The brief still allows `not run (no fresh-context mechanism available)` when "neither path is available" without a probe.

Assumptions: the flag string is exactly `Read,Grep,Glob,LS,Execute` (the measured working retry). Pin it on both sanctioned brief forms (`droid exec -f <prompt-file>` and `droid exec "<prompt>"`) under `skills/dispatch/` only — not define-goal's run-now `droid exec -f`. `new file: test_droid_freshcheck_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_droid_freshcheck_policy.py` is RED at base and GREEN after: both sanctioned Droid lens forms in `skills/dispatch/` (`droid exec -f` and `droid exec "<prompt>"`) include `--enabled-tools "Read,Grep,Glob,LS,Execute"`; the brief requires `command -v droid` to fail before `Fresh-check: not run (no fresh-context mechanism available)` is legal.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing Claude Code lens spawning.
- Raising the Droid lens cap above two.
- Version bump / CHANGELOG / GitHub release.
