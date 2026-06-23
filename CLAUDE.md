# pg-plugin

## Project Overview

Skills-only Claude Code plugin from Pragmatic Growth, v2.7.0. No MCP
servers, no commands, no agents, no hooks, no build step — three skills
under `skills/`, each a single `SKILL.md`, forming a plain-language →
autonomous-execution pipeline around a file-based goal queue
(`docs/goals/` in target repos):

- **define-goal** — plain-language wants → measurable goal contracts.
  Two destinations: a copy-pasteable `/goal` line to run now, or a queued
  goal file (`docs/goals/NNN-slug.md` + `index.yaml` entry). Includes
  repo grounding (CLAUDE.md/AGENTS.md rules copied verbatim, real
  verification commands) and a batch mode for documents of items.
  Produces goals only, never implements. Originally adapted from
  OpenAI's curated `define-goal` skill (its `create_goal`/`get_goal`
  tools don't exist in Claude Code; `/goal` is user-run, transcript-
  evaluated, 4,000-char condition cap).
- **dispatch** — factory orchestrator for the docs/goals queue:
  shepherds factory PRs, claims goals via the claim protocol, spawns one
  isolated worktree implementer per goal, integrates merge-backs under
  `merge: auto`. Solo mode ("work goal 005") turns an interactive
  session into a one-goal orchestrator. Built to run as
  `/loop 15m /dispatch`; iterations are idempotent and parallel sessions
  are safe. Opt-in `config.execution: herdr` mode runs each implementer as
  a fresh `/goal` `claude` in its own `goal/NNN` herdr worktree pane
  (parallel, observable, crash-recoverable); default `native` keeps the
  in-process path and full portability.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs;
  names `docs/goals/index.yaml` the canonical factory ledger.

## Queue design invariants (research-backed, decided 2026-06-12)

- Status lives ONLY in `index.yaml`, never in goal-file frontmatter —
  dual-write drifts. Goal files are immutable contracts.
- Statuses: `not_started | in_progress | completed | blocked` — blocked
  (with reason) is required to avoid re-dispatch livelock. `completed`
  only when the work is merged.
- `index.yaml` `config:` block: `base` (integration branch goals branch
  from and merge back to — main, staging, or other; per-goal `base:`
  override allowed), `merge: pr|auto`, `wip` parallelism cap, `model`
  (inherit|sonnet|haiku — applied to every code agent dispatch spawns;
  the repo owner's depth-vs-limit trade), repo-wide `skills`,
  `execution` (native|herdr — spawn substrate), `autonomy`
  (conservative|balanced|bold — herdr block-handling threshold).
  Defaults: repo default branch, `pr`, 2, inherit, none, native, balanced.
- Goal frontmatter `type: bug|feature|chore` shapes the contract: bugs
  always lead with a failing-test-reproduces-root-cause criterion (all
  recon hypotheses recorded); features must fill Out of scope; chores
  prove "no behavior change" (suite green before and after) plus one
  mechanical check.
- Claim protocol: every status write is pull → flip one entry → commit
  (`chore(goals): claim|complete|block|archive <id>`) → push on the base
  branch; push acceptance arbitrates parallel sessions. Same arbitration
  covers NNN minting (collision → renumber the NEW goal only; never
  renumber existing goals).
- `merge: auto` integration is orchestrator-only, one goal at a time,
  sync-with-current-base then re-verify before every merge; substantive
  conflicts → `blocked`, never guessed through. Implementers never
  merge and never edit `docs/goals/`.
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
- Recon (define-goal) never inherits the session model: search angles on
  the Explore agent type (fallback `model: haiku`), at most one judgment
  agent on `model: sonnet` — weekly-limit economy, doc-backed.
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
.claude-plugin/plugin.json        # manifest — name: pg-plugin
.claude-plugin/marketplace.json   # marketplace — name: pragmatic-growth
skills/<name>/SKILL.md            # the three skills
AGENTS.md                         # symlink → CLAUDE.md (one source, no drift)
```

## Rules

- **Skills-only.** Don't add MCP servers, commands, agents, or hooks here
  without an explicit ask.
- **Portability.** Skills must not contain user-specific absolute paths
  (`/Users/...`, `~/.claude/...`). They run in arbitrary repos.
- **This repo is the single source of truth.** The plugin is installed
  user-scoped from the `pragmatic-growth` marketplace; the former
  user-level copies in `~/.claude/skills/` were deleted on 2026-06-10.
  Skill edits land here, bump the `plugin.json` version, push, then
  refresh with `/plugin marketplace update pragmatic-growth`.
- **Push every time.** Pushing to GitHub (`origin main`) after committing
  is pre-authorized — always push without asking. The installed plugin
  refreshes from GitHub, so an unpushed commit is an unshipped skill.
- **Validation.** After changing plugin structure or manifests, run the
  `plugin-dev:plugin-validator` agent before committing.
- **Skill edits are tested.** New or changed skill mechanics get a
  subagent dry-run (scenario + "cite the section that decides each
  answer") before shipping; close every flagged ambiguity.
