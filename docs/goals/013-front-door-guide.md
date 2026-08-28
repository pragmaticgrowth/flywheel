---
id: 013-front-door-guide
title: Ideate takes a list of issues and goals-status names the next command
created: 2026-08-28
type: feature
skills: []
model: heavy
size: M
touches:
  - skills/ideate/SKILL.md
  - skills/goals-status/SKILL.md
  - skills/goals-status/scripts/goals_status.py
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_front_door_policy.py
  - uv run --with pytest --python 3.13 pytest -q skills/goals-status/scripts/test_goals_status.py
---

## Outcome (plain language)

An owner arriving with N issues has no ideate entry path, and goals-status prints queue state with no next command. After this goal, ideate's description/front matter accepts "I have N issues/items, where do I start?", and goals-status prints one `next: <command>` line derived from the current queue.

## Context / why

provenance: inbox-drain. Two halves of one front-door gap (≤2 findings, one sitting — the status view is what tells the owner which skill to run). Verified 2026-08-28:

- `skills/ideate/SKILL.md` description triggers on single-idea language only; no list/backlog entry path. Handoff of already-shaped wants goes to define-goal batch, but unshaped N-item arrival is unnamed.
- `skills/goals-status/scripts/goals_status.py` empty-queue line is `"docs/goals — nothing open · %d completed"` with no next-command; SKILL.md says print output verbatim.

Assumptions: ideate on an N-item unshaped list writes/updates one plan whose phases map 1:1 onto later define-goal goals (existing ideate behavior), not a skip-to-define-goal. goals-status `next:` first match: any `in_progress`/`blocked`/`not_started` → `/dispatch` (dispatch self-heals blocked contracts in-run); else if `docs/goals/inbox.md` has `- [ ]` lines → `/process-inbox`; else `/ideate`. Kept as one sitting: the status view is what tells the owner which skill to run. `new file: test_front_door_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_front_door_policy.py` is RED at base and GREEN after: ideate's description/front door names the "I have N issues/items, where do I start?" entry path; goals-status output includes a `next:` command line.
- [ ] `uv run --with pytest --python 3.13 pytest -q skills/goals-status/scripts/test_goals_status.py` covers the `next:` derivation (open queue → `/dispatch`; empty queue + inbox lines → `/process-inbox`; empty queue + empty inbox → `/ideate`) and still passes its existing cases.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Changing define-goal batch mode.
- Requiring ideate for already-shaped wants (those still skip to define-goal).
- Version bump / CHANGELOG / GitHub release.
