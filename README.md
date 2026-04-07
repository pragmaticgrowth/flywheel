# mcp-droid

> **Status: scaffolding — not yet implemented.** Build brief at
> [`docs/spec.md`](docs/spec.md).

A local **stdio MCP server** that exposes the Factory AI [`droid`](https://docs.factory.ai/cli/getting-started/overview)
CLI as a typed tool surface inside Claude Code (and any other MCP client).

## What it does

- Wraps `droid exec` via subprocess and parses `--output-format stream-json` so
  every droid call has structured input and output
- Surfaces droid **sessions** and **missions** by reading `~/.factory/` directly
  (sessions-index.json, `missions/<uuid>/state.json`, `progress_log.jsonl`)
- Inherits the caller's `cwd`, so when Claude Code in project X spawns this
  server, droid runs in X with X's `.factory/` config and X's session history
- Ships specialized tool presets, one per droid profile in `~/.factory/droids/`
  (research, code review, explore, simplify, silent-failure scan, …)

## Tools (planned)

| Group | Tools |
|---|---|
| Generic | `droid_exec`, `droid_list_tools`, `droid_list_models`, `droid_list_profiles` |
| Presets | `droid_research`, `droid_research_fast`, `droid_review_code`, `droid_explore_code`, `droid_architect`, `droid_simplify`, `droid_silent_failure_scan`, `droid_pr_test_analyzer`, `droid_type_design_analyzer`, `droid_scrutiny_review`, `droid_user_testing_validator` |
| Missions | `droid_mission_start`, `droid_mission_list`, `droid_mission_status`, `droid_mission_progress`, `droid_mission_cancel` |
| Sessions | `droid_session_continue`, `droid_session_fork`, `droid_session_list`, `droid_session_search` |
| Spec mode | `droid_spec` |

Full schemas live in [`docs/spec.md`](docs/spec.md).

## Requirements

- Node.js ≥ 18
- [`droid`](https://docs.factory.ai/cli/getting-started/overview) CLI ≥ 0.95
- A Factory account — either `FACTORY_API_KEY` exported, or already logged in
  via `droid` (auth lives in `~/.factory/auth.v2.file`)

## Install (after the build session)

```bash
npm install
npm run build
claude mcp add mcp-droid -- node /Users/serkan/mcp-droid/dist/index.js
```

## Why

The global `~/CLAUDE.md` "Droid Headless Models — Token Saving" rule already
tells Claude to spawn `droid exec ...` from the Bash tool for research and
review. That works but is unstructured: every call is a raw shell string,
output is unparsed, sessions/missions are invisible. `mcp-droid` keeps the same
token-saving model but gives it a typed MCP surface that any client can call.

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — full project context for AI agents
- [`AGENTS.md`](AGENTS.md) — agent-agnostic rules
- [`docs/spec.md`](docs/spec.md) — the build brief

## License

Personal project. No license declared.
