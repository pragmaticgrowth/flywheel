---
id: 012-capture-bar-default
title: Inbox lines name their earning condition; Report-only is the default
created: 2026-08-28
type: bug
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/SKILL.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_capture_bar_policy.py
---

## Outcome (plain language)

The v11.6 capture bar still lists Capture before Report-only and the inbox-line template has no earning-condition field, so settle-time captures keep landing. After this goal, Report-only is the DEFAULT disposition (unsure → Report-only), and every inbox line names which earning condition it meets (live defect / genuinely new work / owner decision) in the line itself.

## Context / why

provenance: inbox-drain. Verified 2026-08-28: `skills/dispatch/SKILL.md:852-862` — Capture is gated on the bar, Report-only is "under the bar", no "default" wording, template at `:856` is `- [ ] <YYYY-MM-DD> <source-goal-id> <bug|feature|chore> — <one-line description> (evidence: …)` with no earning token. `grep -i earning skills/` is empty. `/root/romy/docs/goals/inbox.md` is 647 lines (capture claimed 580; trend holds). Last capture-bar text edit: `532b135` (v11.6.0).

Assumptions: the earning token is a required parenthetical or field in the template, e.g. `(earn: live-defect|new-work|owner-decision)`. Unsure / latent / wording nits stay Report-only. `new file: test_capture_bar_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_capture_bar_policy.py` is RED at base and GREEN after: Settle triage states `unsure → Report-only` adjacent to the four dispositions; Capture is legal only when the line carries an earning token; the inbox-line template requires naming the earning condition (live defect / genuinely new work / owner decision) in the line itself.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Sweeping or rewriting existing `docs/goals/inbox.md` lines in this or other repos.
- Changing process-inbox triage buckets.
- Version bump / CHANGELOG / GitHub release.
