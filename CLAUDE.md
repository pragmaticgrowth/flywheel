# pg-plugin

## Project Overview

Skills-only Claude Code plugin from Pragmatic Growth, v2.4.0. No MCP
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
  are safe.
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
  the repo owner's depth-vs-limit trade), repo-wide `skills`. Defaults:
  repo default branch, `pr`, 2, inherit, none.
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
