# Changelog

All notable changes to the **pragmatic-growth** marketplace in this repo are
recorded here. The primary release version matches the `flywheel` plugin's
`version` field in `.claude-plugin/plugin.json`; each is tagged in git
(`vX.Y.Z`) and linked to its release commit on GitHub.

This file is the canonical, git-tracked source of truth for the version
history. (The public site at <https://plugin.pragmaticgrowth.com> no longer
carries a changelog section — this file is the single source.)

The format is loosely based on [Keep a Changelog](https://keepachangelog.com).

<!-- COMMIT-BASE: https://github.com/pragmaticgrowth/flywheel/commit/ -->

## [5.0.2] — 2026-07-13

**dispatch: gate robustness pass — PyYAML-primary frontmatter parsing, a
package-manager-aware fallback, and failure evidence that names the command.**
Follow-up hardening after the v5.0.1 parser fix, closing the rest of that bug
class instead of waiting for the next YAML shape to false-fail a goal:

- **PyYAML is now the primary frontmatter parser.** `_parse_goal` uses
  `yaml.safe_load` when PyYAML is importable (the factory already requires it —
  factory-doctor BLOCKERs on it missing), so every YAML shape and escape is
  read correctly — e.g. a double-quoted `"…\\.render…"` acceptance pattern now
  decodes to the `\.` the author meant. The hand parser remains as the fallback
  for stdlib-only environments and unparseable frontmatter, and now also
  decodes `\"`/`\\` in double-quoted flow elements and `''` in single-quoted
  ones. Verified: primary and fallback parse **byte-identical** results on all
  real goal files of the repo that hit the v5.0.1 bug.
- **`detect_gate_command` no longer guesses wrong.** The no-`acceptance:`
  fallback now (a) requires a real `test:` target before picking `make test`,
  (b) JSON-parses `package.json` and rejects the npm-init `"no test specified"`
  placeholder plus `"test"` strings that aren't a script, and (c) names the
  package manager from the lockfile — `pnpm test` / `yarn test` / `bun test`
  instead of a blind `npm test` that fails at any pnpm/yarn workspace root.
- **Red evidence names the command.** `acceptance-green` and `repro-direction`
  failures now report `[i] <command> (exit N)` instead of a bare index, so an
  operator (or the repair loop) sees what actually failed without digging.
- 13 new tests (98 total green, plus the `--self-test` pure sweep at 90).

## [5.0.1] — 2026-07-13

**dispatch: the local gate now parses multi-line YAML flow arrays in goal
frontmatter.** `pg_validate.py`'s stdlib goal-file parser understood only two
of the three YAML list shapes — inline flow (`acceptance: ["a", "b"]`) and
block sequences (`- "a"` lines). Goal files whose `acceptance:`/`touches:`
arrays a formatter had reflowed into the third shape (`[` on its own line, one
quoted element per line, closing `]`) silently parsed as **empty**, so the gate
fell back to a generic `npm test` and false-failed every goal in such repos
(caught live in a real dispatch run: a fully green implementation gated
`FAIL_FIXABLE` while all declared acceptance commands passed). Fixes:

- **Multi-line flow arrays parse.** `_parse_goal` now accepts `[` opening on
  the key line or its own line, elements across lines (with or without trailing
  commas), YAML comments between elements, and the closing `]` — for both
  `acceptance:` and `touches:`.
- **Quote-aware splitting.** Flow elements are split on commas *outside*
  quotes, so a command like `python -c 'print(1, 2)'` stays one command.
- **Balanced unquoting.** Items lose one matched pair of surrounding quotes
  instead of the old greedy character strip, which mangled commands ending in
  a quote (`pnpm test -- --testPathPatterns '(a|b)'` lost its final `'`).
- **Empty inline `[]` now yields `[]`**, not a latent one-empty-string list.
- Eight new parser tests lock all three shapes plus the comma/quote edge cases
  (85 total, plus the `--self-test` pure sweep).

## [5.0.0] — 2026-07-11

**Droid removed — the marketplace is now Claude Code only.** A whole-repo sweep
stripped every Droid / Factory-CLI code path and dual-CLI framing across all
four plugins, their scripts, the manifests, the README, and the public site, so
`flywheel`, `html-artifacts`, `autoresearch`, and `human-writing` target Claude
Code exclusively. How goals are worked on Claude Code is unchanged — dispatch,
the local gate, and the queue behave identically; only the Droid-specific
surfaces are gone. Major bump because a supported runtime is dropped. Changes:

- **Skills.** All five flywheel skills lose their `CLI detection` blocks and
  dual-CLI branches: `define-goal` (no `droid exec` run-now line, no Droid
  self-verification, CLAUDE.md-only repo grounding), `dispatch` (no
  `config.droid_models` resolution, no Droid PushNotification / `.factory`
  fallbacks), `factory-doctor` (the entire `droid-models` interview and the
  `.claude/`+`.factory/` dual-path prose gone), `loop-architect` (the 3-column
  primitive table collapses to Claude Code only; no `CronCreate`, Droid
  Computers, or Factory app), and `telegram-message` (the Droid "dispatch pings
  only" section gone). `autoresearch` and `html-artifacts`/`human-writing` lose
  their stray Droid refs too.
- **`config.droid_models` removed.** The alias→Droid-model map and
  factory-doctor's owner interview (added in 4.16.0) are deleted. A goal's
  implementer model resolves `goal model:` > `config.model` > `inherit`, full
  stop.
- **`doctor_checks.py`.** Dropped the `--runtime claude|droid` flag,
  `droid_models_check` (plus its six tests and the now-dead `ANTHROPIC_ALIASES`
  / `_frontmatter_model` helpers), the `.factory/` settings probing, the
  `droid exec` scheduler pattern, and the Droid clause in the limit-resilience
  fix. The doctor's status line drops its `models:` field. 38 tests pass and
  the probe emits valid JSON with no `droid-models` check.
- **Manifests + version bumps.** Root `flywheel` 4.16.0 → **5.0.0** (drops the
  `factory`/`droid` keywords and the "and Droid" descriptions);
  `autoresearch` 1.0.1 → **1.1.0** (its `CronCreate` cadence branch removed);
  `html-artifacts` 1.0.0 → **1.0.1** and `human-writing` 1.0.0 → **1.0.1**
  (stray-ref doc edits). `marketplace.json` and `hooks/hooks.json` drop their
  Droid text.
- **Docs + site.** README loses the Droid install block, the CLIs badge, and
  the "Works in both CLIs" section; the public site drops the Droid install tab
  (the tab UI collapses to a single install block), the `droid_models` config
  example, and the "2 CLIs" hero stat. `AGENTS.md` (the symlink to CLAUDE.md, a
  Droid/Codex convention) is removed along with the alignment rule. The
  "Adapted from Factory's … plugin (MIT)" attribution lines are purged (owner
  decision; the repo's own MIT `LICENSE` is unchanged).
- **History intact.** Prior CHANGELOG entries and `docs/superpowers/**` design
  artifacts are left untouched — they record what shipped.

## [4.16.0] — 2026-07-09

**Droid coverage audit — every Factory-CLI claim verified against the current
docs and a live Droid 0.168.2, plus owner-decided Droid model mapping.** A
full sweep (Factory docs deep-read + repo claim inventory + empirical
`droid exec --list-tools` / `--help` / `droid plugin marketplace list` checks)
confirmed the big claims — `CronCreate`/`CreateAutomation`/`Task`/`Skill` are
real session tools despite docs silence, the GitHub marketplace registers as
`flywheel` so every `X@flywheel` install command stands, there is no
PushNotification tool, and Droid's hook event set has no `StopFailure` — and
caught four stale ones. Changes:

- **Droid model mapping — `config.droid_models` + a factory-doctor interview
  (owner decision 2026-07-09).** Droid has no `opus|sonnet|haiku` alias
  namespace and an owner can run many custom models (`custom:<name>`), so
  stamped aliases silently downgraded to `inherit` on Droid. Now the queue can
  carry an owner-authored map: the probe gains a `droid-models` check (new
  `--runtime claude|droid` flag; WARN on Droid when an alias in use —
  `config.model` or a goal's frontmatter — has no mapping, INFO-only in
  Claude Code) and the doctor ASKS which concrete Droid model each alias
  means — presenting the real choices from `droid exec --help` (built-ins
  plus the owner's `custom:` entries), never guessing — then writes
  `config.droid_models` in one atomic edit. dispatch resolves aliases through
  the map and passes the mapped ID to code-writing spawns (absent/rejected →
  `inherit`, noted in the report line); define-goal documents that a stamped
  alias is honored on Droid via the map. The doctor status line gains
  `models: <mapped|⚠ unmapped|n/a>`. +8 probe tests (46 total).
- **define-goal:** dropped the stale claim that headless Droid accepts only
  built-in model IDs — `droid exec -m custom:<name>` is officially supported;
  model-ID examples refreshed. Removed "AskUser in Droid" at its three sites:
  Droid exposes no question tool at any autonomy level (verified via
  `--list-tools`) — ask directly in chat.
- **autoresearch 1.0.1:** `/enter-mission` doesn't exist — missions are
  `droid exec --mission` headless, or the ProposeMission/StartMissionRun
  tools in an interactive session.
- **loop-architect:** project hook location corrected to
  `.factory/hooks.json` (was `.factory/hooks/hooks.json`; user-level is
  `~/.factory/hooks.json`).
- **hooks/hooks.json** description no longer claims Notification/SessionEnd
  "work on both CLIs": events are Claude Code-verified, and unattended Droid
  runs get their pings from dispatch's hook-free `dispatch` category.

## [4.15.0] — 2026-07-09

**Per-goal implementer model — goal contracts carry their own `model:`, so an
expensive orchestrator drives cheap implementers on well-specified goals.**
Motivated by a real romy-repo session (astro-website-and-shadcn-ui): with 11
tightly-contracted goals queued, the only routing knob was the repo-wide
`config.model` toggle, which the owner would have had to flip back and forth
between goals to give the two judgment-heavy goals a stronger implementer than
the nine mechanical ones. Now the routing lives in the contract itself:

- **define-goal** stamps a frontmatter `model:` (`inherit | opus | sonnet |
  haiku`) on every queued goal — decided LAST, after the acceptance criteria
  are final, via a new "Implementer model — decide it last" rubric: a tight,
  objectively-checkable contract defaults to `sonnet` (the judgment was
  front-loaded into the contract); flagship design craft, wide blast radius,
  ambiguous root-cause, or security/data-loss-adjacent work gets `opus`;
  `inherit` matches the session model; unsure between tiers → the stronger.
  Batch mode's approval table gains a `model` column.
- **dispatch** resolves each spawn as goal `model:` > `config.model` >
  `inherit` and passes the result to the implementer AND any repair agent;
  the orchestrator's own claim/gate/review judgment stays on the session
  model, and recon/review read-only agents keep inheriting it too. In Droid
  (no Anthropic alias namespace) an unmappable alias resolves to `inherit`.
- `config.model` is now documented as the repo-wide DEFAULT (and accepts
  `opus`); goal files without `model:` behave exactly as before — fully
  backward compatible, and `pg_validate.py` ignores the new key by design.

**Patch: Windows `type: bug` goals are gateable — workspace-aware dep links,
actionable INCONCLUSIVE, and a junction-traversal data-loss guard.** Follow-up
field report from the same Windows user: with the shell fixed (4.14.1),
chore/feature goals gated fine but every bug goal returned INCONCLUSIVE.
Root cause was two-layered: (1) `os.symlink` needs
`SeCreateSymbolicLinkPrivilege` (Developer Mode or elevation — off on a stock
box), and the gate's `except OSError: pass` silently swallowed WinError 1314,
leaving the repro-direction base worktree dep-less; (2) even with symlinks
available, only top-level `DEP_DIRS` were linked — pnpm/yarn/npm-workspace
packages resolve runner bins from their OWN `node_modules/.bin`, so `jest`
stayed unresolvable. Fixes: link failures are now RECORDED and, when a base
run is red, the gate returns an INCONCLUSIVE whose evidence names the cause
and the operator fix (enable Developer Mode / run elevated) — this also closes
a latent FALSE-PASS on the direct-probe path (no overlaid test → no bare-base
control), where a dep-less base red could previously be mistaken for a bug
reproduction; `_dep_link_pairs` now links per-workspace-package
`node_modules` (`*/node_modules`, `*/*/node_modules`) alongside the root dep
dirs. Cleanup is hardened per the reporter's data-loss warning (a naive
junction fallback destroyed 41 tracked files in his checkout — recursive
deletes traverse live dir links into real workspace sources): links are
removed link-only (`unlink` then `rmdir` for Windows dir symlinks) BEFORE
`git worktree remove --force`, and if any link survives, the worktree remove
is SKIPPED (rmtree handles links safely; the stale registration is pruned).
Junctions are explicitly rejected in code comments. factory-doctor gains a
Windows-only `symlink-privilege` WARN with the Developer Mode fix text;
dispatch SKILL.md documents the Windows requirement and now requires the
gate's `evidence` to reach INCONCLUSIVE block reasons. +5 gate tests
(78 total), +3 doctor tests (38 total).

## [4.14.1] — 2026-07-08

**Patch: the dispatch gate works on Windows — bash resolves by full path, and
acceptance runs are time-bounded.** First Windows field report: on any machine
with the WSL optional feature enabled, `pg_validate.py`'s
`subprocess.run(["bash", "-lc", …])` let CreateProcess resolve the bare name
through System32 BEFORE PATH, hitting the distro-less WSL launcher stub
(`System32\bash.exe`) instead of Git Bash — every acceptance command exited 1
(`execvpe(/bin/bash) failed`) and every goal false-FAILed `FAIL_FIXABLE` even
with the suite fully green. The gate now resolves its POSIX shell to a FULL
path once per run: `PG_BASH` env override → `which(bash)` → `which(sh)` (both
rejected when they live under `%SystemRoot%`) → standard Git-for-Windows
install locations built from `ProgramFiles`/`ProgramW6432`/
`ProgramFiles(x86)`/`LocalAppData` env vars → platform default shell
(`shell=True`) as the last resort, so no machine-specific path is ever
hardcoded. Acceptance commands also gain a bounded timeout (default 1800 s,
`PG_VALIDATE_TIMEOUT` override; expiry reds the command as exit 124), so a
hung test suite reds the gate instead of locking it forever. +8 tests
(73 total), including cross-platform simulations of the exact WSL-stub
shadowing reported.

## [4.14.0] — 2026-07-08

**Minor: hook pings are dispatch-gated — interactive sessions stop flooding
the chat.** A real day of parallel interactive sessions produced a stream of
idle/permission/error DMs with zero dispatch relevance (transcript forensics:
8 of 8 hook pings that day came from ordinary interactive work; the one useful
ping was a dispatch report). The notifier now gates its three hook categories
on per-repo dispatch context, read from `~/.local/state/pg-dispatch/<slug>/`:
`waiting` requires a LIVE fire — the new `active` marker dispatch writes as
the first act of every fire and removes as the last — so loop sessions idling
between fires, elicitation dialogs, and teammate blips in ordinary work never
ping; `errors`/`completions` accept the marker OR a heartbeat younger than
4 h, so a wakeup turn dying to a usage limit before its fire starts still
pings and the run-ended ping still lands after the last fire cleaned up. The
`dispatch` report category is never gated. Default ON with no config change
(existing configs gain the gate on refresh); `"gate_on_dispatch": false` per
scope restores fire-always hooks, and the env-var cloud scope stays ungated
(`PG_TELEGRAM_EVENTS` is its narrowing knob). dispatch SKILL.md gains the
fire-marker write/cleanup; the gate is per-repo, not per-session (skills
can't see their session id) — documented in the skill. +11 notifier tests
(47 total).

## [4.13.0] — 2026-07-07

**Minor: telegram-message identifies the SESSION, drops timestamp noise.**
Several sessions on one project were indistinguishable in the chat. Message
headlines are now `<emoji> <project> · <session> · <event>`, where the session
label is the session's name — a `/rename` or Claude Code's derived name,
resolved by `session_id` from the live-session registry at
`~/.claude/sessions/<pid>.json` — falling back to the session id's first
8 chars. Dispatch pings (plaintext pipe, no session id) keep the plain
`<project> · dispatch` headline. Completion messages also stop echoing the
heartbeat's UTC timestamp — Telegram already shows arrival time. Registry
lookup is best-effort and never-crash like the rest of the notifier; +6 tests
(36 total).

## [4.12.1] — 2026-07-07

**Patch: notification messages lead with the PROJECT name.** With several
projects feeding one Telegram chat, the project must be the headline, not a
`repo:` footnote — and the old `flywheel ·` prefix on line 1 was brand noise
(ambiguous for this very repo). Every category now formats as
`<emoji> <project> · <event>` on the first line (`🛑 myapp · turn failed`,
`🔔 myapp · needs you`, `✅ myapp · run ended`, `🏭 myapp · dispatch`), body
below, `repo:` line dropped. The skill's setup test message follows the same
rule. Tests updated to pin the first-line contract (30 passing).

## [4.12.0] — 2026-07-07

**Minor: telegram-message goes project-scoped, and Droid + cloud get pings.**
Telegram credentials are personal settings, so setup is now **per-project by
default and always stored OUTSIDE the repo** — structurally impossible to
commit or push, whatever scope the plugin is installed at. And the deferred
Droid path shipped: dispatch pings directly, hook-free.

- **Project scope (new default):** `/telegram-message <token> [chat_id]` writes
  `~/.local/state/pg-telegram/projects/<slug>.json` (chmod 600) carrying
  `project_root`; the notifier resolves by longest-`project_root`-prefix match
  on the event's `cwd`. Different repos → different bots/chats/toggles;
  `"enabled": false` in a project file silences ONLY that project (explicit
  opt-out, no fallthrough). `--global` writes the machine-wide fallback
  (the v4.11 config, still honored).
- **Cloud/env scope:** `PG_TELEGRAM_BOT_TOKEN` + `PG_TELEGRAM_CHAT_ID` env vars
  beat both files — for routines/automations where `~/.local/state` doesn't
  persist; narrow categories with `PG_TELEGRAM_EVENTS=errors,dispatch`.
  Resolution chain: explicit override → env → project → global.
- **New `dispatch` category — the hook-free path that covers Droid and cloud:**
  dispatch Phase 4 now pipes its report line to the notifier every fire
  (`printf '%s' "<report>" | python3 "$PGNOTIFY" dispatch`; non-JSON stdin is
  treated as the report text, so no quoting hazards). Works in both CLIs and
  cloud because it's a plain script call — on Droid, where hooks don't fire
  under `droid exec` (v4.11 finding), this IS the notification path. The skill
  now sets up on Droid too, with plain expectations: dispatch pings only there.
  Configs written by v4.11.0 lack the `dispatch` toggle — re-run setup or add
  `"dispatch": true` to `events` to enable it.
- Notifier: +9 tests (precedence, longest-prefix, opt-out, env override,
  dispatch compose/toggle/plaintext stdin) → 30 total, still pure stdlib and
  never-crash. README/site/CLAUDE.md updated (incl. correcting the stale
  "skills-only / no hooks / four skills" intro copy v4.11.0 had missed).

Dry-run tested on 8 scenario questions with cited answers; zero ambiguities.
Skill change:
[`13d6ac5`](https://github.com/pragmaticgrowth/flywheel/commit/13d6ac5).

## [4.11.0] — 2026-07-07

**Minor: new `telegram-message` skill — get a Telegram DM when an autonomous run
needs you.** Wires a bot to ping the owner the moment a `/dispatch` or `/loop`
run hits an error/usage limit, waits on a permission prompt, or finishes —
closing the "I didn't know it stalled until morning" gap that the v4.10
usage-limit work made survivable but not *observable*. This is flywheel's first
hook bundle: an explicit owner decision that ends the former "skills-only"
invariant (now "skills-first" — hooks need the same explicit ask, must no-op
safely, and must never disrupt a session).

- **New skill `telegram-message`:** `/telegram-message <bot_token> [chat_id]`
  validates the token (`getMe`), helps find the chat id (`getUpdates`), writes a
  **chmod-600 config at `~/.local/state/pg-telegram/config.json` — the bot token
  never enters the repo, `hooks.json`, or any tracked file** — and sends a test
  message. Verbs: `off`/`on`/`test`/`status`.
- **`hooks/hooks.json`** (ships dormant, no-ops until set up): `StopFailure` →
  error/usage-limit pings, `Notification` → agent-waiting (permission/idle),
  `SessionEnd` → run finished. Auto-registers when the plugin is enabled via
  `${CLAUDE_PLUGIN_ROOT}`; no user settings edit.
- **`scripts/pg_telegram_notify.py`** — pure-stdlib notifier (no pip deps), 21
  tests. Never crashes a session (every path exits 0), no-ops when unconfigured,
  8s network timeout, token redacted in logs, best-effort enrichment of
  completion pings with the newest dispatch heartbeat line.
- **Verified end to end on Claude Code**, including a live `claude -p` run:
  `StopFailure` (forced via a bogus model) and `SessionEnd` both fire in headless
  mode — so an unattended external-scheduler drain (loop-architect Step 5) pings
  on the exact usage-limit stop v4.10 made survivable.
- **Claude Code only; Droid deferred (honest, not silent).** Empirically settled
  2026-07-07 (Droid 0.164.1): Droid has no error-hook event AND its hooks don't
  fire under `droid exec`/`CronCreate` (tested `SessionStart`/`Stop`/`SessionEnd`
  echo hooks at both project and user scope — none fired). The skill detects
  Droid and says so rather than writing config that can't fire; a hook-free
  dispatch-Phase-4 notify is the deferred Droid path. Design +
  finding recorded in
  `docs/superpowers/specs/2026-07-07-telegram-message-design.md`.

Dry-run tested on 8 scenario questions with cited answers; both flagged
ambiguities closed before shipping. Skill change:
[`4545084`](https://github.com/pragmaticgrowth/flywheel/commit/4545084).

## [4.10.0] — 2026-07-07

**Minor: the factory now survives account usage-limit stops.** A subscription
usage limit (the 5-hour rolling window, or the weekly window) blocks every
turn until reset: an in-session `/loop /dispatch` silently dies, no Claude
Code hook fires on the limit banner (source-verified on CLI 2.1.202 —
SessionEnd/Notification carry no limit event; `StopFailure` with the
`rate_limit` matcher is the one informational signal), and the CLI ships no
wait-until-reset auto-resume. Before this release a quota pause was
indistinguishable from a dead implementer, so dispatch's cross-fire brake
would wrongly block a healthy goal as `repeated transient death`.

- **loop-architect:** new primitive-table row + Step 5 "Usage-limit proofing"
  rail. The limit-proof shape is an OS scheduler (cron/launchd) firing fresh
  `claude -p "/dispatch"` sessions (Droid: `CronCreate new_session` already
  is this shape); an optional refinement reads the reset clock from the
  statusline `rate_limits.five_hour/seven_day.resets_at` epoch fields or a
  `StopFailure` (rate_limit) hook marker, and stands down until a weekly
  reset instead of retrying hourly. Step 4 notes the heartbeat alone cannot
  tell a limit pause from silent death.
- **dispatch:** the cross-fire brake is now measured in FIRES OBSERVED, never
  wall-clock — it counts heartbeat lines after the stale claim's date and
  blocks only at ≥3 fires with zero work commits; an old-but-untried claim
  (a quota/outage gap) resumes. The Phase 4 heartbeat becomes an append log
  (newest ~50 lines) so any fresh fire can count attempts; wall-clock age
  survives only as the fallback when no heartbeat log exists.
- **factory-doctor:** new read-only `limit-resilience` probe in
  `doctor_checks.py` (+5 tests, 35 total): WARNs when a dispatch loop
  demonstrably fires on the repo (heartbeat lines exist) but neither an
  external scheduler (crontab / LaunchAgents / systemd user timers referencing
  `claude -p`, `droid exec`, or `/dispatch`) nor a configured `StopFailure`
  hook is present; INFO otherwise. Status line `health:` gains
  `⚠ limit-exposed`.

Dry-run tested on 11 scenario questions with cited answers; all three flagged
ambiguities closed before shipping. Skill change:
[`cd06faa`](https://github.com/pragmaticgrowth/flywheel/commit/cd06faa).

## [4.9.0] — 2026-07-07

**Minor: dispatch's local gate now verifies review evidence** — closing the
one gap a transcript-forensics audit of every real dispatch run found. The
Jul-1 brief hardening took implementer nesting from 0/7 to ~100%, but
compliance stayed prompt-enforced: one audited goal ran its explores, skipped
its review lenses, and still gate-PASSED. The gate now checks, and self-heals.

- **dispatch:** the implementer's Finish report must end with a labeled
  `Fresh-check:` block — the lens verdicts when the fresh-window panel
  applied, or the literal `Fresh-check: not required (one-file mechanical
  edit)` line when it didn't. Working-a-goal step 3 opens with a
  review-evidence check before the gate commands: a missing block, or a
  not-required claim on plainly multi-file work, makes the orchestrator spawn
  the 2–3 read-only lenses itself over `gate_base..HEAD` (fresh windows,
  concurrent; findings are hypotheses to verify). Verified Critical/Important
  findings enter the existing `FAIL_FIXABLE` repair path; the miss itself
  never blocks a goal. Recurring misses surface once via Hygiene's
  lesson-encoding rule (session memory only — no persisted counter, per
  status-only-in-index). Dry-run tested on 7 scenarios with cited answers;
  all flagged ambiguities closed before shipping. Skill change:
  [`210703b`](https://github.com/pragmaticgrowth/flywheel/commit/210703b).

## [4.8.0] — 2026-07-07

**Minor: alignment pass with Anthropic's official loops guidance** — the
"Getting started with loops" article (Claude Devs, 2026-07-06) and the current
`/goal` / scheduled-tasks / routines / workflows / agent-teams docs pages. The
official taxonomy and token guidance map cleanly onto the v4 model (no
architectural changes); this release closes the drift a docs-vs-skills diff
found. Scenario-tested before/after: a baseline subagent run documented the
gaps, a fresh run with citations confirmed the fixes, and every flagged
ambiguity was closed.

- **define-goal:** the emitted Goal contract now ends with a mandatory turn cap
  (`Stop after <N> turns`, sized S≈10 / M≈20 / L≈30) — official guidance bounds
  every `/goal` with a turn or time clause. Enforcement is per-destination
  (run-now: the evaluator; queue: implementer self-enforced, backed by
  dispatch's brakes), and a cap-out reports as a budget stop ("turn cap
  reached"), distinct from a GOAL_UNREACHABLE contract defect. "Goal command
  facts" now documents the evaluator precisely (the configured small-fast
  model, default Haiku), the `/goal` no-argument status readout (turns, token
  spend, latest evaluator reason), and availability (`/goal` is a
  session-scoped Stop hook — needs a trusted workspace with hooks enabled;
  `disableAllHooks` blocks it).
- **loop-architect:** Step 2 maps the official four-loop taxonomy (turn-based /
  goal-based / time-based / proactive) onto the primitive table — a "proactive
  loop" ask routes to the queue/routine rows, not just channels; workflows,
  agent teams, and Stop hooks are called out as building blocks, not loop
  types — and adds an agent-teams row (collaborating peers that message each
  other; never a factory lane). Evaluator naming fixed ("Haiku evaluator" →
  configured small-fast model, default Haiku). New guidance: pair `/goal` with
  auto mode for unattended runs (per-tool vs per-turn prompts); match `/loop`
  intervals to the watched system's change rate (Monitor-tool alternative;
  project `loop.md` beats user); routines management (`/schedule
  list|update|run`, 1-hour minimum cadence, web-only API/GitHub triggers);
  Step 4 names the built-in usage surfaces (`/usage`, `/goal` status,
  `/workflows`); Step 5 adds pilot-on-a-smaller-slice before large workflow
  runs.
- **dispatch:** the parallel-implementer ban now names agent-team teammates
  explicitly (intro + implementer brief); new Hygiene rule **encode recurring
  lessons** — a gate-failure class recurring across goals is a system defect:
  propose (one needs-you line) encoding it into `config.verify` /
  `config.skills` / CLAUDE.md instead of re-fixing per goal; the
  orchestrator-level no-progress rule is marked distinct from the
  implementer's ~3-honest-attempts rule.
- **Site/README:** one-line note that flywheel implements the official
  guidance's "proactive loops" composition. Skills commit:
  [`da15b6a`](https://github.com/pragmaticgrowth/flywheel/commit/da15b6a).

## [4.7.0] — 2026-07-02

**Patch/minor: end-to-end audit of the goal + autonomous-dispatch pipeline —
gate correctness fixes and robustness hardening.** A multi-agent audit (finders
per subsystem + adversarial verification) surfaced 13 verified findings across
`define-goal`, `dispatch`, `pg_validate.py`, `loop-architect`, `factory-doctor`,
and the docs; all confirmed ones are fixed here. No new machinery — the changes
tighten existing checks and remove retired v3 vocabulary.

#### Local gate (`pg_validate.py`) — correctness

- **Fixed a false PASS on unproven bug fixes.** `already_correct` was a naive
  full-text substring scan of the immutable goal body, so any prose containing
  "already correct" (even negated, "was *not* already correct") flipped a bug
  fix that reproduced nothing into a PASS. It now reads an explicit
  `already_correct: true` frontmatter KEY only.
- **Fixed correct TDD goals being blocked.** `blast_radius` now exempts test
  paths (`tests/`, `__tests__/`, `*_test.go`, `*.test.ts`, …) from the
  out-of-scope check, so a proving test added in a split-tree layout no longer
  trips scope validation when `touches:` names product surfaces. Test paths are
  still bound by the forbidden-path and lockfile checks.
- **Retired dead v3 checks.** `one_goal_integrity` (which asserted `goal/<id>`
  branch names, PR-body markers, and PR base — all removed in v4.0.0) is replaced
  by `queue_untouched`, the one check meaningful on a local diff. Removes the
  synthesized fake-PR inputs and misleading vocabulary a maintainer could mistake
  for "dispatch still opens PRs".

#### Dispatch — robustness

- **Cross-fire transient-death brake.** The `~3 respawns per session` cap reset
  every `/loop` fire; a chronically-dying goal could livelock forever. Added a
  session-independent age brake (claim-commit age vs loop cadence) that blocks
  `repeated transient death` — no new persisted counter.
- **Single-`in_progress` data-loss guard.** Phase 1 now stops (surfaces
  needs-you) if it finds more than one `in_progress` claim, instead of
  `git reset --hard`-ing an older claim's `gate_base` and silently rewinding a
  newer claim's committed work on the linear branch.
- **Report reconciliation.** A residual `in_progress` entry now counts into
  `blocked` so `done + ready + blocked` always equals `total`.

#### define-goal, loop-architect, factory-doctor, docs

- **define-goal:** ID reservation is now LOCAL (push optional/backup-only) to
  match the v4 claim model — no longer breaks on repos with no remote;
  documented the `already_correct` frontmatter key; scoped `acceptance:` to the
  headless-runnable subset (dev-server browser checks stay in the human-visible
  criteria, not the gate); noted the gate auto-exempts test paths from `touches:`.
- **loop-architect:** replaced "merged PR" / "merge ledger" health-metric
  vocabulary with the no-PR v4 "gate-passed completed goal" / "completion ledger".
- **factory-doctor:** `working_branch_check` had inverted semantics — it WARNed
  on the healthy state (on `config.base`) and stayed silent on the dangerous one.
  Now WARNs when off an explicit `config.base` (mirroring dispatch's hard-STOP),
  INFO when on it; status-line token `⚠ on-base` → `⚠ off-base`.
- **Test hygiene:** the stale `test_public_docs_advertise_two_plugins` root test
  (asserted "two plugin" while the repo ships four) now derives the expected
  count from the marketplace manifest so it self-updates; README documents the
  gate's `INCONCLUSIVE` verdict (setup gap → `/factory-doctor`).

## [4.6.0] — 2026-07-01

**Minor: two new marketplace plugins — `autoresearch` 1.0.0 and `human-writing`
1.0.0**, bringing the `pragmatic-growth` marketplace to four plugins alongside
`flywheel` and `html-artifacts`. Both are adapted from Factory plugins and
translated to be Claude-Code-first while staying CLI-aware, matching the
conventions of the existing plugins.

#### `autoresearch` 1.0.0 — autonomous optimization loop

- **What it does.** Given a measurable metric, a benchmark command, files in
  scope, constraints, and a termination condition, it works an
  `autoresearch/<goal>-<date>` branch: try one hypothesis → run the benchmark →
  keep the change if the primary metric improves and `git`-revert it if not →
  journal what was learned (ASI) → repeat. **MAD-based confidence scoring**
  separates real gains from benchmark noise. On termination it groups the kept
  experiments into independently-mergeable branches for review; the raw
  experiment branch is always preserved.
- **File-based, resumable.** All state lives in the target repo
  (`autoresearch.md` living doc, `autoresearch.sh` benchmark emitting
  `METRIC name=value`, append-only `autoresearch.jsonl`, optional `.checks.sh` /
  `.ideas.md`), so a fresh session with no memory reads them and continues
  exactly where the last one stopped. Ships one stdlib-only helper,
  `scripts/autoresearch_helper.py` (`init`/`log`/`evaluate`/`summary`/`status`).
- **Translated to Claude Code, still CLI-aware.** `.claude-plugin` manifest; the
  helper is resolved via `$CLAUDE_PLUGIN_ROOT`/`$DROID_PLUGIN_ROOT` with a
  cache-glob fallback (the house convention) instead of the source's
  cwd-relative call; the Factory mission-mode spine is replaced with `/loop`
  (Claude Code) or same-session `CronCreate` (Droid) for unattended cadence,
  with an optional Droid-mission note; finalization detects the repo's default
  branch instead of hardcoding `main`; context wording is session-neutral. A
  dry-run review then hardened the port: robust base-branch resolution with a
  guard, and clean `log` snippets (the upstream's mid-command `# --metrics`
  comment had orphaned the trailing `--direction`).
- Adapted from Factory's `autoresearch` plugin (MIT).

#### `human-writing` 1.0.0 — AI-writing cleanup

- **What it does.** Edits AI-sounding text into human prose: scans for the tells
  catalogued in Wikipedia's "Signs of AI writing" — inflated significance,
  promotional language, `-ing` filler, em-dash and rule-of-three overuse, AI
  vocabulary, vague attributions, and chatbot artifacts ("I hope this helps!") —
  rewrites them, and pushes for real voice instead of clean-but-soulless prose.
- **CLI-neutral, minimal port.** Pure writing guidance — one `SKILL.md`, no
  scripts, state, or references — so it needed no runtime translation beyond
  house frontmatter (`name` + `description`, dropped the upstream `version:`) and
  attribution. Extracted from Factory's multi-skill `droid-evolved` plugin as a
  standalone single-skill plugin. Content based on Wikipedia's guide (WikiProject
  AI Cleanup, CC BY-SA).

#### Marketplace

- **Install.** `/plugin install autoresearch@pragmatic-growth` and
  `/plugin install human-writing@pragmatic-growth` (Claude Code), or the
  `@flywheel` equivalents (Droid). `marketplace.json`, `README.md`, the public
  site, and `CLAUDE.md`/`AGENTS.md` all updated to list four plugins. Release
  commit: [`557b933`](https://github.com/pragmaticgrowth/flywheel/commit/557b933).

## [4.5.0] — 2026-07-01

**Minor: factory-doctor detects and strips deprecated v3 config keys, and
recon's per-run model override is made CLI-aware.** Closes a real gap found on a
project that was set up under the v3 model, updated to the v4 plugin, and kept
running an `index.yaml` full of dead config.

- **`config-drift` check + auto-strip (factory-doctor).** A queue set up under
  v3 still carries `merge` / `wip` / `execution` / `autonomy` — keys the v4
  one-goal/local-gate model removed and that v4 dispatch now **silently ignores**,
  so the owner keeps thinking in the old PR/worktree/herdr model. The read-only
  probe (`doctor_checks.py`) gains a `config-drift` check (new
  `DEPRECATED_V3_KEYS` constant + `config_drift_check` helper, unit-tested) that
  WARNs naming exactly which dead keys are present; factory-doctor then
  **auto-strips only those keys** from `index.yaml` config in one atomic edit,
  preserving every live key (`base`/`model`/`skills`/`verify`/`budget`), comments,
  and all `goals:` entries, echoing each removed `key=value` under `fixed:`. The
  removed-key set is one constant so future removals extend one list.
- **Recon model override made CLI-aware (define-goal).** Recon still inherits the
  session/runtime model by default and there is deliberately **no**
  `config.research_model` knob (it would need per-CLI translation and re-invites
  the shallow-recon failure the rule guards against). The one override — a per-run
  user ask — is now documented as CLI-aware: in Claude Code it's an Anthropic-only
  alias (`opus`/`sonnet`/`haiku`/`inherit`); in Droid it's a concrete full model
  ID via `droid exec -m <id>` (no `sonnet`-style short alias exists there, and
  headless accepts only built-in IDs). Model-ID strings are treated as
  version-dependent; the stable fact is the format.
- **Docs aligned.** CLAUDE.md/AGENTS.md, README, and the site version reflect the
  new factory-doctor auto-fix. Source change:
  [`11006c0`](https://github.com/pragmaticgrowth/flywheel/commit/11006c0).

## [4.4.0] — 2026-07-01

**Minor: dispatch's intra-goal quality loop gets a multi-lens fresh check and
named subagent patterns.** No change to the sequential, one-goal-per-run,
worktree-free dispatch model — this sharpens the per-goal quality loop and
documents why the model is shaped the way it is.

- **Multi-lens fresh check.** The implementer's post-implementation review
  (quality-loop step 5) upgrades from a single verifier/reviewer subagent to a
  small panel of independent read-only lenses run concurrently:
  contract-conformance, tests + overbuild, and stray-files + regressions. Two or
  three lenses is the norm and stays lightweight; it escalates to a read-only
  review Workflow only at the ~5+ independent-checks threshold already defined in
  quality-loop step 3. Proportional by design — a one-file mechanical edit skips
  the panel entirely. Source change:
  [`44aa885`](https://github.com/pragmaticgrowth/flywheel/commit/44aa885).
- **Named subagent patterns.** The implementer brief now names
  `subagent-driven-development` as the method behind its nested read-only
  fan-out, and calls out two patterns that fit inside one goal: adversarial
  verification (a reviewer tries to refute the change, not rubber-stamp it) and
  loop-until-dry for bug hunts. All graceful — "invoke the skill when it is
  available," with the run-it-yourself fallback intact when subagents aren't
  provided.
- **The sequential model documented as deliberate scar tissue.** The dispatch
  header now states outright that the single-branch, worktree-free, no-parallel
  shape is a deliberate choice with the v3 livelock behind it (see 4.0.0), so
  worktrees and cross-goal parallelism are not re-proposed as "missing." The
  extra concurrency lives INSIDE one goal (read-only recon/review), never across
  goals.
- **Docs aligned.** README's per-goal description reflects the multi-lens fresh
  check; the public site and README version text advertise v4.4.0.

## [4.3.0] — 2026-06-30

**Minor: HTML artifacts split into their own marketplace plugin.** This release
keeps `html-artifacts` in the same GitHub repository and `pragmatic-growth`
marketplace, but publishes it as a separate installable plugin.

- **Two-plugin marketplace.** `.claude-plugin/marketplace.json` now lists both
  `flywheel` and `html-artifacts`; the new plugin is sourced from
  `./plugins/html-artifacts`.
- **Flywheel refocused.** The root `flywheel` plugin now contains the four
  workflow skills only: `define-goal`, `dispatch`, `loop-architect`, and
  `factory-doctor`.
- **HTML artifacts preserved.** The existing `html-artifacts` skill and its
  progressive-disclosure references moved intact under
  `plugins/html-artifacts/skills/html-artifacts/`, with its own plugin manifest
  at version 1.0.0.
- **Install docs aligned.** README, CLAUDE/AGENTS, and the public site now show
  the separate install commands: `flywheel@pragmatic-growth` and
  `html-artifacts@pragmatic-growth` for Claude Code, or `flywheel@flywheel` and
  `html-artifacts@flywheel` for Droid. Source change:
  [`d802bbc`](https://github.com/pragmaticgrowth/flywheel/commit/d802bbc5f6517929e3656651b7cd64c9f5bec342).
- **Release metadata aligned.** The root plugin manifest, README version badge,
  and public site version text now advertise v4.3.0.

## [4.2.0] — 2026-06-30

**Minor: HTML artifacts join the marketplace.** This release adds a fifth skill,
`html-artifacts`, for rich browser deliverables when markdown would flatten the work.

- **New `html-artifacts` skill.** Produces self-contained `.html` plans, specs, PR/code
  review writeups, module maps, diagrams, timelines, research explainers, status/incident
  reports, decks, prototypes, and one-off editors with copy/export round trips. Source
  change: [`fff9b12`](https://github.com/pragmaticgrowth/flywheel/commit/fff9b12).
- **Progressive-disclosure references.** The skill keeps a compact trigger/routing
  `SKILL.md`, with separate references for foundation rules, planning/comparison,
  code review, design/prototypes, diagrams/data, reports/research, custom editors,
  decks, and source coverage.
- **Skills-only boundary preserved.** The new skill does not add commands, servers,
  listeners, hooks, MCP surfaces, or a build step; interactive artifacts round-trip via
  in-file copy/export buttons.
- **Docs and coverage aligned.** README, CLAUDE/AGENTS, the public site, and regression
  tests now advertise the five-skill lineup and guard against accidentally adding a
  listener/server surface to `html-artifacts`.
- **Release metadata aligned.** The plugin manifest, marketplace copy, README version
  badge, and public site version text now advertise v4.2.0.

## [4.1.3] — 2026-06-28

**Patch: recon subagents inherit the session model.** This release removes the hard-coded
Sonnet policy for `define-goal` recon and synthesis subagents.

- **Model inheritance for recon.** `define-goal` now tells recon search subagents and the
  optional synthesis/judgment subagent to inherit the current session/runtime model, and not
  set a fixed alias, including Sonnet, unless the user explicitly asks for one in that run.
  Source change:
  [`89ae165`](https://github.com/pragmaticgrowth/flywheel/commit/89ae165).
- **Config scope clarified.** `config.model` remains scoped to spawned code-writing agents,
  while recon and batch-mode finder agents inherit the current model by default. The README,
  public site, and repo agent guide now use the same wording.
- **Regression coverage added.** A docs policy test now fails if active docs reintroduce
  forced-Sonnet recon language or drift in the public config model vocabulary.
- **Release metadata aligned.** The plugin manifest, README version badge, and public site
  version text now advertise v4.1.3.

## [4.1.2] — 2026-06-28

**Patch: versioned agent-guide alignment.** This release packages the
`CLAUDE.md` / `AGENTS.md` synchronization rule as an explicit versioned update.

- **Cross-runtime guide alignment.** `CLAUDE.md` now says Claude Code must verify
  `AGENTS.md` after guide edits, while Codex or Droid must update `CLAUDE.md`
  when they touch `AGENTS.md`. The repo keeps `AGENTS.md` as a symlink to
  `CLAUDE.md`, and the guideline now says to restore that symlink or update both
  filenames in the same commit if it is ever missing or broken. Source change:
  [`d1f8400`](https://github.com/pragmaticgrowth/flywheel/commit/d1f8400).
- **Release metadata aligned.** The plugin manifest, README version badge, and
  public site version text now advertise v4.1.2.

## [4.1.1] — 2026-06-28

**Patch: brief-first goal intake and Droid install hardening.** This keeps the v4.1
one-goal dispatch model unchanged while removing two autonomy blockers found in review.

- **Brief-first goal and loop intake.** `define-goal` now explicitly extracts the desired
  outcome, target system/environment, validator, scope, risk, and destination before recon,
  asks at most one concise proactive question round when those facts would change the goal,
  and still finishes with a real run-now command or queued goal artifact. `loop-architect`
  now uses the same short intake and returns to `define-goal` when a recurring factory run
  needs an actual goal contract.
- **Droid install path aligned with current Factory docs and the local CLI.** README and the
  public site use the tested GitHub marketplace add + `flywheel@flywheel` install flow,
  include `droid plugin marketplace list` so users can confirm Factory's registered
  marketplace name, and include a Droid headless `/factory-doctor` preflight command.
  `CLAUDE.md` no longer recommends invalid `droid plugin marketplace add ./` validation.
- **Factory Doctor path resolution hardened.** The skill resolves `$DROID_PLUGIN_ROOT`
  directly before falling back to the Factory plugin cache, instead of relying on an
  undocumented `$CLAUDE_PLUGIN_ROOT` alias in Droid.
- **Marketplace copy aligned.** The marketplace description now says Flywheel works one
  ready goal per run on the current branch, not isolated implementer lanes.

## [4.1.0] — 2026-06-28

**One-goal dispatch with a lightweight subagent-driven quality loop.** `dispatch` now works
at most one ready goal per run, then reports and stops. Long unattended runs still drain the
queue by repeating the same safe cycle with `/loop /dispatch` (Claude Code) or a
same-session Droid cron. This keeps the v4 direct-to-branch model simple while making each
fire easier to reason about and recover.

- **One ready goal per `/dispatch` run.** The current branch remains the integration surface:
  no PRs, no worktrees, no `goal/<id>` branches, and no parallel code-writing lanes. PASS
  still squashes to one `feat(goal NNN)` commit and completes the goal; FAIL still rolls back
  to `gate_base` and blocks with a reason.
- **Latest-context preflight.** Before spawning the implementer, `dispatch` now gathers a
  short read-only summary of the newest plan/progress note and any current/latest PR context
  available through `gh`. That context is advisory only: it never creates a merge gate,
  authorizes a branch switch, or overrides the goal contract/local gate.
- **Subagent-driven discipline without the old orchestration machinery.** The single
  foreground implementer must use a short plan/checklist, TDD for code changes, and a fresh
  verifier/reviewer subagent for non-trivial work. Workflow/mission mode is allowed only for
  bounded read-only fan-out or review inside that one goal, never for parallel
  implementation or cross-run state.
- **Docs aligned.** `define-goal`, `loop-architect`, `CLAUDE.md`, README, and the public site
  now describe one-goal dispatch, TDD-backed checks, and repeated `/loop /dispatch` as the
  queue-drain mechanism.

## [4.0.1] — 2026-06-28

**Patch: harden the bug repro-direction gate against a false PASS.** The local gate ran a
`type: bug` goal's `acceptance:` command in a *fresh* base `git worktree` that lacks installed
deps (`node_modules`/`.venv` are gitignored), so a test-runner command (`npm test`/`pytest`)
could go red on base for **environment** reasons and be mistaken for a genuine bug
reproduction — a false PASS. Two guards in `pg_validate.py`:

- **Best-effort dep-sharing.** The base worktree now symlinks the live checkout's dependency
  dirs (`node_modules`, `.venv`, `venv`, `vendor`) so the acceptance command runs against base
  product code with a working environment. Cleanup removes only the symlink, never the target.
- **Bare-base control run.** When a separate proving test is overlaid (the TDD case), the gate
  runs the acceptance on the bare base *first*; if base can't run clean before the proving test
  exists, the red is environment/pre-existing noise → **INCONCLUSIVE, never a forged PASS**.
  Direct-probe acceptance (e.g. `grep`, no overlaid test file) is unchanged.

This converts the prior false-PASS path into a safe INCONCLUSIVE → surfaced for a human, in
keeping with the v4 "never silent-PASS" rule. (Caught by the v4.0.0 final review.)

## [4.0.0] — 2026-06-27

**BREAKING — the factory goes sequential and local.** `dispatch` no longer opens
pull requests, creates worktrees, or runs implementers in parallel. It drains the
`docs/goals/` queue one goal at a time, in a single session, committing directly to
the branch you start it on, and keeps each goal only if a **local build+test gate**
passes. This replaces the entire v3 PR → CI → auto-merge model, which livelocked on
real autonomous runs: dozens of PR-shepherding cycles per PR, self-hosted CI runners
going offline and blocking every merge, and piles of stale `goal/*` and
`worktree-agent-*` branches left as garbage. Sequential + local-gated removes that
whole class of failure.

- **`dispatch` is a sequential single-session drain.** Per goal: claim → one
  *foreground* implementer commits its work on the current branch → the orchestrator
  runs the local gate authoritatively → **PASS** squashes the work into one
  `feat(goal NNN)` commit kept on the branch; **FAIL** rolls back to the goal's
  `gate_base` and marks it `blocked`. No PRs, no worktrees, no `goal/<id>` branches,
  no `wip`/parallel agents, no herdr. Two anchors per goal — `anchor` (pre-claim HEAD)
  and `gate_base` (post-claim HEAD, what the gate diffs against, so the claim's queue
  commit isn't in the validated diff).
- **The local gate replaces CI as the merge gate.** `pg_validate.py` was rewritten
  from a GitHub-PR gate (`--pr`) into a local branch-diff gate (`--head/--base`, no
  `gh`): blast-radius, forbidden-content/secret scan, one-goal integrity, and the bug
  repro-direction proof (red-on-base → green-on-head) all run on the local
  `gate_base..HEAD` diff plus the repo's ordered `config.verify` commands. Unresolved
  refs or no runnable gate → `INCONCLUSIVE`, never a silent PASS. CI, if the repo has
  it, is a **non-blocking** post-push observation surfaced under `needs-you`.
- **Config slimmed** to `base`, `model`, `skills`, `verify` (the ordered local
  build+test gate, e.g. `["npm ci", "npm run build", "npm test"]`), and `budget`.
  Removed: `merge`, `wip`, `validation`/`llm_validation`/`validator_model`/
  `validation_attempts`, `execution`, `autonomy`, `state_branch`.
- **Removed machinery:** `pg_safe_merge.py` (the PR merge wrapper), `pm.py` +
  `references/herdr-mode.md` + the herdr-pm vendoring, and `resolve_ids.py` (the herdr
  pane resolver). ~82 KB of code deleted.
- **`factory-doctor`** dropped the PR/CI-world checks (`merge-permission`,
  `branch-protection`, `base-push`, `state-branch`, `validation-gate`) and added
  `verify` (local gate configured & runnable), `working-tree` (clean), and
  `working-branch`. `gh`/`gh-auth`/`ci` are now INFO-only; the only CLI flag is
  `--base`.
- **`define-goal`** goal contracts no longer instruct opening a PR; dropped the
  parallel-`wip` guidance; goals carry `acceptance:`/`verify` for the local gate;
  a criterion that can't be expressed as a command becomes a human-verification item
  surfaced under `needs-you` (the opt-in LLM validator is gone).
- **`loop-architect`** documents `dispatch` as a sequential single-session drain;
  `/loop` is only for picking up later-added goals, not a 15-minute parallel cadence.
- Docs (CLAUDE.md invariants, README, the public site) rewritten to the sequential,
  local-gated, direct-to-branch model.

## [3.0.1] — 2026-06-25

**Validator fix: TDD bug fixes no longer FAIL_CONTRACT just because the proving
test arrives with the fix.** A real `merge: auto` run kept rejecting genuinely-good
bug fixes: the deterministic gate's repro-direction check ran the goal's
`acceptance:` commands on a clean base checkout and demanded one go red, but in
standard TDD the failing test is *added by the fix PR* — so it never exists on
base, nothing can be red there, and every good fix was ruled "fixed nothing"
(FAIL_CONTRACT). The contract couldn't be amended around it either: even adding
the test command to `acceptance:` didn't help, because the test file still isn't
on base.

- **`pg_validate.py` now overlays the PR's changed test files onto the base
  checkout** (`git checkout <head> -- <test-files>`) before running `acceptance:`
  for `type: bug`. A genuine regression test then fails on base product code (bug
  present) and passes on head (bug fixed) — the canonical red→green proof. The
  overlay is monotonic: it only adds tests, never removes the bug, so it can never
  turn a previously-passing validation into a failure.
- Test-file detection (`is_test_path`) spans JS/TS (`.test.`/`.spec.`/`__tests__`),
  Python (`test_*.py`), Go (`_test.go`), Ruby, Java, and `tests/`/`spec/` dirs.
- FAIL_CONTRACT evidence is now specific: "tests overlaid but still green on base"
  (the test doesn't reproduce the bug) vs "no recognizable test file in the diff"
  (the fix ships no regression test) — instead of a single ambiguous "fixed
  nothing".
- **`define-goal`** now requires `type: bug` goals to name a real test-running
  command in `acceptance:` (not just typecheck/lint/build) — the gate needs a
  command that actually executes the regression test, or there is nothing to go
  red. This was the second half of the same real-run failure (a hydration bug
  whose `acceptance:` was only typecheck/lint/build).
- `dispatch`'s Validate step (2b) documents the overlay and the remaining genuine
  contract gap.

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
