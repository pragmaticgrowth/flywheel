# mcp-droid

**Status: v0.1.0 verified.** 24 MCP tools, 172 passing unit tests,
11/11 smoke tests, 71/71 live MCP-client tool calls across 5
verification rounds. Registered at user scope — works from any
Claude Code session regardless of cwd.

A local **stdio MCP server** that exposes the Factory AI [`droid`](https://docs.factory.ai/cli/getting-started/overview)
CLI as a typed tool surface inside Claude Code (and any other MCP
client).

## What it does

- Wraps `droid exec` via subprocess and parses `--output-format
  stream-json` so every droid call has structured input and output
- Surfaces droid **sessions** and **missions** by reading
  `~/.factory/` directly (sessions-index.json with optional
  `scan_disk` fallback, `missions/<uuid>/` on-disk state with graceful
  partial-state handling)
- Inherits the caller's `cwd`, so when Claude Code in project X
  spawns this server, droid runs in X with X's `.factory/` config and
  X's session history
- Ships specialized tool presets, one per droid profile in
  `~/.factory/droids/` (research, code review, explore, simplify,
  silent-failure scan, …)
- Missions spawn **detached** with output logged to a temp file —
  the mission keeps running even if mcp-droid exits
- Full error surfacing: on any non-zero exit, the response includes
  `exit_code`, `signal`, `duration_ms`, parsed stream events, stderr,
  and raw stdout tail

## Tools (24)

| Group | Tools |
|---|---|
| Generic | `droid_exec`, `droid_list_tools`, `droid_list_models`, `droid_list_profiles` |
| Presets | `droid_research`, `droid_research_fast`, `droid_review_code`, `droid_explore_code`, `droid_architect`, `droid_simplify`, `droid_silent_failure_scan`, `droid_pr_test_analyzer`, `droid_type_design_analyzer`, `droid_scrutiny_review`, `droid_user_testing_validator` |
| Missions | `droid_mission_start`, `droid_mission_list`, `droid_mission_status`, `droid_mission_progress`, `droid_mission_cancel` |
| Sessions | `droid_session_continue`, `droid_session_fork`, `droid_session_list`, `droid_session_search` |
| Spec mode | `droid_spec` |

Full schemas and example calls in [`docs/spec.md`](docs/spec.md).
User-facing usage guide in the committed skill at
[`.claude/skills/droid-mcp/SKILL.md`](.claude/skills/droid-mcp/SKILL.md).

## Requirements

- Node.js ≥ 18
- [`droid`](https://docs.factory.ai/cli/getting-started/overview)
  CLI ≥ 0.95
- A Factory account — either `FACTORY_API_KEY` exported, or already
  logged in via `droid` (auth lives in `~/.factory/auth.v2.file`)

## Install

```bash
git clone git@github.com:pragmaticgrowth/mcp-droid.git
cd mcp-droid
npm install
npm run build
npm link                              # optional: adds `mcp-droid` to PATH
claude mcp add -s user mcp-droid -- node $(pwd)/dist/index.js
# or, if you ran npm link:
# claude mcp add -s user mcp-droid -- mcp-droid
```

After this, every Claude Code session will have all 24 `mcp__mcp-droid__*`
tools available regardless of which project it's running in.

The companion usage skill at `.claude/skills/droid-mcp/` is tracked
in this repo and symlinked from `~/.claude/skills/droid-mcp` so
editing the files here instantly updates what Claude Code loads.

## Development

```bash
npm run build         # tsc → dist/
npm run dev           # tsx src/index.ts (stdio loopback for testing)
npm start             # node dist/index.js
npm test              # vitest run — 172 tests across 8 files
npm run test:watch    # vitest watch mode
bash scripts/smoke-stdio-list.sh       # JSON-RPC tools/list
bash scripts/smoke-stdio-readonly.sh   # four read-only tools
bash scripts/smoke-stdio-full.sh       # 11 tools + real MiniMax exec
bash scripts/smoke-stdio-presets.sh    # all 11 specialized presets
```

## Project structure

```
src/
├── index.ts                # MCP server entry, stdio transport
├── droid/
│   ├── defaults.ts         # DEFAULT_MODEL, DEFAULT_SPEC_MODEL
│   ├── exec.ts             # spawnDroidExec + runDroidProcess
│   ├── flags.ts            # typed DroidExecFlags → argv
│   ├── output.ts           # stream-json parser
│   ├── sessions.ts         # list/read sessions (index + scan_disk paths)
│   ├── missions.ts         # list/read/poll missions, graceful partial state
│   ├── profiles.ts         # ~/.factory/droids/*.md parser
│   └── models.ts           # customModels from settings.json
├── tools/
│   ├── index.ts            # registerAllTools
│   ├── exec.ts             # droid_exec
│   ├── presets.ts          # 11 specialized presets
│   ├── missions.ts         # 5 mission tools
│   ├── sessions.ts         # 4 session tools
│   ├── spec.ts             # droid_spec
│   └── meta.ts             # droid_list_models/_profiles/_tools
├── schemas/                # zod input schemas
└── utils/
    ├── cwd.ts              # resolveCwd
    └── errors.ts           # createJsonResponse, execResultToToolResponse
```

## Why

The global `~/CLAUDE.md` "Droid Headless Models — Token Saving" rule
already tells Claude to spawn `droid exec ...` from the Bash tool for
research and review. That works but is unstructured: every call is a
raw shell string, output is unparsed, sessions/missions are invisible.

`mcp-droid` keeps the same token-saving model but gives it a typed
MCP surface that any client can call. Also exposes mission management
and session continuation that the shell-string approach can't touch.

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — full project context for AI agents
- [`AGENTS.md`](AGENTS.md) — agent-agnostic rules
- [`docs/spec.md`](docs/spec.md) — architecture spec with verified
  shapes (stream-json events, sessions-index.json, mission state.json)
- [`.claude/skills/droid-mcp/`](.claude/skills/droid-mcp/) — user-facing
  skill for how to USE this MCP (symlinked from
  `~/.claude/skills/droid-mcp`)

## License

Personal project. No license declared.
