---
name: droid-mcp
description: Use Factory.ai Droid (via the mcp-droid MCP server) to delegate work — research, code review, codebase exploration, silent-failure scans, type-design analysis, multi-feature missions, session continuation. Trigger this skill whenever the user mentions droid, missions, mcp-droid, droid_research, droid_review_code, droid_explore_code, droid_mission_start, "delegate to droid", "run a mission", "ask the researcher", "have droid look at this", "audit X with droid", "kick off a long mission", or wants to offload any non-trivial task to a custom BYOK model (GLM-5-Turbo, MiniMax-M2.7, GLM-5.1). ALSO trigger when the user describes a task that fits the mission pattern (3+ files, audit-and-fix, test coverage sprint, multi-file refactor, "replace pattern X with Y everywhere") — proactively suggest a droid mission and draft the prompt. ALSO trigger when the user wants to continue or fork a previous droid session, search across past sessions, list available droid profiles, or check what models are available. Do NOT undertrigger this — if the task touches research, review, exploration, or substantial autonomous work, this skill is the right tool.
---

# droid-mcp — Factory.ai Droid via mcp-droid (+ tmux fallback)

Delegate work to Factory.ai Droid via two complementary paths:

1. **`mcp-droid`** — 24 typed MCP tools, accessible directly from Claude Code without leaving the conversation. The default and easier path. Handles 90% of cases including missions.
2. **tmux + interactive `droid` REPL** — fallback for live monitoring of multi-day missions, mid-mission manual intervention, or when you need to set worker/validator models separately from the orchestrator.

The `mcp-droid` server is registered at user scope (works from anywhere), so the `mcp__mcp-droid__*` tools are available in every Claude Code session.

## Decision matrix — which path to use

| Task | Use |
|---|---|
| Research a library / API / concept | `mcp__mcp-droid__droid_research` (or `_fast` for quick lookups) |
| Code review of recent edits (single model) | `mcp__mcp-droid__droid_review_code` |
| Code review with cross-model verification | `mcp__mcp-droid__droid_cross_review` — 3 models in parallel, merged report |
| "Where is X?" / "How does Y work?" navigation | `mcp__mcp-droid__droid_explore_code` |
| High-level architecture analysis | `mcp__mcp-droid__droid_architect` |
| Find empty catches / silent failures | `mcp__mcp-droid__droid_silent_failure_scan` |
| Check PR test coverage | `mcp__mcp-droid__droid_pr_test_analyzer` |
| Review TypeScript type design | `mcp__mcp-droid__droid_type_design_analyzer` |
| Deep-dive single feature review | `mcp__mcp-droid__droid_scrutiny_review` |
| Validate a user-facing flow | `mcp__mcp-droid__droid_user_testing_validator` |
| Refactor toward simpler code | `mcp__mcp-droid__droid_simplify` (writes files, `auto: "low"`) |
| Generic single-shot droid call | `mcp__mcp-droid__droid_exec` |
| Continue / fork a previous droid session | `droid_session_continue` / `droid_session_fork` |
| Search across past droid sessions | `droid_session_search` |
| List custom models / profiles / tools | `droid_list_models` / `droid_list_profiles` / `droid_list_tools` |
| Multi-feature autonomous mission (1–2 hours, fire-and-forget) | `mcp__mcp-droid__droid_mission_start` |
| Cancel a runaway / stuck / unwanted mission | `mcp__mcp-droid__droid_mission_cancel` (best-effort kill + state.json write) |
| Multi-day mission with live observability needs | tmux + `droid` REPL (see "Tmux fallback" below) |
| Mission with required mid-run human intervention | tmux + REPL (mcp-droid missions are non-interactive) |
| Quick bug fix in a single file | Handle in Claude Code directly — no droid |
| Anything needing browser verification or live prod data | Handle in Claude Code directly |

## When to suggest a mission proactively

Before working on a task, check for these signals:

| Signal | Action |
|---|---|
| 3+ files across DDD layers | Suggest mission (likely mcp-droid `mission_start`) |
| "Audit X and fix" pattern | Suggest mission |
| "Add tests for N files" | Suggest mission |
| "Refactor X into smaller files" | Suggest mission |
| "Replace pattern X with Y everywhere" | Suggest mission |
| Multi-day work requiring live monitoring | Suggest tmux/REPL mission |
| Quick bug fix, single file | Handle in Claude Code |
| Needs browser verification / live prod data | Handle in Claude Code |
| Scope unclear, needs exploration | Brainstorm first, then mission |
| Pre-commit review of significant changes | `droid_cross_review` (3 models catch more than 1) |
| Security / payment / auth code review | `droid_cross_review` (non-negotiable for sensitive code) |

When suggesting: **always draft the full mission prompt yourself** so the user just has to review and click. Tell them which path you're suggesting (`mcp-droid mission_start` vs tmux REPL) and why.

## mcp-droid quick reference (26 tools)

Full catalog with examples in [`references/all-tools.md`](references/all-tools.md).

**Generic / power-user (4):** `droid_exec`, `droid_list_tools`, `droid_list_models`, `droid_list_profiles`

**Specialized presets (11):** `droid_research`, `droid_research_fast`, `droid_review_code`, `droid_explore_code`, `droid_architect`, `droid_simplify`, `droid_silent_failure_scan`, `droid_pr_test_analyzer`, `droid_type_design_analyzer`, `droid_scrutiny_review`, `droid_user_testing_validator`

**Cross-model (1):** `droid_cross_review` — runs the same review prompt through 3 models (GLM-5-Turbo, GPT-5.4-Mini, GLM-5.1) in parallel, returns merged report. Each model gets structured instructions to produce actionable file:line findings. Different training lineages = different blind spots.

**Sessions (4):** `droid_session_continue`, `droid_session_fork`, `droid_session_list`, `droid_session_search`

**Missions (5):** `droid_mission_start`, `droid_mission_list`, `droid_mission_status`, `droid_mission_progress`, `droid_mission_cancel`

**Spec mode (1):** `droid_spec`

Every tool inherits the caller's cwd by default. Every tool accepts an optional `cwd` parameter. All custom BYOK models, never built-ins.

## Core operational rules

These are **load-bearing** — violating them has caused real bugs. Read them.

### Rule 1: Never run `droid_mission_start` with cwd inside a git repo you care about

Droid missions run with `--auto high` and **WILL commit their scaffolding into the cwd's git repo**. Verified three times on the mcp-droid project itself — droid created `step1.txt`, `step2.txt`, `step3.txt`, `.factory/init.sh`, `.factory/services.yaml`, `.factory/validation/scrutiny/*` and committed them via worker commits, bypassing `.gitignore` for previously-tracked files.

**Always pass `cwd: "/tmp/mission-<unique>"`** when calling `droid_mission_start`:

```typescript
mcp__mcp-droid__droid_mission_start({
  prompt: "...",
  cwd: "/tmp/mission-feature-x",  // ← throwaway, never your nt-dev clone
  model: "custom:glm-5-turbo",
  timeout_ms: 90000,
})
```

The mission's outputs end up in `/tmp/mission-feature-x/`, you read them later, and if droid commits scaffolding into that throwaway dir it doesn't matter.

### Rule 2: Only custom BYOK/VP models, never Factory built-ins

Use `custom:glm-5-turbo`, `custom:MiniMax-M2.7`, `custom:glm-5.1`, `custom:VP-GPT-5.4-Mini-48`, `custom:VP-GPT-5.4-15`, `custom:VP-Opus-4.6-1M-xHigh-44`, etc. **Never** `claude-opus-4-6`, `gpt-5.4`, `gpt-5.4-mini`, `gemini-3-flash-preview`, `glm-5`, `kimi-k2.5`, etc — those are factory built-ins (402 Payment Required) and not part of this user's workflow.

The mcp-droid presets already default to custom models. Only override `model:` with a custom id.

### Rule 3: Trivial prompts don't trigger missions

`droid exec --mission "say hi"` completes as a plain exec in ~5 seconds and creates **zero** new mission directories. mcp-droid detects this and returns:

```json
{ "mission_triggered": false, "reason": "...", "base_session_id": "...", "text": "..." }
```

**This is not an error.** It means the prompt was too simple to warrant the orchestrator. If you actually want a mission, write a prompt that genuinely needs multi-feature planning (3+ features, milestones, validation criteria). If you just want a one-shot answer, use `droid_exec` or a preset, not `mission_start`.

### Rule 4: Missions are fully autonomous — no AskUser, no mid-run interaction

Verified empirically: zero `AskUser` calls and zero `user_input_needed` events across 26 existing missions. Droid help text says explicitly: **"Missions auto-approve proposals (no interactive confirmation)."**

If your task needs back-and-forth with the user, **do not start a mission**. Use a session instead:

```typescript
// Conversational pattern
mcp__mcp-droid__droid_exec({ prompt: "let me iterate with you on the auth design. What model should we use for tokens?", model: "custom:glm-5-turbo" })
// → returns session_id "abc-123" with droid's questions

mcp__mcp-droid__droid_session_continue({ session_id: "abc-123", prompt: "HS256 with rotation every 24h" })
// → droid continues with that context
```

For missions, **put every decision in the opening prompt**. The mission has no way to ask you anything mid-run. If it hits ambiguity, it auto-decides or a worker fails.

### Rule 5: `droid_session_search` is global; `droid_session_list` is incomplete

- `droid search` (the underlying CLI) ignores cwd entirely. mcp-droid's `droid_session_search` post-filters by reading each hit's `.jsonl` first line for the authoritative cwd, but pass `all: true` if you want the unfiltered set.
- `droid_session_list` reads `~/.factory/sessions-index.json` by default — **and that index is incomplete**. It skips sessions created via `droid exec` (which is how mcp-droid creates them). Pass `scan_disk: true` for the complete set (slower, walks the on-disk session files directly).

```typescript
// Default: fast but may miss sessions
mcp__mcp-droid__droid_session_list({ all: true })

// Complete: walks ~/.factory/sessions/<dir>/*.jsonl
mcp__mcp-droid__droid_session_list({ all: true, scan_disk: true })
```

## Mission workflow via mcp-droid (the canonical path)

This is the easier, faster path. No tmux ceremony. Reference: [`references/missions-deep-dive.md`](references/missions-deep-dive.md).

### 1. Set up a throwaway cwd

```bash
mkdir -p /tmp/mission-<feature-name>
```

Use a unique name per mission so concurrent missions don't collide. Don't reuse `/tmp/mission-test` for different work.

### 2. Start the mission

```typescript
mcp__mcp-droid__droid_mission_start({
  cwd: "/tmp/mission-federal-tax-audit",
  model: "custom:glm-5-turbo",  // or custom:VP-Opus-4.6-1M-xHigh-44 for deep work
  timeout_ms: 180000,  // 3 min wait for mission dir to appear; mission keeps running after
  prompt: `## Goal
Audit and harden silent error catches in src/features/federal-tax/.

## Context
- nt-dev TypeScript codebase, follows DDD layering
- Recent bug from a swallowed Stripe webhook error in process-webhook.use-case.ts

## Scope
### IN SCOPE
- src/features/federal-tax/**
- src/features/webhooks/application/**
### OUT OF SCOPE
- Any state-tax code
- Frontend changes

## Constraints
- TDD: write the failing test before fixing each catch
- Use Sentry.captureException with { extra, tags } per .claude/rules/observability.md
- Read .claude/rules/tdd.md and .claude/rules/federal-tax.md before starting

## Milestones
### Milestone 1: Audit
- List every empty catch / .catch(() => {}) / try-without-rethrow in scope
- Output: docs/silent-catch-audit-2026-04.md

### Milestone 2: Fix
- For each empty catch from Milestone 1: add Sentry capture + write a test that fails when the catch is empty
- Exit criteria: all 5366+ tests pass, 0 type errors, 0 new lint warnings

### Milestone 3: Validation
- pnpm typecheck → 0 errors
- pnpm test → 5366+ pass
- pnpm lint → ≤50 warnings (no new ones)
- grep -rn 'catch.*{[^}]*}' src/features/federal-tax/ → manual review

## Reference files in scope
- .claude/rules/tdd.md
- .claude/rules/federal-tax.md
- .claude/rules/observability.md`,
})
```

The response returns immediately (typically within 10–30 seconds) with:
```json
{
  "mission_triggered": true,
  "uuid": "84e2d4c7-...",
  "mission_id": "pending-84e2d4c7-..." or "mis_xxx" once factoryd starts,
  "working_directory": "/tmp/mission-federal-tax-audit",
  "spawn_cwd": "/tmp/mission-federal-tax-audit",
  "working_directory_matches_spawn_cwd": true,
  "state_file": "/Users/serkan/.factory/missions/<uuid>/state.json",
  "state_file_exists_yet": false,
  "initial_status": { "state": "initializing", "title": "...", "recent_events": [...] },
  "droid_pid": 22169,
  "droid_log": "/var/folders/.../mcp-droid-mission-<timestamp>.log"
}
```

**Save the `uuid` and `droid_log` path.** You'll need them for monitoring.

### 3. Poll for progress

```typescript
// Initial state — typically "initializing" → "running" → "orchestrator_turn" → "completed"
mcp__mcp-droid__droid_mission_status({
  mission_id: "<uuid from step 2>",
  include_progress: true,
  progress_limit: 10,
})
```

Returns:
```json
{
  "mission_id": "mis_662293c0",
  "uuid": "<uuid>",
  "state": "running",
  "completed_features": 1,
  "total_features": 5,
  "current_feature_id": "audit-empty-catches",
  "current_worker_session_id": "...",
  "current_worker_pid": 12345,
  "title": "Federal Tax Silent Catch Hardening",
  "recent_events": [
    { "type": "mission_run_started", ... },
    { "type": "worker_selected_feature", "featureId": "audit-empty-catches", ... },
    { "type": "worker_started", ... },
    { "type": "worker_completed", "handoff_summary": { "summary": "...", "what_implemented": "..." }, ... }
  ],
  "features": [...]
}
```

### 4. Tail progress incrementally

For polling loops, use `droid_mission_progress` with `since_offset` to only get new events:

```typescript
mcp__mcp-droid__droid_mission_progress({
  mission_id: "<uuid>",
  since_offset: 0,  // first call
  limit: 50,
})
// → returns { events: [...], next_offset: 12, is_complete: false }

// Subsequent calls
mcp__mcp-droid__droid_mission_progress({
  mission_id: "<uuid>",
  since_offset: 12,
  limit: 50,
})
// → returns only events 12+
```

When `is_complete: true` the mission is in a terminal state (completed/failed/cancelled).

### 5. Inspect droid's raw output

If something looks wrong, the full droid stdout/stderr is in the `droid_log` path returned by `mission_start`:

```bash
tail -100 /var/folders/.../mcp-droid-mission-<timestamp>.log
```

This is your debugging window into what the orchestrator and workers are doing turn-by-turn.

### 6. Read mission outputs

The mission's actual file outputs live in the `cwd` you specified at start time:

```bash
ls /tmp/mission-federal-tax-audit/
# whatever the mission produced
```

Mission *metadata* (state.json, features.json, progress_log.jsonl, handoffs/, worker-transcripts.jsonl) lives in `~/.factory/missions/<uuid>/` — you usually don't need to look there directly; mcp-droid surfaces it via `mission_status` / `mission_progress`.

### 7. Post-mission audit

After the mission reaches `state: "completed"`, **always** run a post-mission audit before merging anything to nt-dev:

1. **Read the changed files** — droid's commits live in the mission's cwd's git repo. If the mission's cwd was `/tmp/mission-X` (as it should be), there's no contamination of nt-dev. Diff the produced files into nt-dev manually if you want them.
2. **Run nt-dev's verification** from Claude Code (NOT from droid):
   ```bash
   pnpm typecheck    # 0 errors required
   pnpm test         # all 5366+ tests pass
   pnpm lint         # ≤50 warnings, no new ones
   ```
3. **Check for scope leaks** — did the mission touch files outside its declared scope?
4. **Read any test cases the mission added** to make sure they're meaningful and not green-rubber-stamps.

### 8. Cancel a runaway or unwanted mission

If a mission is misbehaving, stuck, or you just decided you don't want the work anymore, call `droid_mission_cancel`. It's a **best-effort** tool — droid has no official cancel API, so mcp-droid kills the processes we have handles to and writes `state: "cancelled"` to `state.json`.

```typescript
mcp__mcp-droid__droid_mission_cancel({
  mission_id: "<uuid or mis_xxx>",
  droid_pid: <the droid_pid from mission_start's response>,
  // force: true,           // skip SIGTERM, go straight to SIGKILL
  // write_state: false,    // don't touch state.json (preserve for investigation)
})
```

**What it does:**

1. Resolves `mission_id` → directory uuid
2. Reads state.json for `currentWorkerPid`
3. In parallel: SIGTERM → (2 s wait) → SIGKILL for `droid_pid` AND `currentWorkerPid` (if either exists)
4. Writes state.json with `state: "cancelled"` (**creates it from scratch** via synthesis from `working_directory.txt` if factoryd hasn't written state.json yet — verified bug fix in commit `b064382`)

**What it returns:**

```json
{
  "mission_id": "mis_xxx or pending-<uuid>",
  "uuid": "<uuid>",
  "killed": [
    { "pid": 97486, "role": "orchestrator", "killed": true, "required_sigkill": false }
  ],
  "state_before": "initializing",
  "state_after": "cancelled",
  "state_file_updated": true,
  "warnings": []
}
```

**Known limitations** (honest about what it can't do):

- **If you didn't save `droid_pid`** from the original `mission_start` response, the tool can't kill the orchestrator. It'll still kill `currentWorkerPid` (if any) and write `state: "cancelled"`, and the response will include a warning telling you to `pkill -f "droid exec --mission"` manually.
- **factoryd-spawned sibling processes** may survive the orchestrator kill. The warning will point this out. Manual cleanup: `pkill -f "droid exec --mission"`.
- **If factoryd/orchestrator is still alive** when cancel runs, it may overwrite our state.json write. We mitigate by killing processes BEFORE writing state — but it's inherently a race if the daemon is still spawning workers.
- **`force: true` skips SIGTERM entirely** and sends SIGKILL immediately. Use for processes that ignore SIGTERM or when you need instant teardown. Normal `force: false` (default) tries SIGTERM first with a 2-second grace window.

**When NOT to use cancel:**

- If the mission is actually working and you're just impatient — wait it out or use `droid_mission_progress` to watch.
- If you cancelled a mission and it still shows as running, run `pgrep -f "droid exec --mission"` to see if a factoryd worker survived. If so, `pkill -f "droid exec --mission"` for aggressive cleanup.

**Verified 10/10 in a real end-to-end round-trip**: mid-flight cancel with droid_pid, cancel without droid_pid (graceful fallback + warning), cancel of a nonexistent mission (clean isError), cancel with `force: true` (required_sigkill=true confirms SIGKILL was used directly).

## Tmux fallback (only when mcp-droid isn't enough)

Use the tmux + interactive `droid` REPL flow when:

- Mission needs to run for **multi-day duration** with live observability (mcp-droid logs to a file but you'd want to actively watch it)
- You need to **manually intervene** mid-run (tell the orchestrator to course-correct, change a model, etc) — mcp-droid missions are non-interactive
- You want to **set worker and validator models separately** from the orchestrator (mcp-droid only sets the orchestrator via `--model`; worker/validator come from `~/.factory/settings.json missionModelSettings`)
- You're running on **Hetzner VPS** and want to attach from your local Mac via SSH

For these cases, use the [`scripts/mission-manager.sh`](scripts/mission-manager.sh) helper:

```bash
# Launch
bash .claude/skills/droid-mcp/scripts/mission-manager.sh launch federal-tax-audit /Users/serkan/nt-dev

# In the new tmux session, droid will start. Then:
#   /enter-mission
#   /model            ← CRITICAL: set Orchestrator to a custom Opus 4.6 1M (xHigh) entry
#   <describe goal, answer planning questions, approve plan>
#   Ctrl+B, D         ← detach, mission keeps running

# Check progress
bash .claude/skills/droid-mcp/scripts/mission-manager.sh peek federal-tax-audit 50

# Reattach
bash .claude/skills/droid-mcp/scripts/mission-manager.sh attach federal-tax-audit

# Kill
bash .claude/skills/droid-mcp/scripts/mission-manager.sh kill federal-tax-audit
```

**The `/model` step is non-optional** in the REPL flow. The orchestrator resets to Factory's built-in model on every `/enter-mission` and the built-in has token limits that will crash the mission a few hours in. Always set it to a `custom:VP-Opus-4.6-1M-xHigh-*` entry. Worker and Validator persist in `missionModelSettings` so they only need to be set once.

(For mcp-droid missions, this is a non-issue because `--model custom:...` is passed at spawn time and propagates to the orchestrator.)

Full tmux mechanics, monitoring multi-pane, recovery from stalls, and headless droid-exec usage are documented in [`references/tmux-fallback.md`](references/tmux-fallback.md).

## Writing a good mission prompt

Mission quality is determined entirely by the prompt — there's no mid-run correction. Structure every mission prompt with:

1. **Clear outcome** — What you want built/fixed, not how.
2. **Context** — Key files, recent bugs that motivated this, business rules.
3. **Scope** — Explicit IN SCOPE / OUT OF SCOPE lists. Be ruthless.
4. **Constraints** — Tech stack patterns, rule files to read first, things that must NOT happen.
5. **Milestones** — Phased delivery with concrete exit criteria per milestone.
6. **Validation** — Exact commands to run, what to grep for, what tests must pass.
7. **Reference files** — `.claude/rules/*.md` files the mission must read before starting.

**Standing template:**

```
## Goal
{1–2 sentence outcome}

## Context
{Key files, architecture, recent bugs that motivated this}

## Scope
### IN SCOPE
- {item 1}
- {item 2}
### OUT OF SCOPE
- {item 1}
- {item 2}

## Constraints
- {pattern to follow}
- {rule that must not be broken}
- Read first: .claude/rules/{relevant rules}.md

## Milestones
### Milestone 1: {name}
**Features:** {list}
**Exit criteria:** {concrete, verifiable}

### Milestone 2: {name}
**Features:** {list}
**Exit criteria:** {concrete, verifiable}

## Validation
{Exact commands, grep checks, test suites to run}
```

**Tips:**
- Invest time in the prompt — it's the only contract with the mission.
- Keep features narrow — one focused task per worker session.
- Use file artifacts (`docs/audit-2026-04.md`) for cross-session memory; workers spawn fresh each time.
- TDD framing works extremely well — validators get concrete pass/fail signals.
- Audit/fix missions: structure as **audit phase → fix phases → validation phase**.

## Common workflows in nt-dev

### Token-saving research from inside Claude Code

Default to `droid_research_fast` for quick lookups. It uses MiniMax M2.7 + the deep-researcher profile and replaces 10–30 KB of Context7/web-search responses with a clean summary:

```typescript
mcp__mcp-droid__droid_research_fast({ prompt: "what changed in TypeScript 5.6 around control flow analysis?" })
```

For quality research with reliable tool calling, use `droid_research` (GLM-5-Turbo).

### Code review after editing nt-dev files

**Single-model review** (fast, one perspective):
```typescript
mcp__mcp-droid__droid_review_code({
  prompt: "review the changes in src/features/federal-tax/api/admin/[id].ts for security and DDD-layering issues. Compare against .claude/rules/api.md.",
})
```

**Cross-model review** (3 models in parallel, catches 3-5x more issues):
```typescript
mcp__mcp-droid__droid_cross_review({
  prompt: "review the changes in src/features/federal-tax/api/admin/[id].ts for bugs, security issues, edge cases, and DDD-layering violations. Be specific — cite line numbers.",
})
// Returns merged report: ## GLM-5-Turbo [...] ## GPT-5.4-Mini [...] ## GLM-5.1 [...]
```

**When to use which:** Use `droid_review_code` for quick checks on small edits. Use `droid_cross_review` before committing significant changes, after completing a feature, or when the code touches security/payment/auth — different model families have different blind spots and the overlap is small.

### Find where something is implemented

```typescript
mcp__mcp-droid__droid_explore_code({
  prompt: "where is the DocuSeal webhook signature verification logic and how does it handle replay protection?",
})
```

### Multi-turn conversation about a design

```typescript
// Turn 1
mcp__mcp-droid__droid_exec({
  prompt: "let's design the new state-tax onboarding flow. What questions do you have?",
  model: "custom:glm-5-turbo",
  auto: "high",
})
// → returns session_id "abc-123" with droid's questions

// Turn 2 — answer the questions
mcp__mcp-droid__droid_session_continue({
  session_id: "abc-123",
  prompt: "Yes, multi-state. Yes, async via Inngest. No new tables — extend formation_orders.",
})
```

## Project-specific reference (nt-dev example)

The sections below are **example values for the nt-dev project**. If
you're working in a different project, adapt the model IDs, rule file
paths, and validation commands to match. The operational rules above
(custom BYOK models, never-run-missions-in-a-real-repo, structured
prompts, etc.) apply to **every** project.

### Custom models for missions

| Role | Model ID (local Mac) | Model ID (Hetzner VPS) |
|---|---|---|
| Orchestrator | `custom:VP-Opus-4.6-1M-xHigh-44` | `custom:VP-Opus-4.6-1M-xHigh-0` |
| Worker | `custom:VP-Opus-4.6-1M-Med-46` | `custom:VP-Opus-4.6-1M-Med-2` |
| Validator | `custom:VP-Opus-4.6-1M-xHigh-44` | `custom:VP-Opus-4.6-1M-xHigh-0` |

Model IDs differ between machines because they're auto-assigned incrementally. Verify with `grep customModels ~/.factory/settings.json`. Always use **Opus 4.6 1M** family for missions — GPT-5.4 causes daemon crashes when quota runs out and produces empty completions.

For mcp-droid `mission_start`, just pass `model: "custom:VP-Opus-4.6-1M-xHigh-44"` — that propagates to the orchestrator. Worker and Validator come from `missionModelSettings` in `~/.factory/settings.json`, which is already set up.

For research/review presets, the default `custom:glm-5-turbo` is fine — much cheaper than Opus.

### Rule files to reference in mission prompts

- `.claude/rules/tdd.md` — TDD is mandatory for all missions
- `.claude/rules/federal-tax.md` — Federal tax business rules
- `.claude/rules/api.md` — API patterns and DDD layering
- `.claude/rules/testing.md` — Test strategy
- `.claude/rules/design-system.md` — UI patterns
- `.claude/rules/observability.md` — Sentry capture conventions

Always include the relevant rule file paths in the mission prompt's Constraints section.

### Validation commands (for mission validators or post-audit)

```bash
pnpm typecheck    # 0 errors required
pnpm test         # all 5366+ tests pass (405 suites)
pnpm lint         # ≤50 warnings, no new ones
```

### Supabase project IDs

- Staging: `qqmrjlgxpgxhnblghccd`
- Production: `hqxqhwzqqysfitocvemi`

### Mission tracking

All missions are tracked in `.factory/missions/missions.yaml`. Mission prompts are stored in `.factory/missions/prompts/`.

**After every mission completes**, update `missions.yaml` with:
- Mission ID, name, date, machine, status
- Assertions passed/total, milestones, deliverables
- Tests added, PR number
- If failed: add to `failed_attempts:` section grouped by goal

## Known gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `mission_triggered: false` from `mission_start` | Prompt was too trivial — orchestrator decided no mission needed | Write a more substantial prompt with explicit features/milestones, OR if you wanted a one-shot answer use `droid_exec` instead |
| `state_file_exists_yet: false` for an existing mission | factoryd hasn't started workers yet (only `working_directory.txt` written so far) | Wait ~30 seconds and re-poll `mission_status` |
| Mission `uuid` returned but `mission_id` is `pending-<uuid>` | state.json hasn't been written yet | Wait — once factoryd starts, the real `mis_xxx` id appears |
| `worker_failed` events with `Spawn error: [daemon -> droid] Failed to send request` | factoryd worker spawn failure (upstream droid bug) | Restart `droid daemon`, or restart the mission. Not a mcp-droid bug. |
| `droid_session_list` doesn't show your recent session | sessions-index.json is incomplete — droid skips `droid exec` sessions | Pass `scan_disk: true` for the complete list |
| `droid_session_search` returns sessions from other projects | `droid search` is global — ignores cwd | Either pass the explicit `cwd:` you want, or accept the default (which post-filters to current cwd) |
| `droid exec --list-tools` output blew past MCP token limit | The full catalog with descriptions is ~98 KB | Use `mode: "compact"` (default — already slim) or `mode: "names"` for just IDs |
| `droid_spec` exits with code 1 and empty stderr | Spec mode is stochastic — sometimes the model tries to use a blocked tool after `ExitSpecMode` | mcp-droid defaults `auto: "low"` for spec mode to prevent this. If you override to read-only, it can recur. |
| Orphan `step1.txt`, `.factory/init.sh`, etc appear in nt-dev git status | A mission ran with `cwd = /Users/serkan/nt-dev` instead of `/tmp/...` | `git rm -rf .factory/ step*.txt && git commit` — and never run `mission_start` with nt-dev as cwd again |

More gotchas with deeper context: [`references/troubleshooting.md`](references/troubleshooting.md)

## Reference files

When you need details that don't fit in this main file:

- [`references/all-tools.md`](references/all-tools.md) — Full catalog of all 24 mcp-droid tools with example calls
- [`references/missions-deep-dive.md`](references/missions-deep-dive.md) — Mission lifecycle on disk, polling mechanics, prompt-writing tips
- [`references/troubleshooting.md`](references/troubleshooting.md) — Empirical findings from building mcp-droid: failure modes and fixes
- [`references/tmux-fallback.md`](references/tmux-fallback.md) — Full tmux + REPL flow for advanced cases (multi-day, live monitoring, multi-pane)
- [`scripts/mission-manager.sh`](scripts/mission-manager.sh) — Bash helper for the tmux flow (launch/list/peek/attach/kill)

## TL;DR

For 90% of cases: **use mcp-droid tools directly from Claude Code.** No tmux. No REPL. No `/model` ceremony. Just call `droid_research_fast` for research, `droid_review_code` after edits, `droid_explore_code` for navigation, `droid_mission_start` (with `cwd: "/tmp/..."`) for multi-feature work.

For multi-day missions where you need live observability or mid-run intervention: drop down to **tmux + REPL** via `scripts/mission-manager.sh`.

Always: **custom BYOK models only**, **never run missions in a git repo you care about**, **put every decision in the mission prompt** (no mid-run interaction is possible).
