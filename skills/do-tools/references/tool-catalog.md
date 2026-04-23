# do_* Tool Catalog (13 tools)

All tools are MCP tools accessed via `mcp__mcp-do__<tool_name>`. Every tool inherits the caller's cwd by default and accepts an optional `cwd` parameter.

Three backends in use:
- **droid** / **opencode** — BYOK headless models via `droid exec` / `opencode run` spawn-per-call.
- **Codex MCP** — persistent `codex mcp-server` subprocess (one per mcp-do lifetime) for GPT-5.4 plan discussion and auditing. Used by `do_discuss` and `do_audit`. Follow-up turns are ~10x faster than first turns because the process stays warm.

---

## Execution Tools (6 — support `provider` param)

### do_exec
Generic passthrough. For droid: every CLI flag exposed. For opencode: runs `opencode run` with model + agent + prompt.

```typescript
mcp__mcp-do__do_exec({
  prompt: "Explain the error handling in src/utils/errors.ts",
  provider: "droid",   // or "opencode"
  model: "glm-5-turbo",
  auto: "high",        // droid only
})
```

### do_research
Unified web research. Two depths via the `depth` param — default `"deep"` runs parallel search with structured findings + sources + confidence + open questions; `"fast"` returns a concise <200-word answer for quick lookups (version numbers, API signatures, defaults).

```typescript
// Deep (default)
mcp__mcp-do__do_research({
  prompt: "How does opencode handle session persistence? Compare with droid's approach.",
})

// Fast lookup (<200 words, MiniMax model)
mcp__mcp-do__do_research({
  prompt: "What's the default port for opencode serve?",
  depth: "fast",
})
```

### do_review
Code review for bugs, security, edge cases. Returns severity-rated findings with file:line citations. Skeptical by default — only material issues, not style.

Use this tool with a focused prompt prefix for narrow reviews (silent-failure scans, TypeScript type reviews) — the `/do:scan` and `/do:types` slash commands are thin wrappers that do exactly that.

```typescript
mcp__mcp-do__do_review({
  prompt: "Review the changes in src/providers/:\n\n<git diff output>",
  provider: "opencode",
})
```

### do_explore
Codebase navigation — answers "where is X?" and "how does Y work?" with file:line references and call chains. Read-only.

```typescript
mcp__mcp-do__do_explore({
  prompt: "How does the provider abstraction dispatch to droid vs opencode?",
})
```

### do_architect
Architecture analysis — evaluates structure, identifies risks, recommends improvements with explicit trade-off assessments. Uses the deepest droid model (GLM-5.1).

```typescript
mcp__mcp-do__do_architect({
  prompt: "Analyze the mcp-do architecture: provider layer, tool registration, config system",
})
```

### do_cross_review
Cross-model code review — runs the same review through 3 different model families in parallel and merges findings. Different training lineages catch different blind spots.

Default models per provider:
- **droid**: GLM-5-Turbo, GPT-5.4-Mini, GLM-5.1
- **opencode**: zai/glm-5-turbo, openai/gpt-5.4-mini, minimax/MiniMax-M2.7

```typescript
mcp__mcp-do__do_cross_review({
  prompt: "Review changes to the auth middleware:\n\n<git diff output>",
  provider: "droid",
})
```

### do_pr_review
Comprehensive PR review with GPT-5.4 xHigh. Auto-gathers git context. See `/do:pr` slash command for the typical invocation path.

---

## Codex Tools (2 — GPT-5.4 via persistent Codex MCP backend)

### do_discuss
Iterative plan / architecture sounding board with GPT-5.4 xHigh. Returns a structured critique: `objective`, `risks[]`, `blockers[]`, `alternatives[]`, `missing[]`, `verdict` (`proceed` / `proceed-with-changes` / `reconsider`). Pass `thread_id` to continue; follow-ups are ~10x faster than first turn. Read-only sandbox — does not write code.

```typescript
// Turn 1
mcp__mcp-do__do_discuss({
  prompt: "Plan: rename all variables from camelCase to snake_case in one PR across 200k LOC. Good idea?",
  reasoning_effort: "xhigh",   // default. minimal | low | medium | high | xhigh
})
// → { thread_id, verdict: "reconsider", risks: [...], blockers: [...], ... }

// Turn 2 — iterate via thread_id
mcp__mcp-do__do_discuss({
  thread_id: "019dbb...",
  prompt: "What if we split by module boundary into 5 PRs?",
})
```

### do_audit
Post-delivery auditor with GPT-5.4 High. Give it `context` (plan/acceptance criteria) and `diff` (what was delivered), get a typed verdict:

- `verdict`: `"pass"` | `"concerns"` | `"blockers"`
- `blockers[]`, `concerns[]`, `missed_requirements[]`, `strengths[]`, `next_steps[]` — all typed string arrays

Pass `thread_id` from a prior `do_discuss` to audit inside the same Codex conversation — it remembers the plan it helped shape. Also the right tool for adversarial reviews that challenge design choices.

```typescript
mcp__mcp-do__do_audit({
  context: "Add function add(a,b): number with test and TypeError on non-number input.",
  diff: "+export function add(a: number, b: number) { return a + b; }",
  thread_id: "019dbb...",     // optional — continues a prior discuss thread
  reasoning_effort: "high",   // default
})
// → { verdict: "blockers", blockers: ["..."], missed_requirements: ["..."], ... }
```

Typical flow: `do_discuss` to pressure-test a plan → implement → `do_audit` with the same `thread_id` so Codex reviews against the plan it critiqued.

---

## Session Tools (2 — droid only)

### do_session_continue
Continue an existing droid session by id. Loads conversation history and runs the new prompt in the same thread.

```typescript
mcp__mcp-do__do_session_continue({
  session_id: "abc-123",
  prompt: "Now focus on the error handling in the same file",
})
```

### do_session_list
List droid sessions. Pass `scan_disk: true` for complete results (sessions-index.json is incomplete).

```typescript
mcp__mcp-do__do_session_list({
  scan_disk: true,    // walk .jsonl files on disk (slower but complete)
  search: "review",   // optional text filter
  limit: 20,
})
```

---

## Meta Tools (2 — read-only, no provider)

### do_list_models
List custom BYOK models from `~/.factory/settings.json`. Returns canonical id, short alias, display name, and provider.

```typescript
mcp__mcp-do__do_list_models({})
```

### do_list_profiles
List droid agent profiles from `~/.factory/droids/*.md` (global) and `<cwd>/.factory/droids/*.md` (project-local).

```typescript
mcp__mcp-do__do_list_profiles({})
```

---

## Common Parameters

| Parameter | Applies to | Description |
|-----------|-----------|-------------|
| `prompt` | All execution tools | The task/question to send |
| `provider` | Droid/opencode tools | `"droid"` or `"opencode"` — overrides default |
| `model` | All execution tools | Model alias or provider-specific ID |
| `cwd` | All tools | Working directory override |
| `timeout_ms` | Droid/opencode tools | Per-call timeout in ms |
| `auto` | Droid presets | Autonomy level: `"low"` / `"medium"` / `"high"` |
| `session_id` | Droid presets + session_continue | Continue existing droid session |
| `thread_id` | `do_discuss`, `do_audit` | Continue existing Codex thread |
| `reasoning_effort` | `do_discuss`, `do_audit` | `minimal` / `low` / `medium` / `high` / `xhigh` |
| `depth` | `do_research` | `"deep"` (default) or `"fast"` |
| `scan_disk` | `do_session_list` | Walk disk for complete session list |

---

## What changed (April 2026)

Four tools were removed or merged to reduce surface area from 17 to 13:

- `do_silent_scan` → use `do_review` with a silent-failure focus prefix (`/do:scan` slash command does this automatically).
- `do_type_check` → use `do_review` with a type-review focus prefix (`/do:types` does this automatically).
- `do_adversarial_review` → use `do_audit`. GPT-5.4 with structured verdict is strictly better at challenging design choices than the old droid-backed adversarial prompt. `/do:adversarial-review` now routes through `do_audit`.
- `do_research_fast` → merged into `do_research({ depth: "fast" })`.
