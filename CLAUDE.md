# pg-plugin

## Project Overview

Skills-only plugin for Claude Code and Droid (Factory CLI) from Pragmatic Growth, v2.9.7.
No MCP servers, no commands, no agents, no hooks, no build step — four skills
under `skills/` (two ship deterministic Python helpers in `scripts/`),
forming a plain-language → autonomous-execution pipeline around a
file-based goal queue (`docs/goals/` in target repos). The plugin works in
both CLIs via Droid's Claude Code compatibility layer (Droid auto-translates
the `.claude-plugin/` manifest format). Skills are CLI-aware — they detect
the runtime and use appropriate paths, commands, and scheduling primitives.

- **define-goal** — plain-language wants → measurable goal contracts.
  Two destinations: a copy-pasteable `/goal` line (Claude Code) or
  `droid exec --auto high "…"` (Droid) to run now, or a queued
  goal file (`docs/goals/NNN-slug.md` + `index.yaml` entry). Includes
  repo grounding (CLAUDE.md/AGENTS.md rules copied verbatim, real
  verification commands) and a batch mode for documents of items.
  Produces goals only, never implements. Originally adapted from
  OpenAI's curated `define-goal` skill (its `create_goal`/`get_goal`
  tools don't exist in either CLI; `/goal` is user-run, transcript-
  evaluated in Claude Code, self-verified by the agent in Droid,
  4,000-char condition cap).
- **dispatch** — factory orchestrator for the docs/goals queue:
  shepherds factory PRs, claims goals via the claim protocol, spawns one
  isolated worktree implementer per goal, integrates merge-backs under
  `merge: auto`. Solo mode ("work goal 005") turns an interactive
  session into a one-goal orchestrator. Built to run as
  `/loop 15m /dispatch` (Claude Code) or `CronCreate` same_session
  every 15m (Droid); iterations are idempotent and parallel sessions
  are safe. Opt-in `config.execution: herdr` mode runs each implementer as
  a fresh `claude` in its own `goal/NNN` herdr worktree pane
  (parallel, observable, crash-recoverable — `droid` backend is future
  work; degrades to `native` in Droid today); default `native` keeps the
  in-process path and full portability. Phase 4 emits one report line per
  iteration leading with progress — `<done>/<total> done` plus a 20-cell
  fill bar, then labeled `ready`/`running`/`blocked` counts that sum to
  `total` (lead with done, never `ready/total`, which reads as "nothing
  done"); `needs-you` holds only human-blocked goals + mergeable PRs, since
  dep-blocked goals self-unblock as their dependency merges. Under `merge: auto`,
  a **deterministic `pg_validate.py` gate** (`config.validation: off|risk_based|required`,
  default `risk_based` = required for bug/feature + risk-flagged chores) runs on a fresh
  detached checkout before `pg_safe_merge`: one-goal integrity, bug repro-direction
  (the acceptance suite must be red on base → green on head), fresh-checkout
  acceptance-green, blast-radius, forbidden-content/secret scan — emitting a SHA-bound
  `PASS|FAIL_FIXABLE|FAIL_CONTRACT|INCONCLUSIVE` (the orchestrator reads the JSON `verdict`
  to split the two FAILs, both exit 3). PASS→merge with those SHAs; FAIL_FIXABLE→one worker
  repair then blocked; FAIL_CONTRACT→hold slot + needs-you contract amendment;
  INCONCLUSIVE→retry, never default-PASS. The orchestrator merges — the validator never does.
  A deterministic FAIL overrides any future LLM validator. **Phase 2 (opt-in):** when
  `config.llm_validation: on` (default off; costs tokens), step 2c spawns ONE read-only
  adversarial Agent (`config.validator_model`, default sonnet, never inherit) reusing the 2b
  worktree — fed ONLY the contract + raw diff + checkout, never the worker's narrative — that
  must earn a PASS with replayable evidence (criterion→diff map, outcome-vs-commands, one
  validator-authored adversarial probe, no-op reasoning); runs only after the deterministic
  gate PASSES (deterministic FAIL always wins), verdict feeds the same convergence (round cap
  `config.validation_attempts`, default 2), orchestrator merges. Mutation testing + a
  fleet-FAIL-rate health metric + the high-risk→human tail remain future work.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs;
  names `docs/goals/index.yaml` the canonical factory ledger.
- **factory-doctor** (v2.8.0) — one-pass preflight/doctor for a repo +
  machine: checks software, gh auth + scopes, the harness merge allow-rule,
  branch protection, CI, and queue state; aggressively auto-fixes everything
  local (writes the narrow `pg_safe_merge` allow-rule to
  `.claude/settings.local.json` or `.factory/settings.local.json` depending
  on CLI, scaffolds the queue) and reports remote/CI issues with exact fixes.
  Ships `scripts/doctor_checks.py` (read-only probe,
  `BLOCKER|WARN|FIXED|INFO`, exit 0/1/2). Pairs with
  `dispatch/scripts/pg_safe_merge.py` — a verified-merge wrapper (re-checks
  branch/body/base/CI/SHAs/no-queue-edits) that dispatch's Integration calls
  instead of raw `gh pr merge`, so the allow-rule stays narrow. v2.8.3 (from a
  real run on a target repo): the probe resolves the wrapper from the plugin
  INSTALL (its own `__file__`), never repo-relative — a target repo has no
  `skills/` dir, so the old repo-relative path was non-existent AND mismatched
  what dispatch invokes. And the allow-rule auto-fix is harness-blocked in
  auto/unattended mode (the classifier treats an agent adding its own `Bash(...)`
  rule as self-modification): the skill expects this, surfaces the exact line
  under needs-you (`permissions: blocked(classifier)`), and applies it only on
  the user's explicit "go" — never routes around the denial. v2.9.0: the probe
  checks settings in both `.claude/` and `.factory/` (Droid) paths.

## Queue design invariants (research-backed, decided 2026-06-12)

- Status lives ONLY in `index.yaml`, never in goal-file frontmatter —
  dual-write drifts. Goal files are immutable contracts.
- Statuses: `not_started | in_progress | completed | blocked` — blocked
  (with reason) is required to avoid re-dispatch livelock. `completed`
  only when the work is merged.
- `index.yaml` `config:` block: `base` (integration branch goals branch
  from and merge back to — main, staging, or other; per-goal `base:`
  override allowed), `state_branch` (branch holding the `docs/goals/` queue;
  default `= base`), `merge: pr|auto`, `wip` parallelism cap, `model`
  (inherit|sonnet|haiku — applied to every code agent dispatch spawns;
  the repo owner's depth-vs-limit trade), repo-wide `skills`,
  `execution` (native|herdr — spawn substrate), `autonomy`
  (conservative|balanced|bold — herdr block-handling threshold).
  Defaults: repo default branch (and `state_branch` = that base), `pr`, 2,
  inherit, none, native, balanced.
- `config.state_branch` (default `= base`) holds the `docs/goals/` queue;
  when `<base>` is protected, set it to a separate unprotected branch so the
  claim protocol + define-goal can push without touching the protected code
  branch. `<base>` receives only implementer code PRs. Default
  `state_branch = base` = today's behavior (no migration for unprotected repos).
- Goal frontmatter `type: bug|feature|chore` shapes the contract: bugs
  always lead with a failing-test-reproduces-root-cause criterion (all
  recon hypotheses recorded); features must fill Out of scope; chores
  prove "no behavior change" (suite green before and after) plus one
  mechanical check.
- Claim protocol: every status write is pull → flip one entry → commit
  (`chore(goals): claim|complete|block|archive <id>`) → push on the state
  branch (the queue's branch — `config.state_branch`, default `= base`);
  push acceptance arbitrates parallel sessions. Same arbitration
  covers NNN minting (collision → renumber the NEW goal only; never
  renumber existing goals).
- `merge: auto` integration is orchestrator-only, one goal at a time,
  sync-with-current-base then re-verify before every merge; substantive
  conflicts → `blocked`, never guessed through. Implementers never
  merge and never edit `docs/goals/`.
- Promotion (base → a downstream branch, typically `main`/production) is a
  separate human-gated step, NOT part of the iteration loop and NOT Integration
  (`pg_safe_merge.py` targets `<base>` and rejects non-`goal/` heads). v2.9.7
  (from a real 2026-06-24 run where promoting `<base>` into `main`
  auto-deleted it): never open the promotion PR with the persistent base as the
  PR head — a repo with GitHub's `delete_branch_on_merge: true` (correct for
  `goal/*` hygiene) deletes the merged PR's head, so the base vanishes as a side
  effect of the prod merge. Promote through a throwaway `promote-<date>-to-<target>`
  head branch (auto-delete kills the throwaway, base untouched), audit the merge's
  side effects (migrations, head fate) not just the diff, and verify the base
  still exists after. Protecting the base on GitHub is the robust repo-side guard
  (protected branches are never auto-deleted; pairs with `config.state_branch`).
- `merge: auto` needs merge rights: preflight once per session for a
  `gh pr merge` allow rule before the first integration. A harness
  denial of the orchestrator's own merge is an environment blocker,
  not a work failure (decided 2026-06-12 after a long unattended stall): the goal stays `in_progress` holding its wip slot — never
  `blocked`, which would free the slot and pile more unmergeable PRs —
  needs-you carries the exact allow-rule fix verbatim, the stalling
  fire sends ONE PushNotification per distinct blocker set (a report
  line in an unattended /loop has no reader), and later fires probe
  cheaply (PR merged? rule added?) instead of re-running sync/gates on
  a provably unmoved head.
- `execution: herdr` runs each implementer as a fresh `claude` in an
  isolated `goal/<id>` herdr worktree pane (vendored herdr-pm ops kit at
  `skills/dispatch/scripts/pm.py`, MIT, attributed in `VENDORED.md` — one
  STATE_ROOT re-root edit, else verbatim), driven by
  `skills/dispatch/references/herdr-mode.md` (the kit SHIPS INSIDE the plugin —
  no runtime dependency on the upstream repo; the herdr-pm name is MIT
  attribution only). The orchestrator resolves `pm.py`'s plugin path (into `$PM`)
  and its own `terminal_id` (into `$ORCH`, not `$HERDR_PANE_ID`) at preflight,
  then sends each implementer a plain-prose mission brief via `pm.py dispatch
  --file` (there is no `/goal` slash command to send); pm.py mints + anchors a
  unique `TASK_DONE_<hex4>` marker, re-checked from pane scrollback every fire
  (no reliance on a backgrounded wait); blocked implementers are handled tiered
  (auto-answer ≤ escalate)
  per `config.autonomy`. State is three-tier: `index.yaml` (claim truth) +
  `~/.local/state/pg-dispatch/` (runtime cache, with a `PAUSE` all-stop) +
  herdr/git (reality), reconciled by `pm.py lanes`. Default
  `execution: native` preserves the in-process path and full portability;
  herdr unreachable → degrade to native.
- Skills mandates come in three layers: method skills (writing-plans,
  TDD, verification-before-completion) hardcoded in dispatch's brief;
  repo skills in `config.skills`; goal-specific skills in goal
  frontmatter `skills:` (populated by define-goal from actually
  available skills).
- Implementer worktrees always branch `goal/<id>` from `origin/<base>`,
  never from inherited HEAD; PRs target `<base>` and carry "Goal: <id>".
- Recon (define-goal) runs BY DEFAULT before any goal touching an existing
  system (v2.8.1): investigate-first via parallel read-only subagents is not
  optional — "the description sounds clear" is the failure mode it replaces;
  skip only for genuinely greenfield or one-liner wants. Reaches the system
  wherever it lives (local checkout, separate repo, a host you connect to, a
  service/DB), told to each subagent, never hardcoded. It never inherits the
  session model; recon search subagents run as the `general-purpose` type on
  `model: sonnet`, strictly read-only (v2.8.2 — the built-in Explore type is
  locked to haiku and can't be raised, so general-purpose/sonnet is how recon
  buys real understanding; capping at sonnet vs an opus session is the remaining
  economy; the owner chose sonnet-for-all-recon over haiku-breadth). The synthesis
  agent is also sonnet. `config.model` governs only code agents, never recon.
  (Recon stays plain parallel subagents, NOT a Workflow: 2–4 agents is below the
  workflow scale threshold and a workflow can be disabled on a user's machine —
  define-goal batch mode is the only place that conditionally uses Workflow.)
- Workflow tool only where the docs' thresholds say it wins: define-goal
  batch mode at ~5+ items (drafts in script variables, approval table
  gates file writes). Dispatch implementers are NEVER workflows — runs
  are session-bound; branch commits + the stale-claim rule are the
  recovery path. The tool needs CLI ≥2.1.154 and can be disabled, so
  skills never assume it.

- Real-run hardening (v2.7.0, validated against a 24-goal `merge: auto`
  native run on a production repo, 2026-06-23): dispatch fills `min(wip,
  ready)` implementers EVERY iteration — claiming is a loop, not one goal
  per fire (the run silently sat at 1/2 capacity otherwise); a transient
  infra death (connection closed, parse error, 529) is not a blocker and
  doesn't burn the respawn budget, but transient respawns are capped
  (~3/goal/session) so a flaky spawn can't livelock; respawning a goal
  whose branch fell far behind `<base>` branches fresh, not a stale-
  checkpoint rebase; the queue commit is always its OWN command (never
  bundled with branch pruning — a bundled destructive op got the whole
  claim denied), and branch pruning verifies `gh pr view … state ==
  MERGED` first. Implementer-brief traps closed: never `cd` to the main
  checkout (silently measures the base branch); reproduce a cited bug
  before "fixing" it (upstream findings are hypotheses, ~⅓ are false
  positives even post-verification); stage only intended files; pre-
  existing `<base>`-red suites don't block a goal. Review loops converge
  (cap ~3 rounds, cosmetic nits → needs-you); a defect the goal's OWN
  criteria mandate becomes a needs-you contract amendment, not a serial
  merge. herdr mode remains UNVALIDATED in production — every real run to
  date is `native`.

History note: this repo was previously `mcp-do`, a stdio MCP server
wrapping droid/opencode CLIs (removed in v1.0.0 at ac2bd7c). The
**wish** skill (wants → GitHub issues) was retired in v2.0.0 on
2026-06-12 — the docs/goals file queue replaced GitHub issues as the
work queue (issue bodies cap at 65,536 chars; labels needed per-repo
bootstrap). Git history has both if ever needed.

## Structure

```
.claude-plugin/plugin.json        # manifest — name: pg-plugin (Droid auto-translates this format)
.claude-plugin/marketplace.json   # marketplace — name: pragmatic-growth
skills/<name>/SKILL.md            # four skills (define-goal, dispatch, loop-architect, factory-doctor)
skills/<name>/scripts/*.py        # deterministic helpers: dispatch/pm.py + pg_safe_merge.py, factory-doctor/doctor_checks.py
AGENTS.md                         # symlink → CLAUDE.md (one source, no drift)
```

## Rules

- **Skills-only.** Don't add MCP servers, commands, agents, or hooks here
  without an explicit ask.
- **Portability.** Skills must not contain user-specific absolute paths
  (`/Users/...`, `~/.claude/...`, `~/.factory/...`). They run in arbitrary repos.
- **This repo is the single source of truth.** The plugin is installed
  user-scoped from the `pragmatic-growth` marketplace; the former
  user-level copies in `~/.claude/skills/` were deleted on 2026-06-10.
  Skill edits land here, bump the `plugin.json` version, push, then
  refresh with `/plugin marketplace update pragmatic-growth` (Claude Code)
  or `droid plugin marketplace update pragmatic-growth` (Droid).
- **Push every time.** Pushing to GitHub (`origin main`) after committing
  is pre-authorized — always push without asking. The installed plugin
  refreshes from GitHub, so an unpushed commit is an unshipped skill.
- **Validation.** After changing plugin structure or manifests, run the
  `plugin-dev:plugin-validator` agent before committing (Claude Code only;
  Droid has no equivalent agent — validate manually: check skill frontmatter
  has `name` + `description`, run `droid plugin marketplace add ./` locally
  to test-install).
- **Skill edits are tested.** New or changed skill mechanics get a
  subagent dry-run (scenario + "cite the section that decides each
  answer") before shipping; close every flagged ambiguity.
