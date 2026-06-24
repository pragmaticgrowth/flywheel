---
name: factory-doctor
description: Use when setting up or troubleshooting the pg-plugin factory in a repo — before the first /dispatch, after a "gh pr merge permission denied" / unauthenticated-gh / missing-queue error, or any time /dispatch or /define-goal behaves like the environment isn't ready. Preflights software, gh auth, harness merge permissions, branch protection, CI, and the docs/goals queue, auto-fixing everything local. Diagnoses and fixes setup; never implements goals or merges PRs.
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

1. **Resolve paths.** `$DC` = `doctor_checks.py`, `$SAFEMERGE` = `pg_safe_merge.py`, via the
   same fallback chain dispatch uses for `$PM`: `$CLAUDE_PLUGIN_ROOT/skills/<dir>/scripts/<f>`
   (factory-doctor for `$DC`, dispatch for `$SAFEMERGE`; `$CLAUDE_PLUGIN_ROOT` is set by both
   Claude Code and Droid — Droid provides it as an alias for `$DROID_PLUGIN_ROOT`), else
   newest `~/.claude/plugins/{cache,marketplaces}/*/pg-plugin/*/skills/<dir>/scripts/<f>`
   (Claude Code) or `~/.factory/plugins/{cache,marketplaces}/*/pg-plugin/*/skills/<dir>/scripts/<f>`
   (Droid).
2. **Read the queue config** (`docs/goals/index.yaml` `config:` if present) for `base`,
   `merge`, `execution`, `validation` — defaults `base` = repo default branch, `merge: pr`,
   `execution: native`, `validation: risk_based`.
3. **Run the read-only probe:** `python3 "$DC" --base <base> --merge <merge> --execution <execution> --state-branch <state_branch> --validation <validation>`
   (read `state_branch` from `config.state_branch`, default `= base`; `validation` from
   `config.validation`, default `risk_based`). It emits JSON
   `{checks:[{check,level,detail,fix}], result}` and exits 0/1/2. Never edit it.

## Apply local fixes (aggressive — these and ONLY these)

For each check whose `fix` begins with `FIX:`:

- **`merge-permission` (no allow-rule, `merge: auto`):** add the EXACT token the probe printed
  — `Bash(python3 <abs>/pg_safe_merge.py:*)` — to `permissions.allow` in
  **`.claude/settings.local.json`** (Claude Code) or **`.factory/settings.local.json`** (Droid)
  — per-machine; never the committed `.claude/settings.json` or `.factory/settings.json`.
  Trust that token VERBATIM: the probe derives the wrapper from the plugin install (the same
  path dispatch invokes), so never substitute a path of your own. The token has a `*` in place
  of the plugin version (`pg-plugin/*/skills/...`) ON PURPOSE — a deliberate wildcard so this one
  rule survives plugin updates (a version-pinned rule would re-block merges after every upgrade);
  keep the `*`, never expand it to a pinned version. An older version-pinned rule lingering from a
  previous run is harmless (you may delete it). Create the file/keys if absent; dedup; never
  delete existing entries; re-read to confirm → FIXED.
  EXPECT this write to be DENIED in an unattended or auto-mode session — the harness blocks an
  agent from adding its own `Bash(...)` allow-rule as self-modification. That denial is NOT a
  failure and you must NOT route around it: surface the exact line under needs-you (status
  `permissions: blocked(classifier)`) and offer to apply it on the user's explicit "go"; an
  interactive session's permission prompt may let it through directly. If a `deny` blocks the
  rule (`merge-permission` BLOCKER citing a deny), do NOT add an allow — report the conflict.
- **`queue` (missing index.yaml):** scaffold `docs/goals/`, `docs/goals/done/`,
  `docs/goals/archive.yaml`, and an `index.yaml` with the default `config:` block (base = the
  resolved base, `merge: pr`, `wip: 2`, `model: inherit`, `skills: []`, `execution: native`,
  `autonomy: balanced`) and an empty `goals: {}` → mark FIXED.
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
- **`state-branch` (missing, `state_branch != base`):** create the branch off `<base>` and push
  it — `git branch <state_branch> origin/<base> && git push origin <state_branch>` — then re-run
  the probe to confirm → FIXED. (Safe: it's an empty branch off base, queue-metadata only, never
  code.) If the probe reports the state branch is **protected** (BLOCKER), do NOT create or
  unprotect — report it (a protection change is remote governance, never auto-done).

Each fix is one atomic edit, named in the report.

## Never (even though you're aggressive)

Push, open a PR, touch the remote, edit a CI workflow, change branch protection / required
reviews, run `gh auth login`/`refresh` (browser-blocking — report the exact command instead),
run a SYSTEM/sudo/global install (`gh`, `git`, `brew`/`apt`, OR `npm i -g agent-browser`
+ its Chromium download — report those; the ONLY install you may run is the plugin's own
python dep at `--user` scope, above), `git stash`, change
`merge: pr` → `auto`, delete branches/worktrees, or write to user-scope
`~/.claude/settings.json` (Claude Code) or `~/.factory/settings.json` (Droid). Anything not
in the fix list above is REPORT-only.

## Report (always, last line is the status)

`fixed:` lists what you changed (one line each). `needs-you:` lists every BLOCKER/WARN the
probe reported that you did NOT auto-fix — copy its `detail` and `fix` fields verbatim; that
text IS the exact command or guidance for the human (the `gh auth refresh …` line, the "set
config.base to a state branch, or run a single dispatcher" option for a protected base, a
deny-rule conflict, etc.). A `merge-permission` BLOCKER that cites a deny has no `FIX:` prefix,
so it lands here, not in `fixed:`. The probe also checks `browser-verify`: if the repo has
frontend/UI work (a UI framework in package.json, or any goal referencing `agent-browser`)
but `agent-browser` isn't installed, it WARNs with the install command — REPORT-only (a global
npm install + Chromium is a system-level change, never auto-run). The probe also emits three
REPORT-only loop-health checks (all read-only — never auto-fixed): `validation-gate` (under
`merge: auto`, WARN if `config.validation: off` or `pg_validate.py` is unresolvable — an
auto-merge with no deterministic gate is "a loop without a check"; copy its `fix` to set
`config.validation: risk_based`), `queue-liveness` (WARN naming any `in_progress` goal with no
`goal/<id>` branch and no PR on origin — a stale claim / silent-death candidate dispatch will
respawn or that needs unblocking), and `goal-contracts` (WARN naming any active goal whose file
lacks a checkable done-condition — tighten via `/define-goal` before dispatch picks it up). Then
one status line — under `merge: pr` the probe emits `merge-permission` INFO with no fix, so
report `permissions: n/a` (and `gate: n/a`):

`[doctor] software: <ok|missing> · auth: <ok(scopes)|fix> · permissions: <ok|fixed|blocked(classifier)|deny-conflict|n/a> · push: <ok|⚠ base protected> · state-branch: <pushable|missing|⚠ protected|n/a> · ci: <green|none> · gate: <wired|⚠ off|⚠ missing|n/a> · queue: <valid|scaffolded|drift> · health: <live|⚠ stale claims|⚠ underspecified goals> · result: READY|WARN|BLOCKER`

## Relationship to the other skills

- `define-goal` runs the queue subset of these checks before creating the first `index.yaml`.
- `dispatch` Phase 0 runs the read-only probe each fire and cites `/factory-doctor` on a
  failure it can't handle; its permission-stall fix is "run `/factory-doctor`".
- This skill never claims goals, spawns implementers, or merges — that's `dispatch`.
