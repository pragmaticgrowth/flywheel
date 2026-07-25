---
id: 001-prove-the-gate-runs
title: factory-doctor proves the local gate actually runs
created: 2026-07-25
type: feature
skills: []
model: heavy
size: M
touches: ["skills/factory-doctor/scripts/doctor_checks.py", "skills/factory-doctor/SKILL.md"]
acceptance: ["python3 -m pytest -q skills/factory-doctor/scripts/test_doctor_checks.py", "python3 -m pytest -q"]
---

## Outcome (plain language)

Today `/factory-doctor` reports a green gate as long as `config.verify` is a non-empty
list — it never runs those commands. In a large repo the common failure is a *declared but
wrong* gate: a renamed npm script, a wrong workspace filter, a command list that builds but
never tests. The doctor says READY, and every later dispatch PASS is unearned. After this
goal, factory-doctor executes the declared verify commands and tells you, with the failing
command and its exit code, whether the gate you rely on actually runs.

## Context / why

Design brief: `docs/goals/briefs/2026-07-25-close-the-gap.md` (piece A).

Located by recon:

- `skills/factory-doctor/scripts/doctor_checks.py:170-179` — `verify_check(verify_cmds,
  active_goals)` only tests `if not verify_cmds`, then reports
  `f"verify: {len(verify_cmds)} command(s) configured"`. It never executes anything.
- Check dict shape is fixed at 4 keys — `check`, `level`, `detail`, `fix` — emitted either
  via the nested `add()` helper (`:322-326`) or as standalone pure functions appended by
  `run_checks` (e.g. `C.append(vc)` at `:447`). Levels are the bare strings
  `INFO | WARN | BLOCKER`; there is no constant. Aggregation at `:455-456` maps them to
  `result` `READY | WARN | BLOCKER`, and `main` maps that to exit `0 | 1 | 2` (`:471-473`).
- CLI is argparse (`:460-473`) with `--base` and `--self-test` today.
- The existing subprocess wrapper `_run(cmd)` (`:100-105`) is argv-list, no shell, no
  timeout, no cwd — deliberately unsuited to running `config.verify` strings like
  `npm run build && npm test`.
- The runner to mirror is `pg_validate.py:506-574`: `_resolve_shell()` (honors `$PG_BASH`,
  rejects the WSL `System32\bash.exe` stub) and `_run_cmds(cmds, cwd)` (sequential, never
  short-circuits, `[shell, "-lc", c]`, `cwd`, timeout from `PG_VALIDATE_TIMEOUT` default
  1800, `TimeoutExpired` → sentinel exit `124`). It is **not importable** — the two scripts
  live in different skill dirs, are not a package, and each is resolved independently at
  runtime; the logic must be duplicated.
- `verify_cmds` / `active_goals` are pre-initialized to `[]` / `0` before the queue-parse
  guard (`:383-384`), so a missing index, absent PyYAML, or malformed YAML leaves them at
  the defaults rather than crashing.

**Recursion landmine (must be handled).** `test_doctor_checks.py:117-124`
(`test_runner_emits_valid_json_and_exit_code`) runs the real script via subprocess with
`cwd` = the flywheel repo root, whose `docs/goals/index.yaml` declares
`verify: python3 -m pytest -q`. If the new check executes verify commands unconditionally,
that test recursively spawns the full suite.

Note on running the doctor in THIS repo: with execution on by default, `/factory-doctor`
here runs `python3 -m pytest -q`, which itself invokes `doctor_checks.py` with
`--skip-verify-run` one level down. That nesting is bounded and terminates; it is expected,
not a defect.

Test conventions: plain module-level pytest functions, module loaded as `dc` via
`importlib.util.spec_from_file_location` (`:1-4`); verdict logic tested by direct calls on
pure functions; commands faked by `monkeypatch.setattr(dc, "_run", ...)` — the file patches
doctor_checks' own wrapper, never `subprocess` itself.

## Acceptance criteria

- [ ] A new pure verdict function in `doctor_checks.py` — named `verify_run_check` — takes
  already-computed results (never runs anything itself) and returns the standard 4-key dict
  with `check: "verify-run"`, following the `verify_check` / `limit_resilience_check`
  pattern.
- [ ] Verdict policy, each proven by a unit test calling `verify_run_check` directly. Every
  such test asserts the `level` AND that `detail` contains the offending command string and
  its exit code; for the BLOCKER cases it also asserts `fix` is non-empty:
  - every command exits 0 → `INFO`, detail names how many ran
  - any command exits non-zero → `BLOCKER`, detail names the failing command verbatim and
    its exit code, `fix` names the command to reproduce it
  - any command is unresolvable (exit `127`) → `BLOCKER`, detail names that command
  - any command times out (sentinel exit `124`) and none failed otherwise → `WARN`
  - execution skipped → `INFO`, detail says the gate was not run
  - `verify_cmds` empty → `INFO`, and no execution is attempted
- [ ] A separate thin executor function runs the commands with a POSIX shell, `cwd` set to
  the repo root, sequentially without short-circuiting, honoring `$PG_BASH`, with a
  per-command timeout from `PG_DOCTOR_VERIFY_TIMEOUT` (default `1800`), mapping
  `TimeoutExpired` to exit `124` — mirroring `pg_validate.py:555-574`. It is a distinct
  function from the verdict function so tests can `monkeypatch.setattr` it away.
- [ ] `--skip-verify-run` exists as an argparse flag and suppresses execution; a unit test
  asserts the skipped path emits the `INFO` skipped verdict and calls no executor.
- [ ] `test_runner_emits_valid_json_and_exit_code` no longer runs this repo's own pytest
  recursively: the test passes `--skip-verify-run`, and it still asserts exit code in
  `(0,1,2)` and valid JSON.
- [ ] `skills/factory-doctor/SKILL.md` documents the new flag in its run-order step 3
  command line, and its status line includes a `verify:` token distinguishing
  `ran-green | ⚠ ran-red | ⚠ unresolved | ⚠ timeout | configured (unrun) | missing`.
- [ ] `skills/factory-doctor/SKILL.md` states that a failing verify command is REPORT-only —
  never auto-fixed — consistent with its existing never-fix boundary.
- [ ] `python3 -m pytest -q skills/factory-doctor/scripts/test_doctor_checks.py` passes.
- [ ] `python3 -m pytest -q` (full suite) passes.
- [ ] Running `python3 skills/factory-doctor/scripts/doctor_checks.py --base main
  --skip-verify-run` from the repo root exits 0/1/2 and emits JSON containing a check with
  `"check": "verify-run"` — output shown in the transcript.

## Constraints (hard rules)

From CLAUDE.md, verbatim:

- **Skills-first (formerly skills-only).** Don't add MCP servers, commands, agents, or hooks
  here without an explicit ask.
- **Portability.** Skills must not contain user-specific absolute paths (`/Users/...`) for
  either harness.
- **Push every time — on every completion, the FULL tree.**
- Never push protected branches.

Plus:

- Do NOT change `verify_check`'s existing behavior or its `check: "verify"` id — the new
  check is additive and separately named.
- Do NOT auto-fix, repair, or modify anything in the target repo's test suite or
  `config.verify` list in response to a red gate. REPORT only.
- Do NOT make `doctor_checks.py` import from `pg_validate.py` — the scripts are
  independently resolved; duplicate the runner.

## Out of scope

- Scaffolding tests or generating a gate for a repo that has none.
- Judging whether the verify command list is *sufficient* (e.g. warning that no test-shaped
  command is present) — too heuristic to raise a BLOCKER.
- Any change to `pg_validate.py` or to dispatch's own gate.
- Making dispatch run the doctor probe (it does not today, despite prose claiming otherwise;
  that drift is recorded in the brief and is not this goal's work).
- `README.md` and `public/index.html` edits: neither doc enumerates helper-script flags, and
  `--skip-verify-run` is internal to `doctor_checks.py`, not a skill invocation. Do NOT edit
  them — they are outside this goal's declared `touches:` and would fail the gate's
  blast-radius check.
- Version bump, `CHANGELOG.md` entry, git tag, and GitHub release. Goals 001-003 ship as ONE
  release performed by the repo owner after all three complete. Do NOT edit
  `.claude-plugin/plugin.json`, `CHANGELOG.md`, the site `.ver-pill`, or the README version
  badge.

## If blocked

Stop and report attempted paths, evidence, the blocker, and what would unlock you.
If the same acceptance command fails the same way twice in a row, or after ~3 honest
attempts a criterion can be neither satisfied nor shown measurable, declare
GOAL_UNREACHABLE with evidence (which criterion, why unmeasurable, last measurement) and
stop — never retry the identical failing approach.

## Goal contract

/goal Add a `verify-run` check to `skills/factory-doctor/scripts/doctor_checks.py` that
executes the repo's `config.verify` commands and reports whether the declared local gate
actually runs, per the Acceptance criteria section of docs/goals/001-prove-the-gate-runs.md.
Verdict logic lives in a pure `verify_run_check` function (INFO all-green / BLOCKER on
non-zero or unresolvable / WARN on timeout / INFO when skipped or empty); execution lives in
a separate thin runner mirroring pg_validate.py's `_resolve_shell` + `_run_cmds` (shell,
cwd=repo root, `$PG_BASH`, `PG_DOCTOR_VERIFY_TIMEOUT` default 1800, timeout→124). Add a
`--skip-verify-run` argparse flag, and make the existing
`test_runner_emits_valid_json_and_exit_code` pass that flag so the suite never recursively
invokes itself. Update `skills/factory-doctor/SKILL.md` with the flag and the new status-line
token. Done when `python3 -m pytest -q skills/factory-doctor/scripts/test_doctor_checks.py`
passes, `python3 -m pytest -q` passes, and `python3
skills/factory-doctor/scripts/doctor_checks.py --base main --skip-verify-run` emits JSON
containing a `verify-run` check. Before stopping on success, re-print the final
acceptance-command outputs. Stop when every criterion verifiably passes, or when blocked or
a criterion proves unreachable (follow "If blocked"). Stop after 20 turns.
