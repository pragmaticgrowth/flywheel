---
id: 020-standard-of-completion-outcome
title: The standard-of-completion chain is proven as a whole, and ships
created: 2026-08-29
type: chore
skills: []
model: heavy
size: M
touches:
  - CLAUDE.md
  - CHANGELOG.md
  - .claude-plugin/plugin.json
acceptance:
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

This is the plan's own outcome check — the phase that measures the WHOLE rather than another piece, and the first goal in this repo to be one. It builds nothing. It runs every bullet in the plan's `## What will be true when done`, shows each one FAILING at the plan's amended base commit `4007651` and PASSING at HEAD, records the documentation the chain invalidated, and ships v12.4.0. If any bullet cannot be shown failing at base, that bullet was measuring a piece rather than the whole and the goal stops for the owner rather than being quietly relaxed.

## Context / why

Plan: docs/goals/plans/2026-08-28-standard-of-completion.md — Phase 5

This goal exists because of the finding the whole chain came from: an agent that authors its own definition of done stops early, having validated every piece in the context that produced it. Goals 016–019 are those pieces. Nothing before this goal asks whether the thing the plan set out to deliver actually works.

`type: chore` per the plan's owner-resolved question — a verification-only goal is closest to the chore shape and has no new behavior to prove. It is stamped `model: heavy` rather than the chore lane's medium deliberately: the rubric reserves medium for ROTE chore work (lint/doc/config sweeps, ports with an exact source of truth), and demonstrating fail-at-base across seven commands requires real git archaeology, so "unsure → the stronger" applies. Goal 019 adds the type-shape sentence that admits a verification goal as `type: chore` without a no-behavior-change proof — without it, the red-team's Type shape item rejects this contract, which is why the dependency is hard.

The plan's `## What will be true when done` carries EIGHT bullets: seven commands plus one `**needs independent review**` bullet. All eight are discharged here — the seven below by running them, the eighth from the four phase report files (criterion 6). Dropping the review bullet would itself be a weakening under this chain's own taxonomy (`needs independent review` flag removed), which is precisely the failure this goal exists to catch.

The seven commands to run, in order:

```
1  pytest -q test_ratchet_policy.py                                              (016)
2  pytest -q test_ratchet_policy.py -k plan                                      (018)
3  pytest -q test_outcome_check_policy.py                                        (017)
4  pytest -q test_outcome_check_policy.py -k committed                           (017)
5  pytest -q test_outcome_check_policy.py -k test_plan_status_done_means_outcome_check_passed   (019)
6  pytest -q test_outcome_check_policy.py -k report_only                         (019)
7  pytest -q                                    regression guard, green at BOTH ends
```

each prefixed `uv run --with pytest --python 3.13`. Commands 1–6 must FAIL at `4007651` (the suites do not exist there) and pass at HEAD; command 7 is green at both ends and must never drop below the 360 tests passing at authoring. A `-k` selector matching nothing exits 5, so an empty selection is a FAILURE of that bullet, never a pass.

Documentation the chain invalidates, per the repo's own minimal-docs rule (update what a change actually invalidates, nothing more): `CLAUDE.md` gains the ratchet and outcome-check mechanics in the define-goal, ideate, and dispatch bullets, and its repetition of the reality check's wrong "eight" count is corrected. `README.md` is NOT expected to change — no skill's purpose, invocation, install, or config model changes — so leave it alone unless one of those facts actually moved.

Assumptions: (1) v12.3.0 shipped 2026-08-28, so this chain is v12.4.0; (2) the release follows the repo's standing rule — bump `plugin.json`, add a dated `CHANGELOG.md` section, annotated tag on the bump commit, `gh release create` with notes from that section, `--latest`; (3) pushing is pre-authorized and a terminal stop ships it.

## Acceptance criteria

- [ ] Each of commands 1–6 above is shown FAILING at `4007651` and PASSING at HEAD, with both outputs recorded in the goal's report file. Each of the six evidence blocks carries, verbatim: the `git -C <worktree> rev-parse HEAD` output (must read `4007651…`), the full command as run, and pytest's final summary line at both ends — base showing exit 4 (file or directory not found) or exit 5 (no tests ran), head showing `N passed`. A bullet that cannot be shown failing at base stops the goal for the owner — it is not relaxed, reworded, or dropped.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green at HEAD and reports no fewer than 360 tests.
- [ ] `CLAUDE.md` documents the amend ratchet, the plan ratchet, the outcome-check rule with its committed-test form, and the Report-only carve-out; its reality-check count is corrected to match the shipped header.
- [ ] `.claude-plugin/plugin.json` reads `12.4.0` and `CHANGELOG.md` carries a dated `## [12.4.0]` section in the repo's existing section shape; `plugin-dev:plugin-validator` runs clean after the manifest edit.
- [ ] The working tree is clean at hand-off — every edit committed, no untracked files left. (Pushing, tagging, and the GitHub Release are NOT this goal's; see Out of scope.)
- [ ] **Needs independent review** — the plan's eighth outcome bullet is discharged, not dropped: the four phase report files under `~/.local/state/pg-dispatch/<SLUG>/reports/` (016, 017, 018, 019) are cited BY PATH in this goal's report file, each confirmed to contain its named dry-run transcript and RED baseline. A phase whose transcript is missing stops the goal for the owner — it is not waived.

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- The remote is public and permanent: no secrets, and stay mindful of real client/project names.
- Never push protected branches other than the repo's own pre-authorized `origin main`.
- Reach the base commit ONLY via a throwaway worktree — `git worktree add /tmp/soc-base 4007651`, run the six commands there, `git worktree remove /tmp/soc-base` after. NEVER `git checkout` the base commit in the working tree: the claim commit and this goal's increments are live on the branch, and a death mid-archaeology strands the run in detached HEAD with a scrambled `gate_base..HEAD`.

## Out of scope

- **Minting the tag and the GitHub Release.** Dispatch squashes `gate_base..HEAD` into one `feat(goal NNN)` commit on PASS and runs `git reset --hard gate_base` on FAIL. A tag created inside the goal would point at a sha the squash discards, violating the repo's own "tag the bump commit" rule; and `gh release create` is irreversible and externally visible, so a gate FAIL would leave a published release pointing at a commit that never reaches `main`. The reversible half (the `plugin.json` bump and the `CHANGELOG.md` section) is in this contract; the irreversible act is a POST-SETTLE step run against the squashed settle commit. The implementer's report file ends with the exact handoff commands: `git tag -a v12.4.0 <settle-sha> -m "…"`, `git push origin v12.4.0`, `gh release create v12.4.0 --title "…" --notes-file <section> --verify-tag --latest`.
- Pushing `main`. That is dispatch's ship step at a terminal stop, not a goal criterion — the implementer cannot drive "in sync with origin/main" to true while the settle commit does not yet exist.
- Any new rule or mechanic — goals 016–019 own all of those. This goal only measures and ships.
- Relaxing an outcome bullet that fails at HEAD; that is a design fault and stops for the owner.
- Growing `README.md` beyond the user-facing facts it already states.
- Retrofitting the outcome-check rule onto plans written before it.
