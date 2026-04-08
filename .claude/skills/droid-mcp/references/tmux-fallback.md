# Tmux + REPL fallback for advanced missions

For most missions, use `mcp__mcp-droid__droid_mission_start` (see the
main SKILL.md). This reference covers the **tmux + interactive `droid`
REPL** flow for the minority of cases where mcp-droid isn't enough.

## When to use this instead of mcp-droid

Drop down to tmux/REPL only when:

1. **Multi-day missions where you want live observability.** mcp-droid
   logs droid's stdout to a file but doesn't tail it for you. tmux is
   better for actively watching a mission over hours/days.

2. **Mid-mission manual intervention.** If a long mission stalls or
   goes off-track, the tmux REPL lets you type a course-correction
   directly to the orchestrator. mcp-droid missions are non-interactive
   and can't be steered mid-run.

3. **Setting worker/validator models separately from the orchestrator.**
   mcp-droid's `mission_start` passes `--model X` which sets the
   orchestrator. Worker and validator come from
   `~/.factory/settings.json missionModelSettings` and are persistent.
   If you want to OVERRIDE worker/validator for one specific mission,
   you have to do it via `/model` in the REPL — mcp-droid doesn't
   expose per-role model selection.

4. **Hetzner VPS missions** where you want to attach from a local Mac
   via SSH+tmux for live monitoring.

For everything else, mcp-droid `mission_start` is simpler, faster, and
doesn't require any tmux ceremony.

## Why tmux (instead of raw `droid`)?

Droid missions can run for hours or days (median ~2 hours, up to 16
days). Without tmux, closing your terminal kills the orchestrator
process and the mission stops. tmux keeps the process alive across
disconnections, SSH drops, and laptop closures.

**Important:** the orchestrator coordination state is lost on crash.
Worker artifacts survive in git (they commit directly), but recovering
the orchestrator flow is manual and painful. So you want the
orchestrator to NOT die — tmux is the way.

## Quick reference

| Task | Command |
|---|---|
| Launch new mission | `tmux new -s mission-{name}` then `cd {repo} && droid` then `/enter-mission` |
| Detach (keep running) | `Ctrl+B, D` |
| List sessions | `tmux ls` |
| Reattach | `tmux attach -t mission-{name}` |
| Kill session | `tmux kill-session -t mission-{name}` |
| Scroll output | `Ctrl+B, [` then arrow keys, `q` to exit |
| Peek without attaching | `tmux capture-pane -t mission-{name} -p \| tail -50` |
| Check droid version | `droid --version` |

The `mission-manager.sh` helper script wraps all of these — see below.

## Launch a new mission (full flow)

### Step 1: Create a named tmux session

```bash
tmux new -s mission-{descriptive-name}
```

Naming convention: `mission-{feature}` format. Examples:
`mission-federal-tax-audit`, `mission-api-refactor`,
`mission-docuseal-consolidation`.

### Step 2: Navigate to repo and start droid

```bash
cd /Users/serkan/nt-dev
droid
```

(Or `cd ~/nt-dev` on Hetzner.)

### Step 3: Enter mission mode

Inside the droid REPL:

```
/enter-mission
```

### Step 4: CRITICAL — Set the orchestrator model

```
/model
```

Then navigate:
- Select "Orchestrator model"
- Choose a custom model: `VP: Opus 4.6 1M (xHigh)` under Custom Models

**The orchestrator ALWAYS resets to Factory's built-in model on every
`/enter-mission`.** Worker and Validator persist in
`~/.factory/settings.json missionModelSettings`, but the orchestrator
does NOT. This step is required EVERY session — there is no way to
persist it.

Skip this step = "Token limit reached" error a few hours into the
mission, because Factory's built-ins have token quotas that custom BYOK
models don't.

### Step 5: Describe the goal

Answer droid's planning questions thoroughly. The planning conversation
is where mission quality is determined.

### Step 6: Approve the plan

When droid presents the plan and you're satisfied, approve it.

### Step 7: Detach

```
Ctrl+B, then D
```

The mission continues running in the background. You can now close
your terminal, ssh out, whatever — the tmux session keeps the droid
orchestrator alive.

## Launch with a prompt file

For complex missions, write the prompt to a file first:

```bash
cat > /tmp/mission-prompt.md << 'EOF'
## Goal
{mission prompt content}

## Scope
...
EOF
```

Then launch droid with the prompt as an initial input:

```bash
tmux new -s mission-{name}
cd /Users/serkan/nt-dev
droid "$(cat /tmp/mission-prompt.md)"
# Then type /enter-mission inside the REPL
```

Or for a fully scripted launch (advanced):

```bash
tmux new -s mission-{name} \; send-keys "cd /Users/serkan/nt-dev && droid '/enter-mission'" Enter
```

## Monitor a running mission

### Peek without attaching (preferred — doesn't disturb the session)

```bash
# Last 50 lines
tmux capture-pane -t mission-{name} -p | tail -50

# Or use the helper
bash .claude/skills/droid-mcp/scripts/mission-manager.sh peek {name} 50
```

### Attach to watch live

```bash
tmux attach -t mission-{name}
# Detach again: Ctrl+B, D
```

**While attached**, you can scroll back with `Ctrl+B, [` (then arrow
keys) and exit scroll mode with `q`.

### Monitor multiple missions in one screen

```bash
tmux new -s monitor
# Ctrl+B, % — vertical split
# Ctrl+B, " — horizontal split

# In each pane, run:
watch -n 10 'tmux capture-pane -t mission-{name} -p 2>/dev/null | tail -20'
```

Or use the helper script:

```bash
bash .claude/skills/droid-mcp/scripts/mission-manager.sh monitor 10
# Refreshes every 10 seconds, showing all mission sessions
```

## Recover from a stall

If a mission appears frozen (no activity for 10+ minutes):

1. Check what factoryd is doing:
   ```bash
   pgrep -f "droid daemon"
   ```

2. Reattach to the mission:
   ```bash
   tmux attach -t mission-{name}
   ```

3. Type directly to the droid REPL:
   ```
   The mission appears stalled. The last worker finished over 10
   minutes ago. Please re-assess progress and continue from where you
   left off. If a worker is blocked, fail it and move on to the next
   feature.
   ```

4. Detach and let it resume (`Ctrl+B, D`).

5. If daemon is stuck, restart it:
   ```bash
   pkill -f "droid daemon"
   # droid will auto-restart factoryd when needed
   ```

## Clean up

### Kill one mission

```bash
tmux kill-session -t mission-{name}
# Or:
bash .claude/skills/droid-mcp/scripts/mission-manager.sh kill {name}
```

### Kill all missions

```bash
tmux ls | grep "^mission-" | cut -d: -f1 | xargs -I{} tmux kill-session -t {}
# Or:
bash .claude/skills/droid-mcp/scripts/mission-manager.sh kill-all
```

### Check for orphans

```bash
tmux ls
```

## Using mission-manager.sh

The helper script at
`.claude/skills/droid-mcp/scripts/mission-manager.sh` wraps the
common tmux operations. All commands support an optional `{name}` arg
that maps to `mission-{name}` session.

```
bash mission-manager.sh launch <name> [repo-path]    # Create tmux session and start droid
bash mission-manager.sh list                         # List all mission tmux sessions
bash mission-manager.sh status <name>                # Show last 30 lines
bash mission-manager.sh peek <name> [lines]          # Show last N lines (default 30)
bash mission-manager.sh attach <name>                # Reattach
bash mission-manager.sh kill <name>                  # Kill one
bash mission-manager.sh kill-all                     # Kill all mission sessions
bash mission-manager.sh monitor [interval]           # Watch all sessions (default 10s)
```

After `launch`, droid will start inside the tmux session. You still
need to run `/enter-mission` and `/model` manually — the script
doesn't automate those (and shouldn't, because the orchestrator model
selection depends on the machine).

## Model configuration for missions (tmux flow)

Worker and Validator models persist in
`~/.factory/settings.json missionModelSettings`. Orchestrator does NOT
— set via `/model` every session.

### Local Mac (vibeproxy on localhost:8319)

| Role | Model ID | Display Name |
|---|---|---|
| Orchestrator | `custom:VP-Opus-4.6-1M-xHigh-44` | VP: Opus 4.6 1M (xHigh) |
| Worker | `custom:VP-Opus-4.6-1M-Med-46` | VP: Opus 4.6 1M (Med) |
| Validator | `custom:VP-Opus-4.6-1M-xHigh-44` | VP: Opus 4.6 1M (xHigh) |

### Hetzner VPS (vibeproxy on 127.0.0.1:8317)

| Role | Model ID | Display Name |
|---|---|---|
| Orchestrator | `custom:VP-Opus-4.6-1M-xHigh-0` | VP: Opus 4.6 1M (xHigh) |
| Worker | `custom:VP-Opus-4.6-1M-Med-2` | VP: Opus 4.6 1M (Med) |
| Validator | `custom:VP-Opus-4.6-1M-xHigh-0` | VP: Opus 4.6 1M (xHigh) |

Model IDs differ between machines because they're auto-assigned
incrementally. Verify with:

```bash
grep customModels ~/.factory/settings.json | head
# Or better:
python3 -c "
import json
d = json.load(open('/Users/serkan/.factory/settings.json'))
for m in d.get('customModels', []):
    print(m['id'], '→', m.get('displayName'))
"
```

## Known issues (tmux flow)

### Token limit on orchestrator

**Symptom:** Mission fails a few hours in with "Token limit reached".

**Cause:** Orchestrator is using a Factory built-in model, not a
custom BYOK one.

**Fix:** After `/enter-mission`, ALWAYS run `/model` and set the
orchestrator to a `custom:VP-Opus-4.6-1M-xHigh-*` entry. This is the
#1 mistake in the tmux flow.

### GPT-5.4 not supported for missions

**Symptom:** Mission workers produce empty completions, or the daemon
crashes mid-mission.

**Cause:** GPT-5.4 fails in mission mode. Verified — not a bug we can
fix.

**Fix:** Use Opus 4.6 1M family only. Never use GPT-5.4 for any
mission role.

### TTY blocking from shell plugins (macOS)

**Symptom:** `droid daemon` fails to start or hangs.

**Cause:** Shell plugins like `zsh-autosuggestions`, `starship`,
`forge`, `oh-my-zsh` block the daemon when sourced in a non-interactive
context. See droid GitHub issue #794.

**Fix:** Wrap interactive-only plugins in a TTY check in `.zshrc`:

```bash
if [[ -o interactive ]] && [[ -t 0 ]]; then
  # zsh-autosuggestions, starship, etc. here
fi
```

### Concurrent mission limits

**Symptom:** Running 3+ missions simultaneously crashes the daemon.

**Fix:** Run missions sequentially. Max 2 concurrent if you must
parallelize.

## Headless `droid exec` from within tmux (scripting fallback)

For one-off scripted tasks that don't need a full mission, `droid exec`
can be used directly (this is what mcp-droid does under the hood for
every tool except `mission_start`):

```bash
# One-shot headless execution
droid exec "analyze code quality in src/features/federal-tax" --auto low

# From a prompt file
droid exec -f /tmp/task-prompt.md --auto medium

# Continue a previous session
droid exec --session-id <id> "continue with the next step"

# JSON output for scripting
droid exec -o stream-json "list all TODO comments" --auto low
```

**Autonomy levels:**

| Level | Allows |
|---|---|
| (default, no flag) | Read-only — file reads, git reads, no modifications |
| `--auto low` | + file creation/editing in non-system dirs |
| `--auto medium` | + npm/pip install, network, local git ops |
| `--auto high` | + curl\|bash, git push, production deploys |

For most tasks, prefer the mcp-droid equivalent (`droid_exec`,
`droid_research`, etc.) because you get parsed results and structured
responses. Use raw `droid exec` only when scripting in bash or when
you're inside a tmux REPL working interactively.

## Post-mission audit (same as mcp-droid path)

Regardless of which flow you used (tmux or mcp-droid), always audit
before merging:

1. Run nt-dev verification commands:
   ```bash
   pnpm typecheck    # 0 errors
   pnpm test         # all 5366+ tests pass
   pnpm lint         # ≤50 warnings
   ```

2. Read `git diff` for every changed file. Review each change.

3. Check for scope leaks — did the mission touch files outside its
   declared scope?

4. Read the new test cases. Make sure they're meaningful.

5. Update `.factory/missions/missions.yaml` with the mission results.
