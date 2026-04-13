# mcp-do

## Project Overview

Local **stdio MCP server** and Claude Code **"do" plugin** that exposes
Factory AI `droid` CLI and `opencode` CLI as a unified typed tool surface.
Wraps both backends via `child_process.spawn` with intelligent structured
prompts (Codex-inspired: task + output contract + grounding rules). Supports
provider selection (`droid` | `opencode`) per tool call with model alias
resolution.

## Status

**v0.2.0** — unified droid + opencode backend with "do" plugin.

### Verification

| Check | Result |
|---|---|
| `npm run build` (tsc) | clean |
| `npm test` (vitest) | **183 passed** in 8 files |
| Provider abstraction | droid + opencode adapters verified |

### Tool surface (15 tools)

- **Generic (1)**: `do_exec` (provider param)
- **Specialized presets (9)**: `do_research`, `do_research_fast`, `do_review`, `do_explore`, `do_architect`, `do_silent_scan`, `do_type_check`, `do_pr_review`, `do_adversarial_review`
- **Cross-model (1)**: `do_cross_review` (3 models in parallel, provider param)
- **Sessions (2)**: `do_session_continue`, `do_session_list`
- **Meta (2)**: `do_list_models`, `do_list_profiles`

### "do" Plugin

The plugin lives in this repo: `.claude-plugin/plugin.json` (name: "do").

- **10 slash commands**: `/do:review`, `/do:research`, `/do:explore`, `/do:architect`, `/do:scan`, `/do:types`, `/do:exec`, `/do:session`, `/do:status`, `/do:setup`
- **3 subagents**: `do-researcher`, `do-reviewer`, `do-explorer` (thin forwarders)
- **1 skill**: `do-tools` — decision matrix + core rules
- **Bundled MCP server**: via `.mcp.json`

### Empirical findings baked into the code

- **`stream-json` is the only safe output format.** Plain `json` can
  return exit 0 with errors hidden in the payload. `parseStreamJson`
  in `src/droid/output.ts` scans for `error|failed|failure` event
  types and flags the run as failed even if exit code is 0.
- **sessions-index.json is incomplete.** Droid's indexer skips
  sessions created via `droid exec` (which is how mcp-do creates
  every session). `do_session_list` has a `scan_disk: true` opt-in
  that walks `~/.factory/sessions/<dir>/*.jsonl` directly.

## Why This Exists

Today the global `~/CLAUDE.md` "Droid Headless Models — Token Saving" rule tells
Claude to spawn `droid exec ...` from the Bash tool for research, code review,
silent failure scans, etc. That works but is unstructured: every call is a raw
shell string, output parsing is ad-hoc, sessions can't be discovered, mission
state is invisible.

`mcp-do` gives the same functionality a typed surface:

- One MCP tool per droid profile (research, review, explore, simplify, …)
- Mission start / list / status / progress backed by `~/.factory/missions/`
- Session continue / fork / list / search backed by `~/.factory/sessions-index.json`
- A generic `droid_exec` for power-users
- All tools inherit the caller's `cwd`, so when nt-dev's Claude Code spawns
  this server, droid runs in nt-dev with nt-dev's `.factory/` config and
  nt-dev's session history. No flags to set, no path juggling.

## Tech Stack

| Layer | Choice |
|---|---|
| Language | TypeScript (ES2022, strict, NodeNext) |
| MCP SDK | `@modelcontextprotocol/sdk@^1.27` |
| Transport | **stdio** (via `StdioServerTransport`) |
| Schema | `zod` |
| Build | `tsc` → `dist/` |
| Package manager | `npm` |
| Droid invocation | `child_process.spawn("droid", ["exec", …])` |
| Output format | `--output-format stream-json` (plain `json` lies about exit codes) |

## Project Structure (planned)

```
mcp-do/
├── CLAUDE.md                  # this file
├── AGENTS.md                  # pointer to CLAUDE.md + research rule
├── README.md                  # public-facing
├── docs/
│   └── spec.md                # full build brief — read this before coding
├── .claude/
│   └── settings.json          # enables mcp-server-dev plugin
├── package.json               # (build session)
├── tsconfig.json              # (build session)
└── src/
    ├── index.ts               # MCP server entry, stdio, registerAllTools()
    ├── droid/
    │   ├── exec.ts            # spawnDroidExec(args, opts) → parsed result
    │   ├── flags.ts           # typed object → CLI argv
    │   ├── output.ts          # stream-json event parser
    │   ├── sessions.ts        # read sessions-index.json
    │   ├── missions.ts        # read ~/.factory/missions/<id>/
    │   ├── profiles.ts        # enumerate ~/.factory/droids/*.md
    │   └── models.ts          # parse settings.json customModels[]
    ├── tools/
    │   ├── exec.ts            # droid_exec
    │   ├── presets.ts         # droid_research, droid_review_code, …
    │   ├── missions.ts        # droid_mission_*
    │   ├── sessions.ts        # droid_session_*
    │   ├── spec.ts            # droid_spec
    │   └── meta.ts            # droid_list_*
    ├── schemas/               # zod schemas, one per tool
    └── utils/
        ├── cwd.ts             # resolve cwd: param > process.cwd()
        ├── encode.ts          # /Users/serkan/X → -Users-serkan-X
        └── errors.ts          # createErrorResponse
```

## Quick Commands

```bash
npm install                     # install deps
npm run build                   # tsc → dist/
npm run dev                     # tsx src/index.ts (stdio loopback for testing)
npm start                       # node dist/index.js

# Register with Claude Code (after build)
claude mcp add mcp-do -- node /Users/serkan/mcp-do/dist/index.js
```

## How Droid Is Invoked

Every tool call ends in `child_process.spawn("droid", ["exec", ...flags, prompt], { cwd, env })`.

- **cwd**: tool-param `cwd` if given, else `process.cwd()` (= caller's project)
- **env**: pass through `process.env` so `FACTORY_API_KEY` (and droid's
  `~/.factory/auth.v2.file` fallback) just work
- **output**: `--output-format stream-json` always. Parse the JSONL stream:
  - first event has `session_id` → capture for chaining
  - tool-use / tool-result events → can be summarized in the response
  - error events inside the stream → treat as failure even if exit code is 0
- **failure**: any non-zero exit OR any error event inside the stream →
  return `{ isError: true, content: [{ type: "text", text: <stderr or last error event> }] }`

## Tool Surface (planned)

Full schemas and behaviour live in [`docs/spec.md`](docs/spec.md). Summary:

**Generic / power-user**

- `droid_exec` — every droid-exec flag exposed as a typed param
- `droid_list_tools` — `droid exec --list-tools --output-format json`
- `droid_list_models` — parse `~/.factory/settings.json` `customModels[]` + built-ins
- `droid_list_profiles` — scan `~/.factory/droids/*.md` and `<cwd>/.factory/droids/*.md`

**Specialized presets** — one per droid profile, each is a thin wrapper over
`droid_exec` with a preset model + `--append-system-prompt-file`

- `droid_research` (deep-researcher.md, default `custom:BYOK-GLM-5-Turbo-33`, `--auto high`)
- `droid_research_fast` (deep-researcher.md, default `custom:MiniMax-M2.7`)
- `droid_review_code` (code-reviewer.md)
- `droid_explore_code` (code-explorer.md)
- `droid_architect` (code-architect.md, default `custom:BYOK-GLM-5.1-31`)
- `droid_simplify` (code-simplifier.md, `--auto low`)
- `droid_silent_failure_scan` (silent-failure-hunter.md)
- `droid_pr_test_analyzer` (pr-test-analyzer.md)
- `droid_type_design_analyzer` (type-design-analyzer.md)
- `droid_scrutiny_review` (scrutiny-feature-reviewer.md)
- `droid_user_testing_validator` (user-testing-flow-validator.md)

**Missions** — read disk + invoke CLI

- `droid_mission_start` — `droid exec --mission --auto high "..."`, capture mission_id
- `droid_mission_list` — walk `~/.factory/missions/<uuid>/state.json`, filter by cwd
- `droid_mission_status` — read state.json + tail progress_log.jsonl
- `droid_mission_progress` — tail progress_log.jsonl from offset, filter event types
- `droid_mission_cancel` — SIGTERM `currentWorkerPid` (TBD: verify semantics)

**Sessions**

- `droid_session_continue` — `droid exec -s <id> "..."`
- `droid_session_fork` — `droid exec --fork <id> "..."`
- `droid_session_list` — filter `~/.factory/sessions-index.json` by encoded cwd
- `droid_session_search` — wraps `droid search <query> --json`

**Spec mode**

- `droid_spec` — `droid exec --use-spec --spec-model <m> "..."`

## Available Droid Profiles

Located in `~/.factory/droids/` (project-local override at `<cwd>/.factory/droids/`):

| Profile | Purpose |
|---|---|
| `code-architect.md` | High-level architecture analysis |
| `code-explorer.md` | Codebase navigation / feature lookup |
| `code-reviewer.md` | Code review with structured feedback |
| `code-simplifier.md` | Refactor toward simpler code |
| `deep-researcher.md` | Web research with parallel search |
| `pr-test-analyzer.md` | Analyze PR test coverage |
| `scrutiny-feature-reviewer.md` | Detailed feature review |
| `silent-failure-hunter.md` | Find silent error swallows |
| `type-design-analyzer.md` | TypeScript type design review |
| `user-testing-flow-validator.md` | Validate user-facing flows |
| `worker.md` | Generic mission worker |

## Available Models

Built-in (from `droid exec --help`):

- `claude-opus-4-6` (default), `claude-opus-4-6-fast`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- `gpt-5.2`, `gpt-5.2-codex`, `gpt-5.4`, `gpt-5.4-fast`, `gpt-5.4-mini`, `gpt-5.3-codex`
- `gemini-3.1-pro-preview`, `gemini-3-flash-preview`
- `glm-5`, `kimi-k2.5`, `minimax-m2.5`

Custom (from `~/.factory/settings.json` `customModels[]`):

| Short form (preferred) | Canonical id | Notes |
|---|---|---|
| `custom:glm-5-turbo` | `custom:BYOK-GLM-5-Turbo-33` | Default for research / review presets |
| `custom:glm-5.1` | `custom:BYOK-GLM-5.1-31` | Slow but deepest analysis; default for `droid_architect` |
| `custom:glm-5` | `custom:BYOK-GLM-5-32` | |
| `custom:MiniMax-M2.7` | `custom:BYOK-MiniMax-M2.7-30` | Fastest; smoke tests and non-tool-calling batch work |
| `custom:gpt-5.4-mini` | `custom:VP-GPT-5.4-Mini-48` | VP; cross-review default |
| `custom:qwen-3.6-coder` | `custom:VP-Qwen3.6-Plus-Coder-5` | VP |
| `custom:gpt-5.4` | `custom:VP-GPT-5.4-15` | VP |
| `custom:VP-Opus-4.6-1M-xHigh-44` | (same) | Session default in droid itself |

**Verified during planning**: droid accepts **both** short and canonical forms
for BYOK custom models (`droid exec --model custom:glm-5-turbo --list-tools`
and `droid exec --model custom:BYOK-GLM-5-Turbo-33 --list-tools` produce
identical output). Presets should use the short form for readability; no alias
map required at runtime.

## CWD Inheritance — The Whole Point

When Claude Code in `/Users/serkan/nt-dev` spawns this MCP via stdio, the
server process inherits cwd `/Users/serkan/nt-dev`. Every droid tool call
defaults to that cwd. This means:

- `droid exec` runs as if invoked from inside nt-dev — picks up nt-dev's
  `.factory/` (if present), respects nt-dev's git context
- `droid_session_list` returns sessions from
  `~/.factory/sessions/-Users-serkan-nt-dev/` only (cwd → encoded path)
- `droid_mission_list` returns missions whose `state.json#workingDirectory ==
  "/Users/serkan/nt-dev"` only

Every tool also accepts an optional `cwd` parameter to override. Pass `all=true`
to mission/session list tools to ignore cwd filtering.

## Build Instructions for the Next Session

1. **Read [`docs/spec.md`](docs/spec.md)** — it's the full build brief
2. Use `superpowers:writing-plans` to convert the spec into an implementation plan
3. Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development`)
   to execute it
4. Suggested order: scaffold → `droid/exec.ts` → `droid_exec` tool → register +
   smoke test → mission/session readers → preset tools → polish
5. Use `superpowers:test-driven-development` for the parser modules
   (`droid/output.ts`, `droid/missions.ts`, `droid/sessions.ts`) — they're
   pure functions, easy to test against fixture files copied from `~/.factory/`
6. Use `superpowers:verification-before-completion` before claiming any tool works
   — actually call it from a registered Claude Code session

## Token-Saving Rule (inherited from `~/CLAUDE.md`)

**ALL web research MUST go through droid headless mode.** Even when working on
this very project. Never run Research Powerpack or Context7 MCP tools directly
in main context — they produce 10k–30k+ tokens per call.

```bash
# Research (default model)
droid exec --model "custom:glm-5-turbo" --auto high \
  --append-system-prompt-file ~/.factory/droids/deep-researcher.md \
  --output-format text "your research question here"

# Run via Bash tool with run_in_background: true
```

Once `mcp-do` is built, this becomes `droid_research({ prompt: "..." })`
instead.

## Skills & Slash Commands

### MCP server development
- `mcp-server-dev:build-mcp-server` — primary skill for this project
- `mcp-server-dev:build-mcpb` — bundle for distribution (later)

### Workflow (superpowers)
- `superpowers:brainstorming` — explore intent before adding features
- `superpowers:writing-plans` — turn spec into implementation plan
- `superpowers:executing-plans` — execute with review checkpoints
- `superpowers:subagent-driven-development` — parallelize independent tasks
- `superpowers:test-driven-development` — TDD the parser modules
- `superpowers:systematic-debugging` — for stream-json parsing issues
- `superpowers:verification-before-completion` — verify with real droid calls
- `superpowers:requesting-code-review` — before declaring done
- `superpowers:finishing-a-development-branch` — merge / cleanup
- `/commit` — multi-commit with auto-push

### Research (MUST go through droid)
- `droid exec --append-system-prompt-file ~/.factory/droids/deep-researcher.md`
  (or `droid_research` once built)
