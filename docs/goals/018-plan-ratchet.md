---
id: 018-plan-ratchet
title: A plan's outcome bullets are ratcheted the same way a goal's criteria are
created: 2026-08-29
type: feature
skills: []
model: heavy
size: S
touches:
  - skills/ideate/SKILL.md
  - agents/contract-red-team.md
  - test_ratchet_policy.py
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
  - uv run --with pytest --python 3.13 pytest -q test_ratchet_policy.py -k plan
---

## Outcome (plain language)

Goal 016 ratchets goal files, but the outcome bullets do not live in a goal file — they live in the plan, and there is no plan immutability rule anywhere in the repo. Ideate iterates the same plan file by design. So the bar can still be lowered without any amend ever happening: soften the plan, let define-goal contract the outcome goal from the softened text, and every downstream artifact is honestly derived while nothing compares. After this goal, iterating an existing plan classifies every outcome-bullet edit against `git show HEAD:docs/goals/plans/<file>.md` on goal 016's taxonomy — weakening stops for the owner, tightening proceeds — and the red-team catches a plan-derived outcome goal whose bullets were weakened since the previous commit.

## Context / why

Plan: docs/goals/plans/2026-08-28-standard-of-completion.md — Phase 3

Verified against HEAD `cc6a924`:

- There is NO plan immutability rule: grepping `skills/` and `CLAUDE.md` for plan-immutability language returns nothing. Goal files are immutable contracts (`define-goal --amend` the sole exception); plans are freely editable.
- `skills/ideate/SKILL.md` is designed to iterate: re-invoking on a planned idea updates the SAME plan file, and the frontmatter `artifact:` field exists so a later iteration updates the same page.
- The bypass this closes, every step of it individually legitimate: (1) soften `## What will be true when done` in the plan — unguarded today; (2) define-goal contracts the outcome goal from the plan — an honest derivation; (3) goal 016's ratchet compares the goal file against ITS own previous version and sees nothing weakened; (4) the outcome check passes and the plan stamps `status: done` against a lower bar.

**Interfaces** (produced by 016 and 017, consumed by 020): the weakening/tightening taxonomy is goal 016's — reuse it verbatim, do not restate a second, drifting copy. `test_ratchet_policy.py` is created by 016 and EXTENDED here; the tests added here MUST have names containing `plan`, because goal 020's outcome check runs `uv run --with pytest --python 3.13 pytest -q test_ratchet_policy.py -k plan` and `-k` matching nothing exits 5. `agents/contract-red-team.md` item 15 is created by 016 and extended here to cover the plan-derived case.

Scope of what is ratcheted: ONLY the `## What will be true when done` bullets. The rest of a plan — design, phases, context, open questions — stays freely editable, because only the outcome bullets are load-bearing as the standard. Deleting a bullet, dropping its command for prose, loosening its threshold, or removing a `**needs independent review**` flag is weakening; adding a bullet, or pinning a vague one to a command, is tightening. Renaming or removing the `## What will be true when done` section ITSELF is weakening — a classifier keyed on the heading would otherwise read a deleted section as "no bullets present" rather than "every bullet deleted".

One consequence worth stating in the skill text: this makes IDEATE, not just define-goal, a place where the ratchet applies. That is correct — ideate is where the standard is authored, so it is where the standard can first be lowered.

Assumptions: (1) a plan being created for the first time has no previous commit and so has nothing to ratchet against — the rule engages only on iteration of an already-committed plan; (2) "stops for the owner" reuses goal 016's existing owner-fork stop, no new channel; (3) the tests added here extend the existing file rather than creating a second ratchet suite.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the new policy tests overlaid and GREEN after, for each of: (a) iterating an existing plan classifies every outcome-bullet edit as weakening or tightening against `git show HEAD:docs/goals/plans/<file>.md`; (b) a weakening edit stops for the owner; (c) a tightening edit proceeds; (d) only the outcome bullets are ratcheted, the rest of the plan stays freely editable; (e) a first-time plan with no previous commit is exempt.
- [ ] `uv run --with pytest --python 3.13 pytest -q test_ratchet_policy.py -k plan` selects at least one test and passes — the selector goal 020's outcome check depends on.
- [ ] `agents/contract-red-team.md` item 15 also flags a plan-derived outcome goal whose bullets were weakened since the plan's previous commit, contract-blocking.
- [ ] A subagent dry-run decides a plan iteration that deletes one outcome bullet (weakening) and one that adds a command to a vague bullet (tightening), RED-baselined against `git show HEAD:skills/ideate/SKILL.md`, both transcripts in the goal's report file. **Needs independent review**: a reviewer attempts to find a route from a softened plan to a passing outcome check that this rule does not catch, and each route found is either closed in this goal or recorded as an explicit `## Out of scope` line plus an inbox line carrying its earn token — "found none" and "found three, did nothing" must not be indistinguishable.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green, with no fewer tests than the count at this goal's `gate_base` (016 and 017 both add tests before this claim).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches other than the repo's own pre-authorized `origin main`.

## Out of scope

- `CLAUDE.md`'s ideate bullet and any other doc restatement — that is goal 020. Editing it here puts a path outside `touches:` into the diff and fails blast-radius.
- Making plans immutable in general — only the outcome bullets are ratcheted.
- Re-deriving or restating goal 016's taxonomy; it is reused as-is.
- Retrofitting plans written before this rule.
- **Three known residual routes, named so a reviewer has somewhere to put them rather than re-discovering them mid-run.** (a) A plan edited OUTSIDE ideate after its outcome goal is already contracted — the red-team backstop fires at drafting time, so a later softening passes both gates. (b) A weakened TEST BODY under a byte-identical command: 016 compares goal criteria, 018 compares plan bullets, neither compares what a command asserts. (c) A fresh plan file duplicating an existing plan's topic, exempt by the no-previous-commit rule. Closing these needs a different instrument than a text ratchet; each earns an inbox line rather than silent omission.
- Version bump / CHANGELOG / GitHub release — that is goal 020.
