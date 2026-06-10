# pg-plugin

## Project Overview

Skills-only Claude Code plugin from Pragmatic Growth. No MCP servers, no
commands, no agents, no hooks, no build step — just three skills under
`skills/`, each a single `SKILL.md`:

- **wish** — plain-language wants → agent-ready GitHub issues with
  measurable goal contracts. Produces issues only, never implements.
- **dispatch** — factory orchestrator for the GitHub issue queue: reviews
  factory PRs, claims agent-ready issues, spawns one isolated implementer
  agent per issue. Built to run as `/loop 15m /dispatch`; iterations are
  idempotent.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs.

History note: this repo was previously `mcp-do`, a stdio MCP server
wrapping droid/opencode CLIs. All of that was removed in the v1.0.0
transformation — git history has it if ever needed.

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
- **The canonical copies live here.** `~/.claude/skills/{wish,dispatch,
  loop-architect}` are the user-level originals; once the plugin is
  installed, edits should land in this repo and version-bump
  `plugin.json`.
- **Validation.** After changing plugin structure or manifests, run the
  `plugin-dev:plugin-validator` agent before committing.
