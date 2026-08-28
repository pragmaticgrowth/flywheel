---
id: 010-subsystem-count-slice
title: A three-subsystem touches list is a chain, not a goal
created: 2026-08-28
type: feature
skills: []
model: heavy
size: M
touches:
  - skills/define-goal/SKILL.md
  - agents/contract-red-team.md
  - CLAUDE.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_subsystem_count_policy.py
---

## Outcome (plain language)

Size today blocks on a qualitative "spans multiple subsystems" signal that an atomicity Context note can downgrade to advisory, and Slice endorses a single vertical goal that crosses layers. After this goal, a `touches:` list that spans three or more subsystem bands is contract-blocking Size even with an atomicity note; red-team item 7 is updated in lockstep. Slice's vertical-cut test is unchanged.

## Context / why

provenance: inbox-drain. Verified 2026-08-28:

- `skills/define-goal/SKILL.md` Size (one-sitting): qualitative "one subsystem"; span trigger downgradable by an atomicity Context note.
- Slice: blocks horizontal cuts; endorses thin end-to-end paths that may cross layers.
- `agents/contract-red-team.md` items 7–8 match.
- Field: `/root/ajww/aj-leads/docs/goals/249-private-pool-agency-owner-priority.md:9` is 16 globs across supabase/migrations + apps/api + apps/web + docs (4 bands), 4 acceptance runners; it passed the checks and the lane run then needed touches-closure amends.

Assumptions (drain-waiver reading): count **product** bands only — migration/schema (`**/migrations/**`, `**/supabase/**`), API/server (`**/apps/api/**`, `**/server/**`), web/UI (`**/apps/web/**`, `**/frontend/**`). `docs/goals/**` (plans, inbox, index, goal files) does **not** count. Product docs (`docs/**` excluding `docs/goals/**`) may count as a fourth band but the trigger is **≥3 of the three product bands** {migration, API, web} — so a thin vertical `apps/api` + `apps/web` + a linked plan file stays legal. The atomicity-note downgrade does **not** apply to this count trigger (it still applies to the qualitative two-band span). Slice is not rewritten. The split of a 3-product-band goal is a `depends_on` chain of thinner vertical slices. Both define-goal copies of Size must change: the one-sitting authoring rule and the red-team Size check. `new file: test_subsystem_count_policy.py`.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_subsystem_count_policy.py` is RED at base and GREEN after: both define-goal Size copies (one-sitting authoring rule AND red-team Size check), `agents/contract-red-team.md` item 7, and the CLAUDE.md Size restatement name a contract-blocking trigger when `touches:` hits ≥3 of {migration/schema, API/server, web/UI}; `docs/goals/**` does not count; an atomicity Context note does not downgrade this count trigger.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Rewriting Slice to forbid vertical end-to-end goals of one or two bands.
- Changing `touches:` closure/existence checks.
- Version bump / CHANGELOG / GitHub release.
