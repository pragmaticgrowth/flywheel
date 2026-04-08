# mcp-droid full tool catalog

24 tools across 5 categories. Every tool inherits the caller's `cwd` by
default and accepts an optional `cwd` parameter. All defaults use custom
BYOK models, never Factory built-ins.

Tool name prefix in Claude Code: `mcp__mcp-droid__<tool>` (e.g.
`mcp__mcp-droid__droid_research`).

## Generic / power-user (4)

### `droid_exec`
Generic passthrough — runs `droid exec [flags] <prompt>` with every CLI
flag exposed as a typed parameter. Use when no preset fits, when you
need fine control over flags, or when you want to pass `enabled_tools`
/ `disabled_tools` / `tags` / `system_prompt` / etc.

```typescript
mcp__mcp-droid__droid_exec({
  prompt: "explain this codebase in one paragraph",
  model: "custom:glm-5-turbo",
  auto: "high",
  output_format: "stream-json",   // default; rarely changed
  reasoning_effort: "high",        // optional, model-dependent
  tags: ["nt-dev", "exploration"],
  // every other droid exec flag is also available
})
```

Returns:
```json
{
  "session_id": "abc-123",
  "model": "custom:BYOK-GLM-5-Turbo-33",
  "text": "...",
  "num_turns": 1,
  "duration_ms": 5000,
  "usage": { "input_tokens": 100, "output_tokens": 50, ... }
}
```

### `droid_list_tools`
Wraps `droid exec --model <m> --list-tools`. Returns the catalog of
tools a given model has access to (114 tools on a typical install).

```typescript
mcp__mcp-droid__droid_list_tools({
  model: "custom:glm-5-turbo",
  mode: "compact",   // "names" (5 KB) | "compact" (20 KB, default) | "full" (98 KB, blows past limit)
})
```

Use `mode: "names"` if you just want a flat list of tool IDs to skim.
`"compact"` adds display name + category + allowed flags. `"full"`
includes the multi-paragraph descriptions and **usually exceeds the MCP
per-result token limit** — use only when you need a specific tool's
description and have nowhere else to look.

### `droid_list_models`
Reads `~/.factory/settings.json` `customModels[]` directly. **No droid
spawn.** Returns only custom (BYOK) models — Factory built-ins are
intentionally hidden per the user's preference.

```typescript
mcp__mcp-droid__droid_list_models({})
// → returns ~18 custom models with their canonical id, alias (if any),
//   display name, provider, base URL
```

### `droid_list_profiles`
Walks `~/.factory/droids/*.md` (global) and `<cwd>/.factory/droids/*.md`
(project-local override). Project-local profiles shadow global ones with
the same name. **No droid spawn.**

```typescript
mcp__mcp-droid__droid_list_profiles({ cwd: "/Users/serkan/nt-dev" })
// → returns ~11 profiles with name, scope, path, description, model, tools
```

## Specialized presets (11)

Each preset is a thin wrapper over `spawnDroidExec` with a fixed
`--append-system-prompt-file` (the matching profile in `~/.factory/droids/`)
and a default model + auto level. Override `model`, `auto`,
`reasoning_effort`, `session_id`, `tags`, `timeout_ms`, `cwd` per call.

All presets share the same input shape:

```typescript
{
  prompt: string,
  cwd?: string,
  model?: string,                      // override default
  auto?: "low" | "medium" | "high",    // override default
  reasoning_effort?: string,
  session_id?: string,                 // continue an existing session
  tags?: (string | { name: string; metadata?: object })[],
  timeout_ms?: number,                 // default 600000 (10 min)
}
```

| Tool | Profile (`~/.factory/droids/`) | Default model | Default auto | When to use |
|---|---|---|---|---|
| `droid_research` | `deep-researcher.md` | `custom:glm-5-turbo` | `high` | Deep web research with parallel search (web/Reddit/HN/X/news + Context7) |
| `droid_research_fast` | `deep-researcher.md` | `custom:MiniMax-M2.7` | `high` | Quick research lookups; cheaper |
| `droid_review_code` | `code-reviewer.md` | `custom:glm-5-turbo` | (none) | Structured code review (bugs/security/design/style) |
| `droid_explore_code` | `code-explorer.md` | `custom:glm-5-turbo` | (none) | "Where is X?" / "How does Y work?" navigation |
| `droid_architect` | `code-architect.md` | `custom:glm-5.1` | (none) | High-level architecture analysis (slowest, deepest) |
| `droid_simplify` | `code-simplifier.md` | `custom:glm-5-turbo` | `low` | Refactor toward simpler code (writes files — auto: low) |
| `droid_silent_failure_scan` | `silent-failure-hunter.md` | `custom:glm-5-turbo` | (none) | Find empty catches, ignored promises, swallowed errors |
| `droid_pr_test_analyzer` | `pr-test-analyzer.md` | `custom:glm-5-turbo` | (none) | Check PR test coverage |
| `droid_type_design_analyzer` | `type-design-analyzer.md` | `custom:glm-5-turbo` | (none) | Flag `any` leaks, loose unions, missing discriminators |
| `droid_scrutiny_review` | `scrutiny-feature-reviewer.md` | `custom:glm-5-turbo` | (none) | Deep-dive review of a single feature |
| `droid_user_testing_validator` | `user-testing-flow-validator.md` | `custom:glm-5-turbo` | (none) | Validate user-facing flows |

**Example: research a library change**
```typescript
mcp__mcp-droid__droid_research_fast({
  prompt: "what are the breaking changes in tRPC v11 that affect Next.js App Router users?"
})
```

**Example: review code with explicit constraints**
```typescript
mcp__mcp-droid__droid_review_code({
  prompt: "Review src/features/state-tax/api/customer/start.ts for: (1) DDD layering violations, (2) missing Sentry capture in catches, (3) deviations from .claude/rules/api.md. Output a Markdown report with file:line refs.",
  model: "custom:glm-5-turbo",
})
```

**Example: chained explore + simplify**
```typescript
// 1. Explore first
const exploreResult = mcp__mcp-droid__droid_explore_code({
  prompt: "how does the formation order state machine work? List every state and transition."
})
// → captures session_id

// 2. Continue in the same session to refactor
mcp__mcp-droid__droid_session_continue({
  session_id: <from step 1>,
  prompt: "now propose a refactor that makes the state transitions explicit via a typed state union",
  auto: "low",  // allow file edits
})
```

## Sessions (4)

Sessions persist conversation history on disk in
`~/.factory/sessions/<encoded-cwd>/<session-id>.jsonl`. Use sessions for
back-and-forth conversation, iterative design, or to chain multiple
turns of context.

### `droid_session_continue`
Adds a turn to an existing session by id. Equivalent to
`droid exec -s <session_id> "<prompt>"`. Loads conversation history
without replaying old messages in output.

```typescript
mcp__mcp-droid__droid_session_continue({
  session_id: "abc-123",
  prompt: "now refactor it without using async/await",
  model: "custom:glm-5-turbo",   // optional override
  auto: "low",                    // optional
})
```

### `droid_session_fork`
Branches an existing session at its current checkpoint. The new turns
go into a NEW session_id (returned in the response) and don't affect
the original. Useful for "take a different approach from this point".

```typescript
mcp__mcp-droid__droid_session_fork({
  session_id: "abc-123",
  prompt: "actually use Zustand instead of Redux for the state",
})
// → returns NEW session_id (not abc-123)
```

### `droid_session_list`
Lists droid sessions. Two modes:

```typescript
// Default — fast index read, but INCOMPLETE
mcp__mcp-droid__droid_session_list({ cwd: "/Users/serkan/nt-dev", limit: 20 })
// → reads ~/.factory/sessions-index.json which skips droid-exec sessions

// Complete — walks ~/.factory/sessions/<dir>/*.jsonl
mcp__mcp-droid__droid_session_list({ all: true, scan_disk: true, limit: 100 })
// → ~200ms but catches every session
```

Filters: `cwd` (default = current cwd, exact match), `all: true` to
ignore cwd filter, `search` (case-insensitive substring on title),
`limit` (default 50).

The response includes `source: "sessions_index"` or `"disk_walk"` so
you know which mode was used.

### `droid_session_search`
Full-text search across droid session content via the underlying
`droid search` CLI. **The CLI is global** — it ignores cwd. mcp-droid
post-filters the results by reading each hit's `.jsonl` first line for
the authoritative cwd.

```typescript
mcp__mcp-droid__droid_session_search({
  query: "JWT rotation",
  // cwd defaults to current process cwd (post-filter)
  // pass all: true to disable the post-filter
  kind: "message_text",   // | "document" | "tool_use" | "tool_result" | "all" (default)
  limit_sessions: 10,
  limit_hits: 3,
  context_chars: 80,
})
```

Returns each session enriched with the authoritative `cwd` field plus
counts of matching events per kind.

## Missions (4)

Mission state lives on disk in `~/.factory/missions/<uuid>/` with files
appearing in this order during a mission's lifecycle:

```
t=0..N s    working_directory.txt    (cwd, plain text — written FIRST)
            mission.md               (prompt + plan)
            progress_log.jsonl       (mission_accepted, mission_run_started, ...)

t=N..M s    state.json               (only once factoryd starts a worker)
            features.json
            handoffs/
            evidence/
            worker-transcripts.jsonl
```

mcp-droid recognizes missions by `working_directory.txt` (not
`state.json`) and falls back gracefully when `state.json` doesn't
exist yet.

### `droid_mission_start`
Spawns `droid exec --mission --auto high "<prompt>"` as a **detached**
process and polls `~/.factory/missions/` for the new directory. Returns
within ~10–30 seconds leaving the mission running independently.

```typescript
mcp__mcp-droid__droid_mission_start({
  prompt: "...",  // see SKILL.md "Writing a good mission prompt"
  cwd: "/tmp/mission-feature-x",   // ALWAYS use /tmp/ — see Rule 1
  model: "custom:glm-5-turbo",
  // allow_unsafe: true,  // alternative to --auto high (only in sandboxes)
  // tags: [...],
  timeout_ms: 180000,  // wait up to 3 min for the mission dir; mission keeps running after either way
})
```

Returns:
```json
{
  "mission_triggered": true,
  "uuid": "<uuid>",
  "mission_id": "pending-<uuid>" or "mis_xxx",
  "working_directory": "/tmp/mission-feature-x",
  "spawn_cwd": "/tmp/mission-feature-x",
  "working_directory_matches_spawn_cwd": true,
  "state_file": "/Users/serkan/.factory/missions/<uuid>/state.json",
  "state_file_exists_yet": false,
  "initial_status": { ... },
  "droid_pid": 22169,
  "droid_log": "/var/folders/.../mcp-droid-mission-<timestamp>.log"
}
```

If `mission_triggered: false`, the prompt was too trivial. See SKILL.md
Rule 3.

### `droid_mission_list`
Lists missions on disk, filtered by cwd by default. Pass `all: true`
to see every mission across every project.

```typescript
mcp__mcp-droid__droid_mission_list({
  cwd: "/tmp/mission-feature-x",
  // all: true,
  // state: "running" | "paused" | "completed" | "failed" | ...
  limit: 20,
})
```

Returns each mission with mission_id, uuid, state, completed/total
features, working_directory, created/updated timestamps, sorted by
updated_at desc.

### `droid_mission_status`
Get the full status of one mission. Accepts either the `mis_xxx`
mission_id or the directory uuid.

```typescript
mcp__mcp-droid__droid_mission_status({
  mission_id: "<uuid or mis_xxx>",
  include_progress: true,    // default true — adds recent_events
  progress_limit: 20,        // default 20 events from the tail
  include_handoffs: false,   // default false — handoffs are 10 KB+ each
  include_features: true,    // default true
})
```

Returns the parsed `state.json` plus optional features and progress
events. With `include_handoffs: false` (default), each `worker_completed`
event has its giant `handoff` payload replaced with a compact
`handoff_summary` (salient summary + first 200 chars of what was
implemented).

Use `include_handoffs: true` only when you need the full per-feature
handoff payload (test cases, file changes, verification commands —
typically for post-mission audit).

### `droid_mission_progress`
Tail-reads `progress_log.jsonl` for incremental polling. Use this in
loops to watch a mission as it runs.

```typescript
mcp__mcp-droid__droid_mission_progress({
  mission_id: "<uuid>",
  since_offset: 0,                    // first call
  // since_timestamp: "2026-04-01T10:00:00Z",   // alternative to offset
  limit: 50,
  event_types: ["worker_completed", "worker_failed"],   // optional filter
  exclude_handoffs: true,             // default true
})
```

Returns:
```json
{
  "events": [...],
  "next_offset": 47,
  "next_timestamp": "2026-04-01T10:30:00Z",
  "is_complete": false
}
```

`is_complete: true` when the mission is in a terminal state
(`completed` / `failed` / `cancelled`).

## Spec mode (1)

### `droid_spec`
Wraps `droid exec --use-spec --spec-model <m> --auto low "<prompt>"`.
Spec mode is droid's structured planning workflow that produces a
written spec before execution. The output spec file lands in
`~/.factory/docs/<date>-<topic>.md`.

```typescript
mcp__mcp-droid__droid_spec({
  prompt: "spec out a webhook signature verification module that supports HMAC-SHA256 and Ed25519, with replay protection",
  spec_model: "custom:glm-5.1",   // default; the model that authors the spec
  model: "custom:glm-5-turbo",    // default; the model used outside spec mode
  auto: "low",                    // default; lets the model write the spec file (read-only causes spurious exit-1 failures)
})
```

**Why `auto: "low"` is the default**: spec mode is stochastic — after
the model calls `ExitSpecMode` to approve the spec, it may try to
execute on the approved plan (Create/Edit/Execute tool calls). Without
any auto level, those calls are blocked and droid sometimes exits 1.
`auto: "low"` lets the model write the spec file and perform simple
edits cleanly. Override only if you know what you're doing.

## Common usage patterns

**Token-saving research from any project:**
```typescript
mcp__mcp-droid__droid_research_fast({ prompt: "what is the OAuth 2.1 device flow?" })
```
Replaces 10–30 KB of Context7/web-search responses with a clean summary.

**Code review after editing:**
```typescript
mcp__mcp-droid__droid_review_code({
  prompt: "review the changes I just made in src/feature/auth.ts for security issues"
})
```

**Codebase navigation:**
```typescript
mcp__mcp-droid__droid_explore_code({
  prompt: "where is the JWT verification logic and how does the rotation work?"
})
```

**Long-running mission with progress tracking:**
```typescript
// 1. Start
mcp__mcp-droid__droid_mission_start({
  cwd: "/tmp/mission-auth",
  prompt: "implement user auth with email + OAuth2, with tests..."
})
// → returns uuid

// 2. Periodically poll
mcp__mcp-droid__droid_mission_status({
  mission_id: "<uuid>",
  include_progress: true,
  progress_limit: 10,
})
```

**Multi-turn conversation:**
```typescript
// Initial — captures session_id
mcp__mcp-droid__droid_exec({
  prompt: "summarize this directory",
  model: "custom:glm-5-turbo",
})
// → session_id: "abc-123"

// Continue
mcp__mcp-droid__droid_session_continue({
  session_id: "abc-123",
  prompt: "now suggest 3 improvements",
})
```

**Find a session you forgot the id of:**
```typescript
mcp__mcp-droid__droid_session_search({
  query: "JWT rotation",
})
// → returns sessions in current cwd matching the query
```
