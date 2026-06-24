# Changelog

All notable changes to **flywheel** are recorded here. Versions match the
`version` field in `.claude-plugin/plugin.json`; each is tagged in git
(`vX.Y.Z`) and linked to its release commit on GitHub.

This file is the canonical, git-tracked source of truth for the version
history. (The public site at <https://plugin.pragmaticgrowth.com> no longer
carries a changelog section — this file is the single source.)

The format is loosely based on [Keep a Changelog](https://keepachangelog.com).

<!-- COMMIT-BASE: https://github.com/pragmaticgrowth/flywheel/commit/ -->

## [3.0.0] — 2026-06-24

**Renamed `pg-plugin` → `flywheel`.** A rebrand, not a behavior change — the
factory, the four skills, the `docs/goals` queue design, and the merge gate
are all unchanged. The name now says what it is: a self-sustaining loop that
turns plain-language wants into verified PRs.

- **Plugin name, skill namespace, and install target all change.** Skills are
  now `flywheel:<skill>` (was `pg-plugin:<skill>`), and the plugin installs as
  `flywheel@pragmatic-growth`.
- **The GitHub repo moved to `pragmaticgrowth/flywheel`** (the old
  `pragmaticgrowth/pg-plugin` path redirects, so existing links keep working).
- **Migration:** uninstall the old plugin, refresh the marketplace, and install
  under the new name — Claude Code: `/plugin uninstall pg-plugin` →
  `/plugin marketplace update pragmatic-growth` →
  `/plugin install flywheel@pragmatic-growth` (Droid: the `droid plugin …`
  equivalents). The `docs/goals/` queue in your repos is untouched.
- **Unchanged:** the `pragmatic-growth` marketplace name, and the `pg_*.py`
  helper scripts (`pg_safe_merge.py`, `pg_validate.py`) — there `pg` is the
  publisher, Pragmatic Growth, so existing merge allow-rules keep working.

## [2.10.0] — 2026-06-24

**Loop-engineering hardening** — from a 20-bookmark research audit of the
state-of-the-art "loop engineering" discipline; all 11 roadmap items shipped.

- `config.budget` — an external "burnstop" the orchestrator can't edit:
  `max_spawns_per_session` / `max_iterations` ceilings on cumulative spend
  across a scheduled run. On exhaustion dispatch stops claiming/spawning,
  lets in-flight work drain, surfaces `budget exhausted` under needs-you, and
  fires one notification.
- `GOAL_UNREACHABLE` escape hatch — an implementer can declare a goal
  genuinely unreachable, routing it to a needs-you contract amendment instead
  of respawning forever.
- Cost-per-accepted-change metric (merges ÷ spawns), a per-fire heartbeat for
  silent-death detection, and a drained-queue terminal stop.
- Subjective success criteria route to an independent grader; proof-of-output
  and irreversible-action gates added.
- factory-doctor gains read-only `validation-gate`, `queue-liveness`, and
  `goal-contracts` probes (+12 tests).

## [2.9.7] — 2026-06-24

**Safe base→main promotion.** After a real run auto-deleted the base branch,
promotion now goes through a throwaway `promote-<date>-to-<target>` head
branch so a repo's `delete_branch_on_merge: true` can't delete the persistent
base as a side effect. Audit merge side effects, and protect the base as the
robust repo-side guard.

## [2.9.6] — 2026-06-24

**Protected-main support.** `config.state_branch` (default `= base`) holds the
whole `docs/goals/` queue on a separate unprotected branch, so the factory
never has to push to a protected base — only implementer code PRs target it.
Backward-compatible: default `= base` means zero change for unprotected repos.

## [2.9.5] — 2026-06-24

**Recon-populated contracts.** define-goal auto-fills a goal's `touches:` and
`acceptance:` fields from recon findings instead of leaving them for a human.

## [2.9.4] — 2026-06-24

**LLM semantic validator (Phase 2, opt-in).** With `config.llm_validation: on`,
a single read-only adversarial validator — fed only the contract + raw diff +
checkout, never the worker's narrative — must earn a PASS with replayable
evidence. Runs only after the deterministic gate passes; the deterministic
FAIL always wins.

## [2.9.3] — 2026-06-24

**Deterministic merge gate.** Under `merge: auto`, `pg_validate.py` runs on a
fresh detached checkout before every merge: one-goal integrity, bug
repro-direction (red on base → green on head), fresh-checkout acceptance-green,
blast-radius, and a secret/forbidden-content scan — emitting a SHA-bound
`PASS | FAIL_FIXABLE | FAIL_CONTRACT | INCONCLUSIVE` verdict. The orchestrator
merges; the validator never does.

## [2.9.2] — 2026-06-23

**Progress-first report.** Dispatch's per-iteration report line leads with
`<done>/<total> done` plus a 20-cell fill bar, then labeled
ready / running / blocked counts — never `ready/total`, which reads as
"nothing done".

## [2.9.1] — 2026-06-23

**Scripted browser verification.** define-goal and factory-doctor gain a
scripted browser-verification path for UI work, so acceptance can be proven
against a running page.

## [2.9.0] — 2026-06-23

**Dual-runtime (Claude Code + Droid).** Every skill detects the runtime and
uses the correct paths, commands, and scheduling primitives (`/goal` vs
`droid exec`, `/loop` vs `CronCreate`). factory-doctor now checks settings in
both `.claude/` and `.factory/` paths.

## [2.8.7] — 2026-06-23

Hardened define-goal and dispatch for multi-machine concurrency on the shared
queue.

## [2.8.6] — 2026-06-23

factory-doctor writes a version-durable merge allow-rule (survives plugin
version bumps).

## [2.8.5] — 2026-06-23

factory-doctor's pyyaml auto-fix survives a PEP-668 externally-managed Python.

## [2.8.4] — 2026-06-23

factory-doctor auto-installs the plugin's `pyyaml` dependency.

## [2.8.3] — 2026-06-23

factory-doctor resolves the `pg_safe_merge` wrapper from the plugin install
(not repo-relative), and handles the classifier-blocked allow-rule auto-fix —
surfacing the exact line under needs-you and applying it only on the user's
explicit go, never routing around the denial.

## [2.8.2] — 2026-06-23

Recon search subagents run as `general-purpose` on `model: sonnet`, strictly
read-only — buying real understanding the haiku-locked Explore type can't.

## [2.8.1] — 2026-06-23

**Recon investigate-first by default.** Parallel read-only recon runs before
any goal that touches an existing system; "the description sounds clear" is the
failure mode it replaces. Skipped only for genuinely greenfield/one-liner wants.

## [2.8.0] — 2026-06-23

**factory-doctor + pg_safe_merge.** New factory-doctor skill: a one-pass
preflight/doctor for a repo + machine (software, gh auth + scopes, the merge
allow-rule, branch protection, CI, queue state) that auto-fixes everything
local. Pairs with `pg_safe_merge.py`, a verified-merge wrapper that re-checks
branch/body/base/CI/SHAs so the merge allow-rule stays narrow.

## [2.7.0] — 2026-06-23

**Real-run hardening** — validated against the first real 24-goal `merge: auto`
native run. Dispatch fills `min(wip, ready)` implementers
every iteration; transient infra deaths don't burn the respawn budget (which is
itself capped); the queue commit is always its own command; implementer-brief
traps closed (never `cd` to the main checkout, reproduce a bug before fixing,
stage only intended files); review loops converge.

## [2.6.1] — 2026-06-15

herdr-mode path / identity / dispatch fixes from a real run.

## [2.6.0] — 2026-06-15

**herdr execution mode (opt-in).** `config.execution: herdr` runs each
implementer as a fresh `claude` in an isolated `goal/<id>` herdr worktree pane —
parallel, observable, crash-recoverable. Default `native` keeps the in-process
path and full portability.

## [2.5.0] — 2026-06-12

**Permission-stall invariant.** A harness denial of the orchestrator's own
merge is an environment blocker, not a work failure: the goal holds its wip
slot, needs-you carries the exact allow-rule fix verbatim, and one notification
fires per distinct blocker set.

## [2.4.0] — 2026-06-12

`config.model` (inherit | sonnet | haiku) for spawned code agents, and goal
`type: bug | feature | chore` that shapes the contract — bugs lead with a
failing-test reproduction, features must bound scope, chores prove no behavior
change.

## [2.3.0] — 2026-06-12

Maintenance and documentation release.

## [2.2.0] — 2026-06-12

Maintenance and documentation release.

## [2.1.0] — 2026-06-12

Parallel-factory documentation: how multiple sessions safely work one queue.

## [2.0.0] — 2026-06-12

**Three-skill lineup + the docs/goals pipeline.** Retired the `wish` skill; the
`docs/goals/` file queue replaces GitHub issues as the work queue (no issue-body
size caps, no per-repo label bootstrap, versioned with the code).

## [1.1.0] — 2026-06-10

Added the **define-goal** skill (initially ported from `openai/skills`, then
adapted to Claude Code / Droid primitives).

## [1.0.1] — 2026-06-10

Replaced stale-model calibrations with outcome-based contracts in the (then
still present) `wish` skill.

## [1.0.0] — 2026-06-10

**Skills-only plugin.** Transformed `mcp-do` into a skills-only plugin
(named `pg-plugin` at the time; renamed `flywheel` in 3.0.0): removed the
stdio MCP server entirely.

## 0.x — 2026-04-13 → 2026-04-23 (mcp-do era)

Pre-history. A stdio MCP server wrapping the `droid` / `opencode` CLIs —
started as the `do` plugin, renamed to `mcp-do`, with the `pragmatic-growth`
marketplace created along the way. Removed in 1.0.0; preserved in git history.

[2.10.0]: https://github.com/pragmaticgrowth/flywheel/commit/31e3d1f
[2.9.7]: https://github.com/pragmaticgrowth/flywheel/commit/6fafc3c
[2.9.6]: https://github.com/pragmaticgrowth/flywheel/commit/4e335e7
[2.9.5]: https://github.com/pragmaticgrowth/flywheel/commit/ad5ff75
[2.9.4]: https://github.com/pragmaticgrowth/flywheel/commit/18a0016
[2.9.3]: https://github.com/pragmaticgrowth/flywheel/commit/b574407
[2.9.2]: https://github.com/pragmaticgrowth/flywheel/commit/a67c564
[2.9.1]: https://github.com/pragmaticgrowth/flywheel/commit/c83272f
[2.9.0]: https://github.com/pragmaticgrowth/flywheel/commit/d11bd7a
[2.8.7]: https://github.com/pragmaticgrowth/flywheel/commit/dbbb489
[2.8.6]: https://github.com/pragmaticgrowth/flywheel/commit/8bcfec5
[2.8.5]: https://github.com/pragmaticgrowth/flywheel/commit/88bd7d5
[2.8.4]: https://github.com/pragmaticgrowth/flywheel/commit/2705e68
[2.8.3]: https://github.com/pragmaticgrowth/flywheel/commit/a6b0bdb
[2.8.2]: https://github.com/pragmaticgrowth/flywheel/commit/7ed4432
[2.8.1]: https://github.com/pragmaticgrowth/flywheel/commit/b06b586
[2.8.0]: https://github.com/pragmaticgrowth/flywheel/commit/27b1f3b
[2.7.0]: https://github.com/pragmaticgrowth/flywheel/commit/9149a8d
[2.6.1]: https://github.com/pragmaticgrowth/flywheel/commit/e109a77
[2.6.0]: https://github.com/pragmaticgrowth/flywheel/commit/790c18b
[2.5.0]: https://github.com/pragmaticgrowth/flywheel/commit/ec371bd
[2.4.0]: https://github.com/pragmaticgrowth/flywheel/commit/aabf39c
[2.3.0]: https://github.com/pragmaticgrowth/flywheel/commit/167475b
[2.2.0]: https://github.com/pragmaticgrowth/flywheel/commit/a204fcc
[2.1.0]: https://github.com/pragmaticgrowth/flywheel/commit/2bb5d1a
[2.0.0]: https://github.com/pragmaticgrowth/flywheel/commit/c3e8b34
[1.1.0]: https://github.com/pragmaticgrowth/flywheel/commit/c4a0f55
[1.0.1]: https://github.com/pragmaticgrowth/flywheel/commit/14c5d52
[1.0.0]: https://github.com/pragmaticgrowth/flywheel/commit/cc839f5
