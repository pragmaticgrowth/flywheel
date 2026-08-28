---
id: 016-amend-ratchet
title: A weakening amend stops for the owner; a tightening one still runs unattended
created: 2026-08-29
type: feature
skills: []
model: heavy
size: M
touches:
  - skills/define-goal/SKILL.md
  - agents/contract-red-team.md
  - test_self_heal_policy.py
  - test_ratchet_policy.py
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

Since v12.0.0 self-heal rewrites a blocked goal's contract mid-run with nobody watching, and nothing compares the rewrite against what it replaced — so the bar a goal is held to can quietly get easier while every artifact stays honestly derived. After this goal, an amend classifies each edit as weakening or tightening against `git show HEAD:docs/goals/<id>.md`; a weakening amend stops for the owner EVEN under the drain waiver, a tightening one proceeds unattended exactly as today, and the amendment note records which it was. RETIRE falls under the same rule: the disproving evidence must be a command output or a quoted primary artifact, never the agent's own reasoning alone.

## Context / why

Plan: docs/goals/plans/2026-08-28-standard-of-completion.md — Phase 1

Verified against HEAD `cc6a924` (line numbers shifted in v12.3.0 — anchor on the quoted text, not the numbers):

- `skills/define-goal/SKILL.md:948` — `## Amend mode`; it rewrites only the criteria the block reason names defective, byte-for-byte elsewhere, and nothing compares the result against its predecessor. Grep for weaken/loosen/original/previous over define-goal returns nothing.
- `skills/define-goal/SKILL.md:1058` — "The Self-heal drain waiver above is the ONE sanctioned…"; the waiver waives question rounds and owner confirmation but explicitly never the red-team. That makes the red-team the one enforcement point self-heal cannot route around — putting the ratchet ONLY in amend step 4 would leave it waivable.
- `agents/contract-red-team.md:107` — the rubric ends at item **14** (`Absolute claims`). The new item is **15**.
- `skills/define-goal/SKILL.md:718` — "Run these **eight** checks" while items **1–9** are listed (item 9 arrived in v12.1.0 and the header was never updated). This goal adds item 10, so the header becomes "ten" and the stale count is fixed in passing.
- `test_self_heal_policy.py:145-150` — `test_define_goal_reality_check_has_eight_checks` asserts `"eight checks" in text` at `:148`. It pins the OLD count and must be updated in this same change, name included, or the suite goes red.

Split seam, if the sitting stretches: criterion 1's sub-item (e), the RETIRE evidence rule, lands in a different section of `skills/define-goal/SKILL.md` from the amend ratchet and is the only sub-item 018 does not reuse. Split there and nowhere else.

**Interfaces** (consumed by 018 and 020): the weakening/tightening taxonomy defined here is reused verbatim by goal 018 for plan outcome bullets, so name it as a reusable classification, not as amend-only prose. `test_ratchet_policy.py` is created here and EXTENDED by 018 with test names containing `plan` (goal 020's outcome check runs `pytest -q test_ratchet_policy.py -k plan`, which exits 5 if nothing matches).

The taxonomy, per the plan's Design section — weakening (stops for the owner): a criterion deleted and not replaced; a threshold loosened (fewer, slower, lower coverage); a runnable command becoming an assertion a human or agent must vouch for; a drivable-surface check becoming a code-reading check; a before/after criterion losing its BEFORE; a `needs independent review` flag removed; `touches:` narrowed so a path the criteria still require drops out. Tightening or repair (proceeds unattended): a criterion added; a wrong path or command corrected so it actually runs; a two-readable criterion pinned to the STRICTER reading; a criterion split per Drainability; a not-yet-true capability moved to a `depends_on` prior.

Assumptions: (1) "stops for the owner" reuses the existing owner-fork stop the waiver already honors — no new escalation channel; (2) the amendment note gains one field naming the classification and, for a weakening, what was weakened; (3) `new file: test_ratchet_policy.py` is collected by the stable `pytest -q` runner and is NEVER named as its own `acceptance:` path (the 004/006/008/011/012/014/015 lesson).

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q` is RED at base with the new policy tests overlaid and GREEN after, for each of: (a) amend mode classifies every edit as weakening or tightening against `git show HEAD:docs/goals/<id>.md`; (b) a weakening amend stops for the owner even under the drain waiver, stated where the waiver is defined; (c) a tightening amend still proceeds unattended; (d) the amendment note records the classification; (e) retire under the waiver requires a command output or quoted primary artifact as disproving evidence.
- [ ] `agents/contract-red-team.md` carries a new item **15, Ratchet** — given the previous contract, flag any weakened criterion — stating it is contract-blocking, in the existing numbered-item shape.
- [ ] The reality check gains item **10** (amend-only, mirroring red-team item 15) and its header count is corrected from "eight" to "ten"; `test_self_heal_policy.py`'s count guard is updated in the same change, assertion **and test name** (`test_define_goal_reality_check_has_eight_checks` asserting "ten checks" would reintroduce the exact stale-count drift this goal removes).
- [ ] A subagent dry-run decides one weakening and one tightening amend scenario correctly, each with a RED baseline against `git show HEAD:skills/define-goal/SKILL.md`, both transcripts written into the goal's report file under a `## Ratchet dry-run` heading, each stating the scenario, the RED-baseline verdict, and the post-change verdict.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 360 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches other than the repo's own pre-authorized `origin main`.

## Out of scope

- `CLAUDE.md`'s restatement of the reality-check count and the red-team item list — that is goal 020. Editing it here puts a path outside `touches:` into the diff and fails blast-radius.
- Ratcheting PLAN outcome bullets — that is goal 018, which reuses this taxonomy.
- Changing what the drain waiver already waives (question rounds, the approval table) or the red-team's unwaivable status.
- Touching the per-goal gate, which is already an independent standard the implementer did not author.
- Version bump / CHANGELOG / GitHub release — that is goal 020.
