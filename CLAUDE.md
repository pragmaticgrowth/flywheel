# pg-plugin

## Project Overview

Skills-only Claude Code plugin from Pragmatic Growth. No MCP servers, no
commands, no agents, no hooks, no build step — just three skills under
`skills/`, each a single `SKILL.md`, forming a pipeline around a
file-based goal queue (`docs/goals/` in target repos):

- **define-goal** — plain-language wants → measurable goal contracts.
  Two destinations: a copy-pasteable `/goal` line to run now, or a queued
  goal file (`docs/goals/NNN-slug.md` + `index.yaml` entry). Absorbed the
  former wish skill's repo-grounding and batch-document modes. Produces
  goals only, never implements. Originally adapted from OpenAI's curated
  `define-goal` skill (its `create_goal`/`get_goal` tools don't exist in
  Claude Code).
- **dispatch** — factory orchestrator for the docs/goals queue: shepherds
  factory PRs, claims `not_started` goals (status flip committed before
  spawning), spawns one isolated implementer agent per goal. Sole writer
  of status in `index.yaml`. Built to run as `/loop 15m /dispatch`;
  iterations are idempotent.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs.

Queue design invariants (decided 2026-06-12, research-backed): status
lives only in `index.yaml` (never goal-file frontmatter); statuses are
`not_started | in_progress | completed | blocked` — blocked is required
to avoid re-dispatch livelock; sequential `NNN-slug` IDs are safe because
only define-goal mints them; implementers never edit `docs/goals/`.

History note: this repo was previously `mcp-do`, a stdio MCP server
wrapping droid/opencode CLIs (removed in v1.0.0). The **wish** skill
(wants → GitHub issues) was retired in v2.0.0 on 2026-06-12 — the
docs/goals file queue replaced GitHub issues as the work queue (issue
bodies cap at 65,536 chars; labels needed per-repo bootstrap). Git
history has both if ever needed.

## Structure

```
.claude-plugin/plugin.json        # manifest — name: pg-plugin
.claude-plugin/marketplace.json   # marketplace — name: pragmatic-growth
skills/<name>/SKILL.md            # the three skills
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
