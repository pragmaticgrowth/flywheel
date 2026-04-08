# Troubleshooting — empirical findings from building and testing mcp-droid

Each entry: symptom → cause → fix. All verified empirically.

## `mission_triggered: false` from `droid_mission_start`

**Symptom:** You called `mission_start` and got back
```json
{ "mission_triggered": false, "reason": "...too trivial...", "text": "...", "base_session_id": "..." }
```

**Cause:** The prompt was too simple. The orchestrator decided no
multi-feature planning was warranted and just answered as a single-turn
exec. **Verified:** `droid exec --mission "say hi"` completes in ~5
seconds and creates zero new mission directories.

**Fix:** Either
- Use `droid_exec` or a preset (`droid_research`, etc) for one-shot
  questions, OR
- Rewrite the mission prompt with explicit multi-feature structure
  (Goal, Scope, Milestones, Validation — see SKILL.md prompt template).
  Real missions need substantial scope.

## `state_file_exists_yet: false` for an existing mission

**Symptom:** `mission_status` returns
```json
{ "mission_id": "pending-<uuid>", "state": "initializing", "state_file_exists_yet": false }
```

**Cause:** The mission directory was created (we have
`working_directory.txt` and `mission.md`), but factoryd hasn't yet
spawned a worker, so `state.json` doesn't exist.

**Fix:** Wait 10–60 seconds and re-poll. Once a worker actually starts,
factoryd writes `state.json` and `mission_id` becomes the real
`mis_xxx`. If `state.json` never appears after several minutes, the
upstream factoryd spawn bug (next entry) is likely.

## `worker_failed` events with `Spawn error: [daemon -> droid] Failed to send request`

**Symptom:** Mission progress shows
```json
{ "type": "worker_failed", "spawnId": "worker_...", "reason": "Spawn error: [daemon -> droid] Failed to send request" }
```

**Cause:** factoryd (the droid daemon) failed to spawn a worker
session. This is an **upstream droid bug**, not mcp-droid. Sometimes
the daemon goes into a bad state — usually because of TTY blocking
from shell plugins (zsh-autosuggestions, starship, oh-my-zsh, forge).
See droid GitHub issue #794.

**Fix:**
1. Check whether droid daemon is reachable: `pgrep -f "droid daemon"`
2. If running, kill and let it restart: `pkill -f "droid daemon"`
3. Workaround the TTY blocking by wrapping interactive shell plugins:
   ```bash
   if [[ -o interactive ]] && [[ -t 0 ]]; then
     # zsh-autosuggestions, starship, etc here
   fi
   ```
   in your `.zshrc`.
4. Restart the mission. mcp-droid surfaces the failure via
   `worker_failed` events but can't fix the upstream issue.

## `droid_session_list` doesn't show your recent session

**Symptom:** You just created a session via `droid_exec` (or
mcp-droid did internally) and `droid_session_list` doesn't include it.

**Cause:** `~/.factory/sessions-index.json` is **incomplete**. Droid's
indexer skips sessions created via `droid exec` (the automation path —
which is how mcp-droid creates every session). Verified: 142 indexed
entries vs 214 actual `.jsonl` files on disk.

**Fix:** Pass `scan_disk: true`:
```typescript
mcp__mcp-droid__droid_session_list({ all: true, scan_disk: true })
```
The disk-walk path is slower (~200ms for ~200 sessions) but complete.

## `droid_session_search` returns sessions from other projects

**Symptom:** You ran `droid_session_search` from inside nt-dev expecting
nt-dev sessions, but got hits from `/Users/serkan/hetzner` and other
projects.

**Cause:** The underlying `droid search` CLI is **global** — it has no
`--cwd` flag and ignores the cwd it's run from. mcp-droid's
`droid_session_search` post-filters the results by reading each hit's
`.jsonl` first line for the authoritative cwd. The default filter
matches the current cwd.

**Fix:** Default behavior (filter to current cwd) is usually right. If
you wanted ALL projects, pass `all: true`. If you wanted a specific
other cwd, pass it explicitly:
```typescript
mcp__mcp-droid__droid_session_search({
  query: "JWT rotation",
  cwd: "/Users/serkan/nt-dev",  // explicit
})
```

## `droid_list_tools` blew past the MCP per-result token limit

**Symptom:** `droid_list_tools` saved the result to a side file with a
"too large" message instead of returning inline.

**Cause:** The default droid `--list-tools --output-format json` output
is ~98 KB for 114 tools (each tool has a multi-paragraph description).
That exceeds Claude Code's per-tool-result token limit.

**Fix:** mcp-droid's `droid_list_tools` defaults to `mode: "compact"`
which strips descriptions and returns ~20 KB. If you got the overflow,
you probably explicitly passed `mode: "full"`. Use `"compact"` (default)
or `"names"` (just IDs, ~5 KB) instead:
```typescript
mcp__mcp-droid__droid_list_tools({ mode: "names" })
```

## `droid_spec` exits with code 1 and empty stderr

**Symptom:** `droid_spec` returns `isError: true` with text like
`droid exec failed (nonzero_exit): droid exec exited with code 1`
and no stderr details.

**Cause:** Spec mode is stochastic — after the model calls
`ExitSpecMode` to approve the spec, it sometimes tries to execute on
the approved plan (Create/Edit/Execute tool calls). Without an `auto`
level set, those tool calls are blocked, and depending on how the model
recovers, droid can exit 1.

**Fix:** mcp-droid defaults `droid_spec` to `auto: "low"` to prevent
this. If you explicitly overrode `auto` to undefined or a level that
blocks the relevant tools, the failure can recur. Just leave `auto`
unset (default `"low"` will be used).

## Orphan `step1.txt`, `.factory/init.sh`, etc appear in nt-dev `git status`

**Symptom:** After running a mission, your nt-dev git status shows
new untracked or modified files like `step1.txt`, `step2.txt`,
`.factory/init.sh`, `.factory/services.yaml`,
`.factory/validation/scrutiny/*` etc.

**Cause:** A mission ran with `cwd: "/Users/serkan/nt-dev"` (or you
called `droid_mission_start` from within the nt-dev directory without
overriding cwd). Droid runs with `--auto high` and **commits its
mission scaffolding into the cwd's git repo**. This bypasses
`.gitignore` for previously-tracked files. Verified three times on the
mcp-droid project itself.

**Fix:**
```bash
cd /Users/serkan/nt-dev
git rm -rf .factory/ step*.txt hello.sh hello.ts 2>/dev/null
git commit -m "chore: remove droid mission debris"
```

**Prevention:** ALWAYS pass `cwd: "/tmp/mission-<unique>"` when calling
`droid_mission_start`:
```typescript
mcp__mcp-droid__droid_mission_start({
  cwd: "/tmp/mission-feature-x",   // ← throwaway, not nt-dev
  ...
})
```

## "Token limit reached" error during a mission

**Symptom:** Mission stalls or fails partway through with a token
limit error (in tmux/REPL flow).

**Cause:** The orchestrator is using a Factory built-in model that has
token quotas, instead of a custom BYOK model with no limits.

**Fix:**
- **For mcp-droid `mission_start`:** Pass `model: "custom:VP-Opus-4.6-1M-xHigh-44"`
  (or whatever the right machine-specific id is — see SKILL.md "nt-dev
  specifics"). This propagates to the orchestrator.
- **For tmux/REPL flow:** After `/enter-mission`, run `/model` and set
  Orchestrator to a `custom:VP-Opus-4.6-1M-xHigh-*` entry. The
  orchestrator resets to the built-in on every `/enter-mission` —
  this step is required EVERY session in the REPL flow.

## "GPT-5.4 produces empty completions"

**Symptom:** Mission worker completes "successfully" but the handoff
is empty or trivial. Or the daemon crashes mid-mission.

**Cause:** GPT-5.4 has been observed to fail in mission mode when its
quota runs out — the daemon can crash and the model produces empty
completions even before that. Verified at nt-dev project.

**Fix:** **Never use GPT-5.4 for any mission role**. Use Opus 4.6 1M
family for orchestrator/worker/validator. mcp-droid's default
`custom:glm-5-turbo` is fine for non-mission presets, but for missions
specifically, prefer Opus 4.6 1M:
```typescript
mcp__mcp-droid__droid_mission_start({
  model: "custom:VP-Opus-4.6-1M-xHigh-44",  // local Mac
  // model: "custom:VP-Opus-4.6-1M-xHigh-0", // Hetzner
  ...
})
```

## "Concurrent missions cause daemon crashes"

**Symptom:** Running 3+ missions in parallel causes factoryd to crash.

**Cause:** Upstream droid bug. The daemon doesn't handle high
concurrent worker spawn load.

**Fix:** Run missions sequentially. Max 2 concurrent if you must
parallelize. Wait for one mission to complete before starting another.

## Tools out of date — "tool not found" or stale schemas

**Symptom:** Calling a mcp-droid tool from a fresh Claude Code session
fails with "tool not found" or with a schema that doesn't match the
current code.

**Cause:** Claude Code spawned the mcp-droid stdio server before the
latest `dist/` was built, so it's running a stale binary.

**Fix:**
1. Rebuild: `cd /Users/serkan/mcp-droid && npm run build`
2. **Restart your Claude Code session** — stdio MCP servers don't
   hot-reload. The next session will spawn a fresh subprocess against
   the new dist.
3. Verify: in a fresh session, run `claude mcp get mcp-droid`. It
   should show "Status: ✓ Connected".

## "Cannot find mcp-droid tools at all"

**Symptom:** No `mcp__mcp-droid__*` tools available in the current
Claude Code session.

**Cause:** mcp-droid isn't registered in this session's scope. Check:
- `claude mcp list` should show `mcp-droid` as Connected
- If not in `claude mcp list`, it's not registered at user OR project
  scope

**Fix:** Register at user scope (works from anywhere):
```bash
claude mcp add -s user mcp-droid -- node /Users/serkan/mcp-droid/dist/index.js
```
Then restart Claude Code.

## Mission appears to have no progress for 10+ minutes

**Symptom:** `mission_status` shows the same state and same recent
events for many minutes — no new `worker_started` / `worker_completed`.

**Cause:** Could be:
1. Worker is doing real, long work (e.g. reading a large codebase,
   running a long test suite). Check `worker-transcripts.jsonl`.
2. factoryd worker spawn failed silently — check for `worker_failed`
   events further back in the progress log.
3. The orchestrator is stalled waiting for itself. Rare but happens.

**Fix:**
1. **Check the worker transcript directly:**
   ```bash
   tail -50 ~/.factory/missions/<uuid>/worker-transcripts.jsonl
   ```
   If you see active reasoning/tool calls, it's just slow — wait.
2. **Check the droid log file** mcp-droid produced at start time
   (`droid_log` field in the start response):
   ```bash
   tail -100 /var/folders/.../mcp-droid-mission-<timestamp>.log
   ```
3. **For tmux/REPL missions**, reattach and tell the orchestrator:
   ```
   The mission appears stalled. Last worker finished over 10 minutes
   ago. Re-assess progress and continue.
   ```
   For mcp-droid missions there's no equivalent — kill the droid_pid
   and start a new mission with refined prompt.

## How to kill a runaway mission

**For mcp-droid missions:** No `droid_mission_cancel` tool exists in
v1. Kill the droid process directly:
```bash
# Find the pid (mcp-droid returned droid_pid in the start response)
kill <droid_pid>
# Or find via process name
pkill -f "droid exec --mission"
```
Note: this kills the orchestrator. factoryd workers may still be
running — `pkill -f "droid"` more aggressively if needed.

**For tmux/REPL missions:**
```bash
bash .claude/skills/droid-mcp/scripts/mission-manager.sh kill <name>
```
Or manually: `tmux kill-session -t mission-<name>` then `pkill -f droid`
to clean up workers.
