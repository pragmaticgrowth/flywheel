---
id: 004-enforce-report-file-gate
title: A missing implementer report file fails the gate
created: 2026-08-28
type: bug
skills: []
model: heavy
size: M
touches:
  - skills/dispatch/scripts/pg_validate.py
  - skills/dispatch/SKILL.md
  - skills/dispatch/references/implementer-brief.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q skills/dispatch/scripts/test_pg_validate.py
  - uv run --with pytest --python 3.13 pytest -q
---

## Outcome (plain language)

The implementer brief already says a missing report file for non-trivial work is a gate finding, but Arm A never checks. After this goal, `pg_validate.py` refuses PASS when the report file is missing, empty, or older than `gate_base`, and Phase 1's "absent is fine" sentence is explicitly the crash-recovery reviewer handoff only — never a license to complete without a report.

## Context / why

provenance: inbox-drain. Fold of two inbox lines (2026-08-20 report-file enforcement + 2026-08-27 crash-scope belt-and-braces). Verified 2026-08-28 against HEAD `3d5d865`:

- `skills/dispatch/references/implementer-brief.md` (Finish): "a missing report file for non-trivial work is itself a gate finding."
- `skills/dispatch/scripts/pg_validate.py`: no `reports/` / `report.md` check (grep empty of those tokens as path checks).
- `skills/dispatch/SKILL.md:936-940` (Phase 1, work-commits-present): "absent is fine — the diff and goal file suffice" — already crash-scoped to the reviewer handoff; it still reads as a general complete-without-report allowance.

Premise (dated 2026-08-28): `ls ~/.local/state/pg-dispatch/nonresidenttax/reports/` has 152 files, none named `140-155-report.md`. The 2026-08-20 measured gap (goals 149-155 wrote none) is consistent with Arm A not requiring the file.

Assumptions: `pg_validate.py` requires the report on every `--goal` run (exists, non-empty, mtime after `--base` commit time), including one-file mechanical edits — a short report is enough. Phase 1 still lets the reviewer proceed without the prior session's report as evidence, but it regenerates a stub from `gate_base..HEAD` (and any STATUS block) *before* running the gate so Arm A cannot `git reset --hard` a sitting that only lacked the file. Arm A verdict on a missing report is `FAIL_FIXABLE`. Placement-guard tests for the Phase 1 sentences live **inside** the existing `skills/dispatch/scripts/test_pg_validate.py` (no new root policy file — a named new file in `acceptance:` makes repro-direction INCONCLUSIVE). Report path remains `~/.local/state/pg-dispatch/<cwd-basename>/reports/<goal-id>-report.md`. The implementer-brief "non-trivial" carve-out is dropped so it matches Arm A.

**Amended 2026-08-28:** `acceptance:` named new file `test_report_file_policy.py` so Arm A repro-direction was INCONCLUSIVE → drop that path and the new-file proving surface; Phase 1 text pins and the CLI report-file tests both live in existing `test_pg_validate.py`; `acceptance:` is that file plus the repo `config.verify` runner. provenance: dispatch-self-heal.

## Acceptance criteria

- [ ] A failing `test_local_*` CLI test in `skills/dispatch/scripts/test_pg_validate.py` reproduces the root cause: with `--head/--base/--goal/--goal-file` and no report file (or empty, or mtime before `--base`), `pg_validate.py` returns `FAIL_FIXABLE`; after the check exists, the same fixture PASSes only when the report exists, is non-empty, and has mtime after the `--base` commit.
- [ ] Tests in the same existing file pin the Phase 1 work-commits-present bullet: stub regen from `gate_base..HEAD` before the gate; "absent is fine" applies only to handing the prior session's report to the reviewer; implementer-brief no longer carves out "non-trivial" work from the missing-report finding.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline — run the same scenario against `git show HEAD:<file>` and confirm the old text decided differently.
- Never push protected branches.

## Out of scope

- Changing the report path.
- Writing reports for historical nonresidenttax goals 140-155.
- Version bump / CHANGELOG / GitHub release.
