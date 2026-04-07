# mcp-droid — Build Spec

> **Audience**: a future Claude Code session that will implement this MCP server.
> Read this file end-to-end before writing any code. Every architectural decision
> already has a justification in the plan; do not re-derive them, but DO verify
> the items flagged "build session must verify".

## 1. Goal

Local **stdio MCP server** that exposes the Factory AI `droid` CLI as a typed
tool surface inside Claude Code (and any other MCP client). Wraps `droid exec`
via `child_process.spawn`, surfaces missions and sessions by reading
`~/.factory/`, and inherits the caller's `cwd` so it works seamlessly across
sibling projects.

## 1a. Planning-time verifications (already resolved)

Items in this spec that the planning session verified live against the local
droid install so the build session does NOT need to re-investigate:

- ✅ **Model alias forms** — both `custom:glm-5-turbo` and
  `custom:BYOK-GLM-5-Turbo-33` work; same for MiniMax. Section 10.
- ✅ **`sessions-index.json` shape** — `{version, entries: [{sessionId, mtime,
  settingsMtime, title, cwd, messagesCount}]}`. 142 entries in the live file.
  Section 6.4.
- ✅ **Stream-json success event shapes** — `system.init`, `message`,
  `reasoning`, `completion`. Fixture captured at
  `docs/fixtures/stream-json-hello.jsonl`. Section 7.
- ✅ **`droid exec` flag inventory** — complete flag list captured from
  `droid exec --help`; reflected in `droid_exec` input schema (Section 6.1).
- ✅ **Mission on-disk layout** — `state.json`, `mission.md`, `features.json`,
  `progress_log.jsonl`, `handoffs/`, `evidence/`. Sample shapes in Section 6.3.
- ✅ **`cwd` stored as raw absolute path** in both sessions-index and mission
  state.json — no decoding needed for filtering. Section 8.

Items still deferred to build time (each one annotated inline where relevant):

- ⏳ Stream-json **error** event shape (success fixture exists, error fixture needed)
- ⏳ Whether `droid exec --mission` stream-json init event carries `mission_id`
  directly, vs polling `~/.factory/missions/` for the newest dir
- ⏳ `droid_mission_cancel` semantics — likely skip in v1
- ⏳ Whether `sessions-index.json#messagesCount` counts user turns or all turns

## 2. Non-Goals (v1)

- **No HTTP transport.** stdio only. (gtm-mcp / meta-mcp use HTTP for multi-tenant
  remote use; this MCP is the inverse — local, single-user, wraps a local CLI.)
- **No auth shim.** `FACTORY_API_KEY` is read from `process.env`; if missing,
  droid falls back to `~/.factory/auth.v2.file` from a prior `droid login`. Done.
- **No SDK vendoring.** The official `@factory/droid-sdk` (TypeScript) lives at
  the sibling clone `/Users/serkan/droid-sdk-typescript` — reference only, never
  imported. v2 may revisit this if streaming progress notifications are needed.
- **No custom UI / widgets** (no `mcp-server-dev:build-mcp-app`). Plain text/JSON
  responses.
- **No hook management.** Droid hooks live in `~/.factory/settings.json` (`hooks`
  key) and `~/.factory/hooks/hooks.json`. The MCP does not read or write them.
- **No model alias UI.** A static friendly→long alias map is fine; no dynamic
  registry.

## 3. Constraints

- Must work with `droid` CLI ≥ **0.95.0** (current installed version)
- Must not require any droid modification or wrapper script
- Must inherit `cwd` from the parent process by default
- Must default to **safe / read-only** — no implicit `--auto` flag unless the
  tool's preset documents it
- Must never throw across the MCP boundary — wrap every subprocess + every fs
  read in try/catch and return `{ isError: true, content: [...] }` on failure
- Must default to `--output-format stream-json` (plain `json` is unsafe — exit
  code 0 does not imply success; errors live in stream events)

## 4. Architecture

```
Claude Code (project X) ──spawns──▶ mcp-droid stdio server
                                          │
                                          │ child_process.spawn("droid", ["exec", ...flags, prompt],
                                          │                     { cwd, env: process.env })
                                          ▼
                                      droid exec
                                          │
                  ┌───────────────────────┼────────────────────────┐
                  ▼                       ▼                        ▼
        ~/.factory/sessions/      ~/.factory/missions/      ~/.factory/droids/
        ~/.factory/sessions-      ~/.factory/settings.json  <cwd>/.factory/  (project local)
            index.json
                                          │
                                          ▼
                                  /Users/serkan/X/   (cwd inherited from caller)
```

The server has two data sources:

1. **Subprocess output** from `droid exec` (parsed as stream-json)
2. **Direct filesystem reads** of `~/.factory/{sessions-index.json, missions/<uuid>/*, droids/*.md, settings.json}`

Tools are split accordingly: some shell out, some just read files, some do both.

## 5. Project Structure

```
mcp-droid/
├── package.json
├── tsconfig.json
├── .eslintrc.json              # optional, mirror gtm-mcp's config
├── src/
│   ├── index.ts                # MCP server entry, stdio transport, registerAllTools()
│   ├── droid/                  # everything that talks to droid / ~/.factory/
│   │   ├── exec.ts             # spawnDroidExec(args, opts) → ParsedDroidResult
│   │   ├── flags.ts            # FlagBuilder: typed object → CLI argv array
│   │   ├── output.ts           # stream-json event parser
│   │   ├── sessions.ts         # listSessionsForCwd(cwd), getSession(id)
│   │   ├── missions.ts         # listMissions({cwd}), getMissionStatus(id), tailProgress(id, opts)
│   │   ├── profiles.ts         # listProfiles({cwd}), getProfile(name)
│   │   └── models.ts           # listModels(), resolveAlias(name)
│   ├── tools/                  # one file per logical group
│   │   ├── index.ts            # registerAllTools(server)
│   │   ├── exec.ts             # droid_exec
│   │   ├── presets.ts          # droid_research, droid_review_code, droid_explore_code, ...
│   │   ├── missions.ts         # droid_mission_*
│   │   ├── sessions.ts         # droid_session_*
│   │   ├── spec.ts             # droid_spec
│   │   └── meta.ts             # droid_list_tools / _list_models / _list_profiles
│   ├── schemas/                # zod schemas, one per tool
│   │   ├── exec.ts
│   │   ├── presets.ts
│   │   ├── missions.ts
│   │   ├── sessions.ts
│   │   ├── spec.ts
│   │   └── meta.ts
│   └── utils/
│       ├── cwd.ts              # resolveCwd(toolParam) → string
│       ├── encode.ts           # encodeCwdToSessionsKey("/Users/serkan/X") → "-Users-serkan-X"
│       ├── errors.ts           # createErrorResponse(stderr|err) → {isError:true, content:[...]}
│       └── json.ts             # safeJsonParse, jsonlSplit
├── docs/
│   └── spec.md                 # this file
└── dist/                       # build output (gitignored)
```

## 6. Tool Surface (full)

Every tool returns the standard MCP shape:

```typescript
{ content: [{ type: "text", text: <serialized JSON or human text> }] }
```

On error:

```typescript
{ isError: true, content: [{ type: "text", text: "..." }] }
```

### 6.1 Generic / power-user

#### `droid_exec`

Maps to `droid exec [flags] <prompt>`. Every flag supported.

**Input schema (zod):**

```typescript
{
  prompt?: string,                       // mutually exclusive with prompt_file
  prompt_file?: string,                  // → -f <path>
  model?: string,                        // → -m <id>; accepts friendly alias or full id
  auto?: "low" | "medium" | "high",      // → --auto <level>; omit = read-only default
  allow_unsafe?: boolean,                // → --skip-permissions-unsafe (cannot combine with auto)
  output_format?: "text" | "json" | "stream-json",  // default: "stream-json"
  input_format?: "text" | "stream-json",
  session_id?: string,                   // → -s <id>
  fork_session_id?: string,              // → --fork <id>
  cwd?: string,                          // → --cwd <path>; default: process.cwd()
  worktree?: string | true,              // → -w [name]
  worktree_dir?: string,                 // → --worktree-dir <path>
  enabled_tools?: string[],              // → --enabled-tools <comma-list>
  disabled_tools?: string[],             // → --disabled-tools <comma-list>
  tags?: (string | { name: string; metadata?: Record<string, unknown> })[],  // → repeated --tag <spec>
  log_group_id?: string,                 // → --log-group-id <id>
  mission?: boolean,                     // → --mission (requires auto: "high" or allow_unsafe)
  system_prompt?: string,                // → --append-system-prompt <text>
  system_prompt_file?: string,           // → --append-system-prompt-file <path>
  reasoning_effort?: "off" | "low" | "medium" | "high" | "max" | "xhigh" | "minimal" | "none",
  spec_model?: string,                   // → --spec-model <id>
  spec_reasoning_effort?: string,        // → --spec-reasoning-effort <level>
  use_spec?: boolean,                    // → --use-spec
  settings_file?: string,                // → --settings <path>; per-process settings override
  list_tools?: boolean,                  // → --list-tools and exit
  timeout_ms?: number,                   // server-side spawn timeout, default 600_000
}
```

**Behaviour:**

- Build argv via `FlagBuilder`. Validate mutual exclusions
  (`prompt` vs `prompt_file`, `auto` vs `allow_unsafe`, `mission` requires
  `auto: "high"` or `allow_unsafe`).
- Spawn `droid exec ...argv` with `cwd` and `env: process.env`.
- Parse output:
  - `stream-json` (default): split JSONL, scan events for `session_id` (init
    event), `error`, `usage`, final `text`/`assistant_message`. Fail if any
    error event seen, EVEN if exit code is 0.
  - `json`: try `JSON.parse` on stdout. Fall back to raw text.
  - `text`: return as-is.
- Return:
  ```json
  {
    "session_id": "<from init event>",
    "model": "<from init event>",
    "text": "<final assistant message>",
    "events": [/* optional summarized event list */],
    "usage": { "input_tokens": ..., "output_tokens": ..., "cost_usd": ... },
    "exit_code": 0,
    "duration_ms": 1234
  }
  ```
- Default `timeout_ms` is 10 minutes; configurable per call.

#### `droid_list_tools`

Maps to `droid exec --model <m> --list-tools --output-format json`. Returns the
parsed tool list. Defaults `model` to droid's session default (`custom:VP-Opus-4.6-1M-xHigh-44`
per `~/.factory/settings.json`), overridable.

#### `droid_list_models`

Reads `~/.factory/settings.json` `customModels[]` array and merges with the
hard-coded built-in list (extracted from `droid exec --help`; keep this list in
`src/droid/models.ts` as a constant — refresh it when droid's --help output
changes). Returns:

```json
[
  { "id": "claude-opus-4-6", "displayName": "Claude Opus 4.6", "kind": "builtin", "supports_reasoning": true, "default_reasoning": "high" },
  { "id": "custom:BYOK-GLM-5-Turbo-33", "displayName": "BYOK: GLM-5-Turbo", "alias": "glm-5-turbo", "kind": "custom", "provider": "anthropic" },
  ...
]
```

#### `droid_list_profiles`

Scans `~/.factory/droids/*.md` plus `<cwd>/.factory/droids/*.md` (project-local
override). Parses front-matter (`---` block at top, YAML). Returns:

```json
[
  { "name": "deep-researcher", "scope": "global", "path": "/Users/serkan/.factory/droids/deep-researcher.md", "description": "Autonomous research powerhouse...", "model": "inherit", "tools": ["Read", "Grep", ...] },
  ...
]
```

### 6.2 Specialized presets

Each preset is a thin wrapper over `droid_exec`. Internally, the preset calls
the same `spawnDroidExec` helper with a fixed `--append-system-prompt-file` path
and a default model. The user can still override `model`, `auto`, `cwd`, `tags`,
`session_id`, and `reasoning_effort` at call time.

| Tool | Profile file | Default model | Default `--auto` |
|---|---|---|---|
| `droid_research` | `~/.factory/droids/deep-researcher.md` | `custom:BYOK-GLM-5-Turbo-33` | `high` |
| `droid_research_fast` | `~/.factory/droids/deep-researcher.md` | `custom:BYOK-MiniMax-M2.7-30` | `high` |
| `droid_review_code` | `~/.factory/droids/code-reviewer.md` | `custom:BYOK-GLM-5-Turbo-33` | (none — read-only) |
| `droid_explore_code` | `~/.factory/droids/code-explorer.md` | `custom:BYOK-GLM-5-Turbo-33` | (none) |
| `droid_architect` | `~/.factory/droids/code-architect.md` | `custom:BYOK-GLM-5.1-31` | (none) |
| `droid_simplify` | `~/.factory/droids/code-simplifier.md` | `custom:BYOK-GLM-5-Turbo-33` | `low` |
| `droid_silent_failure_scan` | `~/.factory/droids/silent-failure-hunter.md` | `custom:BYOK-GLM-5-Turbo-33` | (none) |
| `droid_pr_test_analyzer` | `~/.factory/droids/pr-test-analyzer.md` | `custom:BYOK-GLM-5-Turbo-33` | (none) |
| `droid_type_design_analyzer` | `~/.factory/droids/type-design-analyzer.md` | `custom:BYOK-GLM-5-Turbo-33` | (none) |
| `droid_scrutiny_review` | `~/.factory/droids/scrutiny-feature-reviewer.md` | `custom:BYOK-GLM-5-Turbo-33` | (none) |
| `droid_user_testing_validator` | `~/.factory/droids/user-testing-flow-validator.md` | `custom:BYOK-GLM-5-Turbo-33` | (none) |

**Common preset input schema:**

```typescript
{
  prompt: string,
  cwd?: string,
  model?: string,             // override default
  auto?: "low" | "medium" | "high",  // override default
  reasoning_effort?: string,
  session_id?: string,
  tags?: (string | { name: string; metadata?: Record<string, unknown> })[],
  timeout_ms?: number,
}
```

If a preset's profile file is missing on disk, the tool returns `isError` with
"profile not found at `<path>`" — do not silently fall back.

### 6.3 Missions

Mission state is stored on disk per mission:

```
~/.factory/missions/<uuid>/
├── state.json              # high-level: state, completedFeatures, totalFeatures, workingDirectory, currentWorkerSessionId, currentWorkerPid, ...
├── mission.md              # original mission prompt
├── features.json           # feature breakdown
├── progress_log.jsonl      # event stream (mission_accepted, worker_started, worker_completed, mission_paused, ...)
├── model-settings.json     # worker / validator model overrides
├── handoffs/               # per-feature handoff payloads
└── evidence/               # optional evidence artifacts
```

Verified `state.json` shape (from `/Users/serkan/.factory/missions/10efd7ee-.../state.json`):

```json
{
  "missionId": "mis_4dda2f93",
  "baseSessionId": "10efd7ee-42c2-49d6-ac80-fdd3cddf3b22",
  "state": "paused",
  "workingDirectory": "/Users/serkan/nt-dev",
  "currentFeatureId": null,
  "currentWorkerSessionId": null,
  "currentWorkerPid": null,
  "workerSessionIds": [],
  "completedFeatures": 0,
  "totalFeatures": 5,
  "createdAt": "2026-03-29T22:52:13.272Z",
  "updatedAt": "2026-03-29T22:54:32.344Z"
}
```

Verified `progress_log.jsonl` event types: `mission_accepted`, `mission_run_started`,
`worker_failed`, `mission_paused`, `mission_resumed`, `worker_selected_feature`,
`worker_started`, `worker_completed`. The `worker_completed` events have a giant
`handoff` field (10KB+) — the MCP must summarize or omit it by default.

#### `droid_mission_start`

**Input:**

```typescript
{
  prompt: string,
  cwd?: string,
  model?: string,                    // default: read from ~/.factory/settings.json missionModelSettings.workerModel
  worker_model?: string,
  validation_worker_model?: string,
  allow_unsafe?: boolean,            // → --skip-permissions-unsafe (alternative to --auto high)
  tags?: (string | { name: string; metadata?: Record<string, unknown> })[],
  detached?: boolean,                // default true — return immediately with mission_id
}
```

**Behaviour:** spawns `droid exec --mission --auto high [--model <m>] "<prompt>"`
in the given cwd. The challenge is capturing the new mission_id without blocking
on completion (missions can run for hours).

**Build session must verify** which approach works:

1. Use `--output-format stream-json` and read events until you see one with
   `mission_id` (likely the init event), then either
   - Detach the child (let it keep running) and return mission_id
   - Or keep streaming and return periodically — but this blocks the MCP request,
     bad for long missions
2. Spawn detached, `setTimeout` 2–5s, then scan `~/.factory/missions/` for
   directories created in the last 10s with `workingDirectory == cwd` and pick
   the newest. Less reliable but doesn't depend on stream parsing.

Prefer (1). Fall back to (2) if the stream-json init event doesn't carry
mission_id. Document findings in CLAUDE.md once verified.

**Output:**

```json
{
  "mission_id": "mis_xxx",
  "base_session_id": "<uuid>",
  "working_directory": "<cwd>",
  "started_at": "<iso>",
  "state_file": "/Users/serkan/.factory/missions/<uuid>/state.json"
}
```

#### `droid_mission_list`

**Input:**

```typescript
{
  cwd?: string,        // default: process.cwd()
  all?: boolean,       // default: false; if true, ignore cwd filter
  state?: string,      // optional filter: "running" | "paused" | "completed" | "failed" | ...
  limit?: number,      // default 50
}
```

**Behaviour:** read every directory under `~/.factory/missions/`, parse each
`state.json`, filter by `workingDirectory == cwd` (unless `all=true`), filter by
`state` (if given), sort by `updatedAt` desc, return top `limit`.

**Output:**

```json
[
  {
    "mission_id": "mis_xxx",
    "uuid": "<dir name>",
    "state": "paused",
    "completed_features": 0,
    "total_features": 5,
    "working_directory": "/Users/serkan/nt-dev",
    "created_at": "...",
    "updated_at": "...",
    "title": "<first line of mission.md, optional>"
  },
  ...
]
```

#### `droid_mission_status`

**Input:**

```typescript
{
  mission_id: string,        // accepts either "mis_xxx" or the directory uuid
  include_progress?: boolean,// default true
  progress_limit?: number,   // default 20 events
  include_handoffs?: boolean,// default false (handoffs are huge)
  include_features?: boolean,// default true
}
```

**Behaviour:** resolve `mission_id` to a directory under `~/.factory/missions/`
(scan dirs, match `state.json#missionId` or use uuid directly). Read
`state.json`, optionally `features.json` (summary: count + names), optionally
tail last N events from `progress_log.jsonl`.

**Output:**

```json
{
  "mission_id": "mis_xxx",
  "uuid": "<dir>",
  "state": "...",
  "completed_features": 0,
  "total_features": 5,
  "current_worker_session_id": null,
  "current_worker_pid": null,
  "working_directory": "...",
  "created_at": "...",
  "updated_at": "...",
  "features": [{"id": "extract-shared-helpers", "name": "..."}, ...],
  "recent_events": [
    {"timestamp": "...", "type": "worker_completed", "feature_id": "...", "success_state": "success", "summary": "<handoff.salientSummary>"},
    ...
  ]
}
```

When `include_handoffs=false`, replace each `worker_completed.handoff` with
`{ summary: handoff.salientSummary, what_implemented: handoff.whatWasImplemented?.slice(0, 200) }`.

#### `droid_mission_progress`

**Input:**

```typescript
{
  mission_id: string,
  since_timestamp?: string,   // ISO; return events strictly after this
  since_offset?: number,      // alternative: line offset into progress_log.jsonl
  limit?: number,             // default 50
  event_types?: string[],     // filter
  exclude_handoffs?: boolean, // default true
}
```

**Behaviour:** tail-style read of `progress_log.jsonl`. Used for polling-based
"streaming" progress. Returns events plus the new offset/timestamp to use for
the next call.

**Output:**

```json
{
  "events": [...],
  "next_offset": 47,
  "next_timestamp": "2026-...",
  "is_complete": false
}
```

`is_complete = true` when the latest event is `mission_completed` or the state
file shows `state in ["completed", "failed", "cancelled"]`.

#### `droid_mission_cancel`

**Build session must verify behaviour first.** Possible approaches:

1. Read `state.json#currentWorkerPid`, send SIGTERM to it, hope droid handles
   the signal cleanly and updates state.json
2. Look for a `droid daemon` API to cancel — `droid daemon` is the factoryd
   server that spawns workers, may have an HTTP/Unix endpoint for cancellation
3. Manually edit `state.json` `state` field to `"cancelled"` (probably wrong
   — droid will overwrite)

**Recommendation**: skip in v1 and document as "not yet supported, kill the
worker pid manually". Re-investigate in v2.

### 6.4 Sessions

Sessions are stored in `~/.factory/sessions/<encoded-cwd>/<session-id>/...` and
indexed in `~/.factory/sessions-index.json` (35KB at last check). The encoded
cwd transforms `/Users/serkan/nt-dev` → `-Users-serkan-nt-dev` (leading `/`
becomes `-`, other `/` become `-`). See `src/utils/encode.ts`.

#### `droid_session_continue`

**Input:**

```typescript
{
  session_id: string,
  prompt: string,
  cwd?: string,
  model?: string,             // optional override
  auto?: "low" | "medium" | "high",
  // ...other droid_exec flags as appropriate
}
```

**Behaviour:** `droid exec -s <session_id> "<prompt>" [other flags]`. Returns
parsed result from `droid_exec`-style stream.

#### `droid_session_fork`

Same as continue, but uses `--fork <id>` instead of `-s <id>`. Creates a new
session that branches from the given checkpoint. Returns the new session_id
from the init event.

#### `droid_session_list`

**Input:**

```typescript
{
  cwd?: string,
  all?: boolean,
  limit?: number,        // default 50
  search?: string,       // optional substring filter on title
}
```

**Behaviour:** read `~/.factory/sessions-index.json`. **Verified shape** (planning
session captured this directly; 142 entries in the live file):

```json
{
  "version": 1,
  "entries": [
    {
      "sessionId": "669d6336-0764-467d-80c4-358c5502c51f",
      "mtime": 1775221044849,
      "settingsMtime": 1775221044889,
      "title": "New Session",
      "cwd": "/Users/serkan",
      "messagesCount": 4
    },
    ...
  ]
}
```

The `cwd` field is the **raw absolute path** — no encoding needed for filtering.
Filter with `entries.filter(e => e.cwd === resolvedCwd)` (unless `all=true`).
Sort by `mtime` desc. `mtime` is unix milliseconds. Do NOT use `encodeCwdToSessionsKey`
here — that encoding only applies to the on-disk session directory layout
(`~/.factory/sessions/-Users-serkan-nt-dev/`), not to this index.

**Still to verify during build**: whether `messagesCount` is the total turn count
or only user turns, and whether `title` gets updated after the session continues
or stays at "New Session" for untitled sessions.

#### `droid_session_search`

**Input:**

```typescript
{
  query: string,
  cwd?: string,
  kind?: "message_text" | "document" | "tool_use" | "tool_result" | "all",   // default "all"
  limit_sessions?: number,    // default 20
  limit_hits?: number,        // default 3
  context_chars?: number,     // default 80
  reindex?: boolean,          // default false
}
```

**Behaviour:** wrap `droid search <query> --json [--kind ...] [--limit-sessions N] [--limit-hits M] [--context-chars C] [--reindex]`.
Spawn in the given `cwd`. Parse stdout as JSON. Return as-is (or with light
normalization).

### 6.5 Spec mode

#### `droid_spec`

**Input:**

```typescript
{
  prompt: string,
  cwd?: string,
  spec_model?: string,             // → --spec-model <id>
  spec_reasoning_effort?: string,  // → --spec-reasoning-effort <level>
  model?: string,                  // → --model <id> (main model, used outside spec)
}
```

**Behaviour:** `droid exec --use-spec [--spec-model <m>] [--spec-reasoning-effort <r>] [--model <m>] "<prompt>"`.
Returns the parsed spec output.

## 7. Output Format Handling

**Default to `--output-format stream-json` everywhere.** Plain `json` is unsafe
because exit code 0 does not imply success — errors can appear inside the JSON
payload. `text` is fine when the caller explicitly asks for it.

### Stream-JSON parser (`src/droid/output.ts`)

**Verified event shapes** (captured live during planning, fixture at
[`docs/fixtures/stream-json-hello.jsonl`](fixtures/stream-json-hello.jsonl)
— a real 5-event run of `droid exec --model custom:BYOK-MiniMax-M2.7-30
--output-format stream-json "reply with exactly: hi"`):

| `type` | `subtype` | Fields | Notes |
|---|---|---|---|
| `system` | `init` | `cwd`, `session_id`, `tools[]`, `model`, `reasoning_effort` | **First event. Capture `session_id` here for continuation chaining.** `tools[]` is the full list available to the model for this run. |
| `message` | — | `role: "user"\|"assistant"`, `id`, `text`, `timestamp`, `session_id` | Turn messages. User turn is echoed back first. |
| `reasoning` | — | `id`, `text`, `timestamp`, `session_id` | Model's internal thinking trace (when reasoning effort > none). |
| `completion` | — | `finalText`, `numTurns`, `durationMs`, `session_id`, `timestamp`, `usage: {input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens, thinking_tokens}` | **Final event. `finalText` is canonical — prefer over concatenating assistant messages.** `usage` has no `cost_usd`; compute it from token counts + model pricing if needed. |

Pure function:

```typescript
function parseStreamJson(stdout: string): {
  session_id?: string,
  model?: string,
  cwd?: string,
  events: DroidEvent[],
  text: string,             // completion.finalText, fallback: concatenated assistant messages
  usage?: {
    input_tokens?: number,
    output_tokens?: number,
    cache_read_input_tokens?: number,
    cache_creation_input_tokens?: number,
    thinking_tokens?: number,
  },
  num_turns?: number,
  duration_ms?: number,
  errors: DroidEvent[],
}
```

- Split stdout by newlines, parse each line as JSON, ignore blank lines
- `system.init` event → capture `session_id`, `model`, `cwd`
- `completion` event → capture `finalText` into `text`, `usage`, `numTurns`, `durationMs`
- Unknown event types → include in `events[]` but don't fail the parse
- Collect any event matching `/error|failed/i` in its type into `errors[]`
- **If `errors[]` is non-empty, treat the call as failed** even if exit code 0

**Build session must still verify**: the shape of **error events**. The
verified fixture is a success case. Run a forced failure (e.g. invalid model
id or blocked tool) and capture a second fixture at
`docs/fixtures/stream-json-error.jsonl` to drive the error-path tests.

### JSON parser (fallback)

For tools where the user explicitly requests `output_format: "json"`. Use
`safeJsonParse(stdout)`. If parse fails, fall back to text.

### Text passthrough

Just return stdout as a string in `content[0].text`.

## 8. CWD Resolution

Every tool accepts an optional `cwd` parameter. Resolution order:

1. Tool parameter `cwd` (must be absolute, or resolve via `path.resolve(process.cwd(), cwd)`)
2. `process.cwd()`

### Filtering rules (verified)

Both the **sessions index** and **mission state files** store `cwd` as the
**raw absolute path**. Filter with direct string equality:

```typescript
// sessions-index.json → entries[i].cwd === resolvedCwd
// ~/.factory/missions/<uuid>/state.json → workingDirectory === resolvedCwd
```

No path encoding needed for filtering.

### Encoded form (storage layout only)

The on-disk sessions directory uses an encoded path key:

```typescript
function encodeCwdToSessionsKey(absCwd: string): string {
  // /Users/serkan/nt-dev → -Users-serkan-nt-dev
  return absCwd.replace(/^\//, "-").replace(/\//g, "-");
}
```

This only matters if the MCP ever needs to walk the on-disk session directory
directly (e.g. to find per-session log files). `droid_session_list` does NOT
need this — it uses the index. Keep the helper in `src/utils/encode.ts` for
when it's actually needed.

### `--cwd` flag

`droid exec` itself receives `--cwd <absCwd>` only if the tool param differed
from `process.cwd()`. If they match, omit the flag (let droid use its own
default, which honors process cwd).

## 9. Error Handling

- Wrap `spawnDroidExec` in try/catch and a Promise that resolves on exit
- If exit code ≠ 0 → `{ isError: true, content: [{ type: "text", text: stderr || \`droid exec exited with ${code}\` }] }`
- If stream-json parser found `errors[]` → `{ isError: true, content: [{ type: "text", text: errors.map(...).join("\n") }] }`
- If a fs read fails (mission state, sessions index) → `{ isError: true, content: [{ type: "text", text: \`failed to read \${path}: \${err.message}\` }] }`
- Never let an exception propagate to the MCP transport

## 10. Model Alias Resolution

**RESOLVED during planning.** Droid accepts **both** the friendly form
(`custom:glm-5-turbo`, `custom:MiniMax-M2.7`) and the long form
(`custom:BYOK-GLM-5-Turbo-33`, `custom:BYOK-MiniMax-M2.7-30`). Verified via:

```bash
droid exec --model custom:glm-5-turbo --list-tools         # ✓ works (shows "BYOK: GLM-5-Turbo")
droid exec --model custom:BYOK-GLM-5-Turbo-33 --list-tools # ✓ works (identical output)
droid exec --model custom:MiniMax-M2.7 --list-tools        # ✓ works
droid exec --model custom:BYOK-MiniMax-M2.7-30 --list-tools # ✓ works
```

`~/.factory/settings.json` `customModels[]` has the canonical ids:

| `id` field | Short alias droid accepts | `displayName` |
|---|---|---|
| `custom:BYOK-MiniMax-M2.7-30` | `custom:MiniMax-M2.7` | BYOK: MiniMax M2.7 |
| `custom:BYOK-GLM-5-Turbo-33` | `custom:glm-5-turbo` | BYOK: GLM-5-Turbo |
| `custom:BYOK-GLM-5.1-31` | `custom:glm-5.1` | BYOK: GLM-5.1 |
| `custom:BYOK-GLM-5-32` | `custom:glm-5` | BYOK: GLM-5 |

**Implication for the build:** no alias map is strictly required — the MCP can
pass through whatever the caller provides. Presets in `src/tools/presets.ts`
should use the **short form** in their defaults (e.g.
`model: "custom:glm-5-turbo"`) because it matches the user's `~/CLAUDE.md`
convention and is easier to read in tool signatures. Document this in
CLAUDE.md.

(Optional: `src/droid/models.ts` can still expose `listModels()` that enriches
each custom model with both its `id` and any detected short alias, for use in
`droid_list_models`. But runtime resolution is a no-op.)

## 11. Authentication

- Read `FACTORY_API_KEY` from `process.env`. If present, pass through to droid
  via the inherited env. No transformation.
- If absent, droid will read its own login state from `~/.factory/auth.v2.file`
  (set up by `droid login`). This is fine — the MCP does not need to detect or
  re-auth.
- **Do not** log `FACTORY_API_KEY` anywhere. Do not include it in tool responses.
- **Do not** strip env when spawning — droid needs other env vars too (PATH,
  HOME, etc).

## 12. Hooks

Out of scope for v1. Documented for completeness so the build session does not
go down a rabbit hole:

- Droid hooks live in `~/.factory/settings.json` `hooks` key (and a duplicate
  copy in `~/.factory/hooks/hooks.json`)
- Event types observed: `UserPromptSubmit`, `Notification`, `Stop`, `PostToolUse`
- Hook entries: `{ matcher?: string, hooks: [{ type: "command", command: "..." }] }`
- The MCP could expose `droid_list_hooks` and `droid_run_with_settings_override`
  in v2 (using the `--settings <path>` flag to pass a per-process settings file)
- For v1: no hook tools, no settings overrides

## 13. Acceptance Criteria

The build is "done" when all of the following work end-to-end from a registered
Claude Code MCP client:

- [ ] `npm run build` produces `dist/index.js` with zero TypeScript errors and
      zero ESLint errors
- [ ] `claude mcp add mcp-droid -- node /Users/serkan/mcp-droid/dist/index.js`
      registers the server successfully
- [ ] Calling `droid_list_models` returns ≥ 30 models (built-ins + customs)
- [ ] Calling `droid_list_profiles` returns 11+ profiles (the 11 in
      `~/.factory/droids/` plus any project-local ones)
- [ ] Calling `droid_research` with `prompt: "what is 2+2"` returns a parsed
      stream-json result with non-empty `text` and a captured `session_id`
- [ ] Calling `droid_session_continue` with that captured `session_id` and a
      follow-up prompt returns a result that demonstrates context preservation
- [ ] Calling `droid_mission_list` returns the 25+ existing missions on disk
- [ ] Calling `droid_mission_status` for one of the existing mission UUIDs
      returns the parsed `state.json` plus `recent_events`
- [ ] Calling `droid_session_search` with `query: "docuseal"` from cwd
      `/Users/serkan/nt-dev` returns hits from the nt-dev sessions
- [ ] Spawning the server with `cwd=/Users/serkan/nt-dev` and calling
      `droid_session_list` only returns nt-dev sessions, not pg-memory ones
- [ ] Calling any tool with a clearly broken input (missing required field)
      returns `{ isError: true, content: [...] }` instead of crashing the server
- [ ] Calling `droid_exec` with `auto: "high"` and `mission: true` runs in
      mission mode without rejection

## 14. Build Sequencing (suggested)

Use `superpowers:writing-plans` to convert this into a real implementation
plan, then `superpowers:executing-plans`. Suggested phases:

### Phase 1: Scaffold
1. `npm init -y`, edit `package.json` (name, type: module, scripts, deps)
2. `npm install @modelcontextprotocol/sdk zod`
3. `npm install -D typescript tsx @types/node`
4. Copy `tsconfig.json` from `/Users/serkan/gtm-mcp/tsconfig.json` (ES2022, NodeNext, strict)
5. Create `src/index.ts` with a no-op MCP server that registers zero tools and
   listens on stdio. `npm run build` succeeds.

### Phase 2: Droid subprocess core
1. `src/droid/flags.ts` — pure function, typed object → argv[] (TDD against
   handcrafted fixtures)
2. `src/droid/output.ts` — pure stream-json parser (TDD against the existing
   success fixture at `docs/fixtures/stream-json-hello.jsonl`, plus a new
   error fixture you'll capture). Verified event shapes in section 7.
3. `src/droid/exec.ts` — `spawnDroidExec(args, opts)` async function. Smoke
   test against real droid: `droid exec --model custom:glm-5-turbo
   --output-format stream-json "say hi"`

### Phase 3: First MCP tool
1. `src/tools/exec.ts` — register `droid_exec`
2. `src/index.ts` — wire it up
3. `npm run build && claude mcp add mcp-droid -- node ./dist/index.js`
4. From a fresh Claude Code session: call `droid_exec({ prompt: "what is 2+2", auto: "high" })`
5. **Use `superpowers:verification-before-completion`**: do not claim the
   tool works until you actually invoke it from a real MCP client and see a
   sensible response

### Phase 4: Filesystem readers
1. `src/droid/sessions.ts` — read sessions-index.json, filter by encoded cwd
2. `src/droid/missions.ts` — walk missions dir, parse state.json + tail jsonl
3. `src/droid/profiles.ts` — scan droids dir, parse front-matter
4. `src/droid/models.ts` — read settings.json customModels[] + alias map
5. Each gets unit tests against fixtures copied from `~/.factory/`

### Phase 5: Remaining tools
1. `src/tools/missions.ts` — list, status, progress (start later, after stream-json verified)
2. `src/tools/sessions.ts` — list, search, continue, fork
3. `src/tools/presets.ts` — all 11 specialized presets
4. `src/tools/spec.ts` — droid_spec
5. `src/tools/meta.ts` — list_tools, list_models, list_profiles
6. **Verify the model alias question** (section 10) and update `models.ts` accordingly
7. **Verify mission_id capture approach** (section 6.3 `droid_mission_start`) and document

### Phase 6: Polish
1. Error handling audit — every tool wraps in try/catch + returns isError shape
2. README update with real install instructions and verified examples
3. Update CLAUDE.md "Status" section: "implemented through phase X"
4. `superpowers:requesting-code-review` before declaring done

## 15. External References

- **Factory docs**
  - https://docs.factory.ai/cli/droid-exec/overview
  - https://docs.factory.ai/cli/features/missions
  - https://docs.factory.ai/cli/configuration/mixed-models
  - https://docs.factory.ai/reference/cli-reference
  - https://docs.factory.ai/reference/hooks-reference
- **Factory GitHub**
  - https://github.com/Factory-AI/factory/tree/main/docs
  - https://github.com/Factory-AI/droid-sdk-typescript
- **Local droid SDK clone target**: `/Users/serkan/droid-sdk-typescript`
  (sibling clone, reference only — not vendored, not imported)
- **MCP SDK docs**: use Context7 (`mcp__claude_ai_Context7__resolve-library-id`
  → `query-docs`) — but ONLY through droid headless per the global token-saving
  rule, never directly in main context
- **Reference MCP projects to mirror**
  - `/Users/serkan/gtm-mcp/` (CLAUDE.md style, package.json/tsconfig.json baseline)
  - `/Users/serkan/meta-mcp/` (simpler entry-point pattern)
- **Mission file format inspection**: any directory under `~/.factory/missions/`
  has the canonical layout. `10efd7ee-42c2-49d6-ac80-fdd3cddf3b22` is one with
  a non-trivial `progress_log.jsonl` worth using as a fixture.
