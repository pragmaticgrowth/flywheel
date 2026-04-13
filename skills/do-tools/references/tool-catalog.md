# do_* Tool Catalog (13 tools)

All tools are MCP tools accessed via `mcp__mcp-do__<tool_name>`. Every tool inherits the caller's cwd by default and accepts an optional `cwd` parameter.

---

## Execution Tools (9 — support `provider` param)

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
Deep web research — parallel search across web, Reddit, HN, docs. Structured findings with source citations and confidence assessment.

```typescript
mcp__mcp-do__do_research({
  prompt: "How does opencode handle session persistence? Compare with droid's approach.",
  provider: "droid",
})
```

### do_research_fast
Quick lookup — concise answer under 200 words with source and caveats. Uses fastest/cheapest model.

```typescript
mcp__mcp-do__do_research_fast({
  prompt: "What's the default port for opencode serve?",
})
```

### do_review
Code review for bugs, security, edge cases. Returns severity-rated findings with file:line citations. Skeptical by default.

```typescript
mcp__mcp-do__do_review({
  prompt: "Review the changes in src/providers/:\n\n<git diff output>",
  provider: "opencode",
})
```

### do_explore
Codebase navigation — answers "where is X?" and "how does Y work?" with file:line references and call chains.

```typescript
mcp__mcp-do__do_explore({
  prompt: "How does the provider abstraction dispatch to droid vs opencode?",
})
```

### do_architect
Architecture analysis — evaluates structure, identifies risks, recommends improvements with explicit trade-off assessments. Uses the deepest analysis model.

```typescript
mcp__mcp-do__do_architect({
  prompt: "Analyze the mcp-droid architecture: provider layer, tool registration, config system",
})
```

### do_silent_scan
Silent failure scanner — finds swallowed errors, empty catches, ignored promises, missing error handling on I/O.

```typescript
mcp__mcp-do__do_silent_scan({
  prompt: "Scan src/ for silent failures, focusing on the spawn helpers in droid/exec.ts and opencode/exec.ts",
})
```

### do_type_check
TypeScript type design review — flags any leaks, unsafe casts, missing nullability, incorrect generics.

```typescript
mcp__mcp-do__do_type_check({
  prompt: "Review type design in src/providers/ and src/config.ts",
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
  // models: ["custom:glm-5-turbo", "custom:VP-GPT-5.4-Mini-48", "custom:glm-5.1"],  // optional override
})
```

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
| `provider` | All execution tools | `"droid"` or `"opencode"` — overrides default |
| `model` | All execution tools | Model alias or provider-specific ID |
| `cwd` | All tools | Working directory override |
| `timeout_ms` | All execution tools | Per-call timeout in ms |
| `auto` | Presets (droid only) | Autonomy level: `"low"` / `"medium"` / `"high"` |
| `session_id` | Presets + session_continue | Continue existing session |
| `scan_disk` | do_session_list | Walk disk for complete session list |
