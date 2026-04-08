# Missions deep dive — lifecycle, mechanics, prompt-writing

Everything you need to know about how droid missions actually work,
empirically verified while building mcp-droid.

## What is a mission?

A droid mission is a multi-feature autonomous orchestration:

1. The **orchestrator model** receives the user's prompt, plans
   features, and decides which workers to spawn.
2. **Worker sessions** are spawned via factoryd (the droid daemon),
   each one given a focused feature to implement.
3. A **validator model** runs after each milestone to check exit
   criteria, run tests, and decide whether to advance.
4. The orchestrator coordinates handoffs between workers and decides
   when to pause/complete the mission.

Missions persist their entire state to disk in
`~/.factory/missions/<uuid>/` so they survive process restarts and can
be inspected/replayed.

**Critically:** missions are **non-interactive by design**. They run
with `--auto high` which auto-approves every proposal. There is no
`AskUser` mid-run, no input mechanism, no way to course-correct from
outside. Verified empirically: zero AskUser calls and zero
user-input-needed events across 26 existing missions on disk.

## Lifecycle on disk

When you call `droid_mission_start`, this is what happens on disk:

```
t=0       droid exec --mission spawns
t=0..N    mission directory appears at ~/.factory/missions/<uuid>/
          - working_directory.txt    ← AUTHORITATIVE cwd, written FIRST
          - mission.md               ← prompt + plan from orchestrator
          - progress_log.jsonl       ← starts with {"type":"mission_accepted"}

t=N..M    factoryd spawns the first worker, eventually writes:
          - state.json               ← structured state, only once a worker actually runs
          - features.json            ← feature breakdown
          - model-settings.json
          - validation-contract.md
          - runtime-custom-models.json

t=M..end  workers run one at a time:
          - worker-transcripts.jsonl ← every tool call from every worker
          - handoffs/                ← per-feature handoff payloads (10 KB+ each)
          - evidence/                ← optional evidence files

End       state.json updated to "completed" / "failed" / "cancelled"
          progress_log.jsonl ends with {"type":"mission_completed"}
```

**Key insight:** `state.json` may not exist for many seconds, sometimes
never (if the mission stalls or factoryd fails). mcp-droid recognizes a
mission directory by `working_directory.txt` (always written first) and
falls back to a partial state with `mission_id: "pending-<uuid>"` and
`state: "initializing"` when state.json is missing.

## Why mcp-droid spawns missions detached

Two reasons:

1. **`droid exec --mission` blocks until the mission completes** (which
   can be hours). If mcp-droid awaited the spawn, the MCP request would
   block for the entire mission duration.

2. **Detached children survive parent exit.** mcp-droid uses
   `spawn(..., { stdio: ["ignore", logFd, logFd], detached: true })`
   followed by `child.unref()`. The mission keeps running under
   launchd/init even if the mcp-droid server exits.

mcp-droid then polls `~/.factory/missions/` for the new directory and
returns as soon as `working_directory.txt` appears. The user gets a
response within 10–30 seconds with the mission's uuid + the path to a
log file capturing droid's stdout/stderr for debugging.

## How polling works (the matching logic)

`pollForNewMissionDir` in `src/droid/missions.ts` of mcp-droid uses a
two-tier match:

1. **Tier 1 — exact match (preferred):** A new uuid (not in the
   "before" snapshot) whose `working_directory.txt` equals the spawn
   cwd. Returned immediately.

2. **Tier 2 — fallback:** A new uuid whose `working_directory.txt` is
   populated but DIFFERENT from spawn cwd. Held as a fallback for
   `fallback_hold_ms` (default 5s) while we keep looking for an exact
   match. If none appears, return the fallback.

**Why the fallback exists:** droid can re-root a mission's working
directory based on absolute paths it sees in the prompt. Verified:
a prompt mentioning "/tmp/foo/step1.txt" caused droid to set
`working_directory.txt` to `/tmp/foo`, NOT the cwd we spawned it with.
The fallback handles this case.

The response includes `working_directory_matches_spawn_cwd: boolean`
so callers know if droid honored their spawn cwd or chose its own.

## Trivial prompts don't trigger missions

Verified: `droid exec --mission --auto high "say hi"` completes in ~5
seconds as a plain single-turn exec and creates **zero** new mission
directories under `~/.factory/missions/`. The orchestrator decides
"this doesn't need multi-feature planning" and just answers directly.

mcp-droid detects this case (no new dir within the poll window) and
returns:

```json
{
  "mission_triggered": false,
  "reason": "no new mission directory appeared within the poll window. Common cause: prompt was too trivial...",
  "working_directory": "/tmp/...",
  "droid_pid": <pid>,
  "droid_log": "/var/folders/.../mcp-droid-mission-<timestamp>.log",
  "poll_timeout_ms": 120000
}
```

**This is not an error.** It's a structured signal that droid decided
no orchestration was warranted. If you wanted a one-shot answer, use
`droid_exec` or a preset instead. If you wanted a real mission, write
a more substantial prompt with explicit features and milestones.

## Polling for progress (the recommended pattern)

After `mission_start` returns, save the `uuid` and poll for updates:

```typescript
// First call — get initial state
mcp__mcp-droid__droid_mission_status({
  mission_id: "<uuid>",
  include_progress: true,
  progress_limit: 10,
})
```

For incremental polling (e.g., every 30 seconds in a loop), use
`droid_mission_progress` with `since_offset`:

```typescript
let offset = 0;
while (true) {
  const result = await mcp__mcp-droid__droid_mission_progress({
    mission_id: "<uuid>",
    since_offset: offset,
    limit: 50,
  });
  for (const event of result.events) {
    // handle event
  }
  offset = result.next_offset;
  if (result.is_complete) break;
  await sleep(30_000);
}
```

Event types you'll see (in rough order):

| Event | Meaning |
|---|---|
| `mission_accepted` | Orchestrator parsed the prompt, mission registered |
| `mission_run_started` | Workers about to spawn |
| `worker_selected_feature` | Orchestrator picked a feature for the next worker |
| `worker_started` | Worker session spawned, executing the feature |
| `worker_completed` | Worker finished — has a `handoff_summary` (or full `handoff` if `include_handoffs:true`) |
| `worker_failed` | Worker hit an error — `reason` field has details |
| `milestone_validation_triggered` | Validator running for a milestone exit |
| `mission_paused` | Mission stopped (manual or auto) |
| `mission_resumed` | Resumed after pause |
| `handoff_items_dismissed` | User-facing items dismissed in the orchestrator UI |
| `mission_completed` | Terminal state |

## Writing a good mission prompt

The mission prompt is the **only contract** between you and the
mission. There's no mid-run correction. Spend real effort here.

**Required sections:**

1. **Goal** — 1–2 sentences. What outcome do you want?
2. **Context** — Background, motivating bug/feature, relevant files.
3. **Scope** — Explicit IN SCOPE / OUT OF SCOPE lists. Be ruthless.
4. **Constraints** — Tech patterns, style rules, things that must NOT
   happen. Reference the project's rule files (e.g.
   `.claude/rules/tdd.md`).
5. **Milestones** — Phased delivery with concrete exit criteria per
   milestone. Each milestone should have a clear "done when X" check.
6. **Validation** — Exact commands to run, what to grep for, what
   tests must pass before the mission is complete.
7. **Reference files** — Paths to project rule files / docs the
   mission must read before starting.

**Standing template:**

```markdown
## Goal
{1–2 sentence outcome}

## Context
- {Key file 1 — what it does, why it matters}
- {Key file 2}
- {Recent bug or motivating incident}

## Scope
### IN SCOPE
- {item 1}
- {item 2}

### OUT OF SCOPE
- {item 1 — explicitly not part of this mission}
- {item 2}

## Constraints
- {pattern that must be followed, e.g. "DDD layering: api → application → domain → infrastructure"}
- {anti-pattern that must be avoided, e.g. "no `as any` casts"}
- {policy, e.g. "every catch must call Sentry.captureException with extra+tags"}
- Read first: {paths to rule files}

## Milestones

### Milestone 1: {name}
**Features:**
- {feature 1}
- {feature 2}

**Exit criteria:**
- {concrete, verifiable check 1}
- {concrete, verifiable check 2}

### Milestone 2: {name}
**Features:** {...}
**Exit criteria:** {...}

## Validation
At the end of every milestone, run:
- `pnpm typecheck` → 0 errors
- `pnpm test` → all 5366+ tests pass (405 suites)
- `pnpm lint` → ≤50 warnings, no new ones
- {custom grep checks for the specific mission}

## Reference files
- .claude/rules/tdd.md
- .claude/rules/{relevant rules}.md
```

**Tips that move the needle:**

- **TDD framing works extremely well.** Validators get concrete
  pass/fail signals. "Write the failing test, then fix it, then verify
  the test passes" is a contract the orchestrator can enforce per
  feature.

- **Audit/fix missions:** structure as **audit phase → fix phases →
  validation phase**. The audit phase produces a markdown file (e.g.
  `docs/audit-2026-04.md`) that the fix phases read. Cross-session
  memory via files is essential because workers spawn fresh.

- **Keep features narrow.** One focused task per worker session. If a
  feature feels like it does 3 things, split it.

- **Reference the project's rule files.** Workers don't have your
  CLAUDE.md context — you have to point them at the rules in the
  prompt's Constraints section.

- **Write down the validation commands explicitly.** "Run pnpm test"
  is enough only if the test framework is obvious. Better: include
  the exact expected outcome ("0 type errors", "5366+ tests pass",
  "no new lint warnings above the 50-warning threshold").

- **Be explicit about output artifacts.** "At the end of Milestone 1,
  produce `docs/silent-catch-audit-2026-04.md` containing every empty
  catch in scope, with file:line refs" is much better than "audit
  silent catches."

## Post-mission audit (always do this)

After a mission completes, **always** verify before merging anything:

1. **Diff the changes.** If the mission ran in `/tmp/mission-X` (as it
   should), there's no contamination of nt-dev. Diff the produced files
   into nt-dev manually if you want them.

2. **Run nt-dev's verification commands** from Claude Code (NOT from
   droid):
   ```bash
   pnpm typecheck    # 0 errors
   pnpm test         # all 5366+ tests pass
   pnpm lint         # ≤50 warnings
   ```

3. **Check for scope leaks.** Did the mission touch files outside its
   declared scope? Read the worker handoffs:
   ```typescript
   mcp__mcp-droid__droid_mission_status({
     mission_id: "<uuid>",
     include_handoffs: true,
     progress_limit: 100,
   })
   ```

4. **Read the test cases the mission added.** Make sure they're
   meaningful, not green-rubber-stamps. Validators check that tests
   PASS, not that tests are USEFUL. A worker can write `expect(true).toBe(true)`
   and the validator will be happy. Always review the actual test
   logic.

5. **Review the orchestrator's reasoning** in `worker-transcripts.jsonl`
   if anything looks off. Each entry shows the model's reasoning, tool
   calls, and tool results.

## Mission tracking in nt-dev

All missions (success and failure) are tracked in
`.factory/missions/missions.yaml`. Mission prompt files live in
`.factory/missions/prompts/`.

After a mission completes, update `missions.yaml` with:
- Mission ID, name, prompt file, machine, date, status
- Assertions passed/total, milestones, deliverables
- Tests added, PR number
- If failed: add to `failed_attempts:` section grouped by goal

## When to use tmux/REPL instead

mcp-droid `mission_start` is the right path for 90% of missions. Drop
down to the tmux/REPL flow only when:

1. **Multi-day missions where you want live observability** — the
   mcp-droid `droid_log` file captures stdout but you'd want to
   `tail -f` it actively, and tmux is more ergonomic for that.

2. **Mid-mission manual intervention** — sometimes a long mission
   stalls or goes off-track and you need to type a course-correction
   into the REPL. mcp-droid can't do that.

3. **Setting worker/validator models separately from the orchestrator.**
   mcp-droid passes `--model X` which sets the orchestrator. Worker
   and validator come from `~/.factory/settings.json missionModelSettings`
   and are persistent. If you want to OVERRIDE worker/validator for one
   mission, you have to do it via `/model` in the REPL.

4. **Hetzner VPS missions** where you want to attach from a local Mac
   via SSH+tmux.

See [`tmux-fallback.md`](tmux-fallback.md) for the full REPL flow.

## Empirical findings worth knowing

These came from building and testing mcp-droid itself.

- **Both model id forms work**: `custom:glm-5-turbo` and
  `custom:BYOK-GLM-5-Turbo-33` are interchangeable in droid CLI. No
  alias resolution needed.

- **`--output-format json` is unsafe**: droid can exit 0 with errors
  hidden in the JSON payload. Always use `stream-json`. mcp-droid
  defaults to stream-json everywhere.

- **`droid search` is global**: ignores cwd entirely, even when run
  from a project directory. mcp-droid's `droid_session_search`
  post-filters by reading each hit's `.jsonl` first line.

- **`sessions-index.json` is incomplete**: droid skips sessions
  created via `droid exec` (which is how mcp-droid creates them).
  142 entries on disk vs 214 actual `.jsonl` files in our test setup.
  Use `scan_disk: true` in `droid_session_list` for completeness.

- **`droid_list_tools` returns 98 KB by default**: 114 tools with
  multi-paragraph descriptions. mcp-droid defaults to `mode: "compact"`
  (~20 KB) which strips descriptions but keeps id/display_name/category.

- **factoryd worker spawn failures** sometimes happen with the message
  `Spawn error: [daemon -> droid] Failed to send request`. Upstream
  droid bug — mcp-droid surfaces it via the `worker_failed` events but
  can't fix it. Workaround: restart the mission or restart `droid daemon`.
