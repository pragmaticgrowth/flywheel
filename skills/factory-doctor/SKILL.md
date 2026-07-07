---
name: factory-doctor
description: Use when setting up or troubleshooting the flywheel factory in a repo — before the first /dispatch, after a missing-queue or unauthenticated-gh error, or any time /dispatch or /define-goal behaves like the environment isn't ready. Preflights software, gh auth, CI, the local working tree, and the docs/goals queue, auto-fixing everything local. Diagnoses and fixes setup; never implements goals or merges PRs.
---

# Factory Doctor

**CLI detection**: this skill works in both Claude Code and Droid (Factory CLI). Detect
your runtime: if Droid-specific tools (CronCreate, CreateAutomation) are available or
`$DROID_PLUGIN_ROOT` is set, you are in Droid. Otherwise Claude Code. The probe checks
settings in both `.claude/` and `.factory/` paths; the fix instructions reference the
appropriate path for your CLI.

Make a repo + machine factory-ready in one idempotent pass. You READ everything via the
shipped probe, AGGRESSIVELY auto-fix everything local and reversible, and REPORT (with the
exact command) everything you physically can't do safely. Running this twice yields the same
green report.

## Run order

1. **Resolve paths.** `$DC` = `doctor_checks.py`, via the surviving scripts' resolution chain
   (the same fallback chain dispatch uses for `$PGVALIDATE`):
   `$CLAUDE_PLUGIN_ROOT/skills/factory-doctor/scripts/doctor_checks.py`
   (Claude Code), else
   `$DROID_PLUGIN_ROOT/skills/factory-doctor/scripts/doctor_checks.py` (Droid), else newest
   `~/.claude/plugins/{cache,marketplaces}/*/flywheel/*/skills/factory-doctor/scripts/doctor_checks.py`
   (Claude Code) or
   `~/.factory/plugins/{cache,marketplaces}/*/flywheel/*/skills/factory-doctor/scripts/doctor_checks.py`
   (Droid).
2. **Read the queue config** (`docs/goals/index.yaml` `config:` if present) for `base`.
   Pass `--base <base>` ONLY when `config.base` is explicitly set. If it is absent, omit
   `--base` — dispatch defaults base to the checked-out branch, so there is no separate
   working branch to mismatch against (the probe reports INFO, not a spurious warning).
3. **Run the read-only probe:** `python3 "$DC" [--base <config.base>]`
   It emits JSON `{checks:[{check,level,detail,fix}], result}` and exits 0/1/2. Never edit it.

## Apply local fixes (aggressive — these and ONLY these)

For each check whose `fix` begins with `FIX:`:

- **`pyyaml` (or any required python dep — BLOCKER with a `FIX:` install):** install it for the
  SAME `python3` dispatch invokes (the one on PATH), then re-import / re-run the probe to confirm
  → FIXED. Try in order, stopping at the first that succeeds: (1) `python3 -m pip install --user
  <pkg>`; (2) if the env is externally-managed (PEP 668 refuses `--user` — common with Homebrew
  python on macOS), `python3 -m pip install --user --break-system-packages <pkg>` — still
  user-scope, and this is the plugin's own pinned, tiny, pure-python dep, so forcing it at user
  scope is safe and IS in scope to auto-fix. Only if BOTH fail, report the manual command under
  needs-you (note any sibling `python3` that already has the dep, e.g. `/usr/bin/python3`, but
  remember dispatch uses the PATH one). A repo venv does NOT help unless dispatch runs under it,
  so don't rely on it. If the harness denies the install in an unattended session, surface it
  under needs-you and apply on the user's explicit "go".
- **`queue` (missing index.yaml):** scaffold `docs/goals/`, `docs/goals/done/`,
  `docs/goals/archive.yaml`, and an `index.yaml` with the default `config:` block:

  ```yaml
  config:
    base: <resolved-base>
    model: inherit
    skills: []
    verify:
      - npm ci
      - npm run build
      - npm test
    # budget:           # optional — uncomment to cap repeated dispatch fires
    #   max_goals_per_session: 1
  goals: {}
  ```

  Adjust `verify` to the repo's actual local build+test commands (inspect `package.json`,
  `Makefile`, `pyproject.toml`, etc.). Mark FIXED.

- **`config-drift` (removed v3 keys in `index.yaml` config — WARN with a `FIX:`):** a queue
  set up under the v3 model still carries keys the v4 one-goal/local-gate model removed
  (`merge`, `wip`, `execution`, `autonomy`); v4 dispatch silently ignores them, so the owner
  keeps thinking in the old PR/worktree/herdr model. **Auto-strip them:** edit
  `docs/goals/index.yaml` config to remove ONLY the keys the probe named, in one atomic edit —
  preserve every live key (`base`, `model`, `skills`, `verify`, `budget`), comments, and
  formatting; NEVER touch `goals:` entries or any goal file. Under `fixed:` echo each removed
  `key=value` (so any owner intent a dead key's value encoded is visible, not silently dropped).
  Mark FIXED. Drives the `queue: …drift` status token below.

Each fix is one atomic edit, named in the report. Like every factory-doctor local fix, leave
the edit in the working tree — do NOT commit or push it (committing is dispatch's job, not the
doctor's). The edits show up in the `working-tree` WARN as expected; the user reviews the
`fixed:` list and commits when ready, before the first `/dispatch`.

## Never (even though you're aggressive)

Push, open a PR, touch the remote, edit a CI workflow, run `gh auth login`/`refresh`
(browser-blocking — report the exact command instead), run a SYSTEM/sudo/global install (`gh`,
`git`, `brew`/`apt`, OR `npm i -g agent-browser` + its Chromium download — report those; the
ONLY install you may run is the plugin's own python dep at `--user` scope, above), `git stash`,
delete branches/worktrees, or write to user-scope `~/.claude/settings.json` (Claude Code) or
`~/.factory/settings.json` (Droid). Anything not in the fix list above is REPORT-only.

## Report (always, last line is the status)

`fixed:` lists what you changed (one line each). `needs-you:` lists every BLOCKER/WARN the
probe reported that you did NOT auto-fix — copy its `detail` and `fix` fields verbatim; that
text IS the exact command or guidance for the human (the `gh auth refresh …` line, or any
install command for a missing system tool). The probe checks `browser-verify`: if the repo has
frontend/UI work (a UI framework in package.json, or any goal referencing `agent-browser`)
but `agent-browser` isn't installed, it WARNs with the install command — REPORT-only (a global
npm install + Chromium is a system-level change, never auto-run). The probe also emits three
REPORT-only loop-health checks (all read-only — never auto-fixed): `queue-liveness` (WARN naming
any `in_progress` goal with no work commits on the branch after its claim commit — a stale claim /
silent-death candidate dispatch will respawn or that needs unblocking), `goal-contracts`
(WARN naming any active goal whose file lacks a checkable done-condition — tighten via
`/define-goal` before dispatch picks it up), and `limit-resilience` (WARN when a dispatch loop
demonstrably fires on this repo — heartbeat log lines exist — but nothing survives an account
usage-limit stop: no external scheduler firing fresh sessions and no `StopFailure` hook; its
`fix` field carries the limit-proofing guidance from loop-architect Step 5. INFO-only when no
loop has fired here or a rail is detected). The `verify` check WARNs if `config.verify` is
absent and there are active goals — copy its `fix` (add a `verify:` list to `index.yaml`). Then
one status line:

`[doctor] software: <ok|missing> · auth: <ok|n/a> · verify: <configured|⚠ missing|n/a> · working-tree: <clean|⚠ dirty> · working-branch: <ok|⚠ off-base> · ci: <present|none> · queue: <valid|scaffolded|drift> · health: <live|⚠ stale claims|⚠ underspecified goals|⚠ limit-exposed> · result: READY|WARN|BLOCKER`

## Relationship to the other skills

- `define-goal` runs the queue subset of these checks before creating the first `index.yaml`.
- `dispatch` Phase 0 runs the read-only probe each fire and cites `/factory-doctor` on a
  failure it can't handle; its permission-stall fix is "run `/factory-doctor`".
- This skill never claims goals, spawns implementers, or merges — that's `dispatch`.
