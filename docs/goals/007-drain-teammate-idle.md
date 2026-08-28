---
id: 007-drain-teammate-idle
title: Parallel-mode closing turns drain stale teammate pings
created: 2026-08-28
type: feature
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/references/parallel-mode.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_lane_idle_policy.py
---

## Outcome (plain language)

Claude Code parallel-lane teammate `idle_notification` pings pile up across continuation sessions and can open the closing turn. After this goal, the parallel-mode report/handoff step drains or dismisses pending teammate messages before the closing turn. Droid has no teammate surface; the instruction is Claude-Code-only.

## Context / why

provenance: inbox-drain. Verified 2026-08-28: `grep -i idle/teammate/notification` over `skills/dispatch/references/parallel-mode.md` is empty of any drain/dismiss instruction. Dispatch SKILL.md bans agent-team teammates as implementers but does not handle leftover idle notifications from lane spawns.

Premise (dated 2026-08-28): inbox evidence named 307 `idle_notification` occurrences across mfa sessions 446477cd and b30fcd80 — a Claude Code teammate-idle surface. Assumptions: the instruction lives in `parallel-mode.md` (report/handoff / settle step), Claude-Code-only, and names the harness event `idle_notification`: consume or dismiss pending `idle_notification` / teammate-inbox messages before the closing turn. No new agent or hook. `new file: test_lane_idle_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_lane_idle_policy.py` is RED at base and GREEN after: `parallel-mode.md` requires consuming or dismissing pending `idle_notification` teammate messages before the closing turn, and names the instruction as Claude-Code-only.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Emulating parallel lanes on Droid.
- Changing lane admission, integration lock, or settle triage.
- Version bump / CHANGELOG / GitHub release.
