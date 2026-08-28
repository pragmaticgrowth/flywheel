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
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

The Droid fresh-check path can claim "no fresh-context mechanism" while `droid` is on PATH, and a `droid exec -f` lens can return UNVERIFIABLE because no filesystem tools loaded. After this goal, every sanctioned `droid exec` lens command includes `--enabled-tools "Read,Grep,Glob,LS,Execute"`, and `Fresh-check: not run (no fresh-context mechanism available)` is honest only after `command -v droid` fails.

## Context / why

provenance: inbox-drain. Fold of two inbox lines (missing `--enabled-tools`; missing `command -v droid` probe). Verified 2026-08-28:

- `implementer-brief.md` names `droid exec -f <prompt-file>` (or `droid exec "<prompt>"`) with no `--enabled-tools`.
- `grep -n "enabled-tools" skills/` is empty.
- `grep -n "command -v droid" skills/dispatch` is empty.
- The brief still allows `not run (no fresh-context mechanism available)` when "neither path is available" without a probe.

Assumptions: the flag string is exactly `Read,Grep,Glob,LS,Execute` (the measured working retry). Pin it on both sanctioned brief forms (`droid exec -f <prompt-file>` and `droid exec "<prompt>"`) under `skills/dispatch/` only — not define-goal's run-now `droid exec -f`. `new file: test_droid_freshcheck_policy.py` is collected by the stable full-suite runner. Its tests enumerate every sanctioned Droid lens command code span in the implementer brief's harness note, require exactly the two specified prompt-file/inline forms with the exact flag, and reject any sanctioned form that lacks it; the generic attended-run `droid exec` mention in dispatch SKILL.md is not a lens command.

**Amended 2026-08-28:** acceptance named a new test file and positive-only assertions allowed unsafe extra forms → use the stable full-suite runner and enumerate/reject every sanctioned lens command. provenance: dispatch-self-heal.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the new policy tests overlaid and GREEN after: the tests enumerate every sanctioned Droid lens command in the implementer brief's harness note, require exactly the two prompt-file/inline forms with `--enabled-tools "Read,Grep,Glob,LS,Execute"`, reject any noncompliant extra sanctioned form, and require `command -v droid` to fail before `Fresh-check: not run (no fresh-context mechanism available)` is legal.
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
