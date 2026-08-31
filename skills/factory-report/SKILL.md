---
name: factory-report
description: Use when the user runs "/factory-report" or asks how the factory is performing — "how long are goals taking", "check timing", "monitor performance", "what's the factory costing", "which goals are slow", "are agents getting stuck". Reports goal timing, agent cost, and the three execution failure modes (runaway, hung, oversized) across every repo with a docs/goals queue, from git history plus the factory event log. Strictly read-only — it measures the factory, never changes the queue, and never implements anything.
---

# Factory Report

One read-only view of how the factory is actually performing, across **every**
repo on the machine that has a `docs/goals` queue — not one repo at a time.
Answers "is it getting faster", "what is it costing", and "which goals went
wrong and how".

Read-only, always. It never claims a goal, writes `index.yaml`, edits a
contract, or implements anything.

## Where the numbers come from

Three sources, and the skill prefers the most trustworthy one for each number:

1. **git `chore(goals):` commits** — the authoritative goal clock. Every claim
   and every terminal flip is a commit with an author date the agent did not
   write. This works retroactively, over repos that never had the event log on,
   and it cannot be fabricated. Goal timing ALWAYS comes from here.
2. **the factory event log** — `~/.local/state/pg-factory/events.ndjson`, one
   machine-wide file written by the plugin's hooks on both harnesses. This is
   the only source for agent lifecycles, tool-call counts, and session cost.
   Absent before logging was enabled; that is normal, and the report says so
   rather than failing.
3. **`index.yaml` / `archive.yaml`** — status and queue depth. The stamped
   `claimed_at` / `settled_at` are cross-checked against git and never trusted
   over it (they were measurably fabricated before v12.7.0).

## Run

One command. Run it as a single block — don't split the resolution into
separate calls. It does not matter which repo you are in; the report is
machine-wide.

```bash
FR="$CLAUDE_PLUGIN_ROOT/skills/factory-report/scripts/factory_report.py"
[ -f "$FR" ] || FR=$(find ~/.claude/plugins ~/.factory/plugins/cache -path '*/flywheel/*/skills/factory-report/scripts/factory_report.py' 2>/dev/null | sort -V | tail -1)
[ -n "$FR" ] && python3 "$FR" --days 7 || echo "factory_report.py not found — reinstall/update the flywheel plugin"
```

`--days N` sets the window (default 7). `--json` emits the same data as
structured JSON for further analysis. `--roots` overrides where to look for
repos (default: `~` and `~/*`).

Exit `2` means no repo with a `docs/goals` queue was found — say so plainly and
stop; do not invent numbers from anywhere else.

## Reading the three failure signals

The report separates three things that all look identical from the outside —
"the goal took two hours". Each has its own signal and its own fix, and
confusing them is how the wrong fix gets applied.

| Mode | Signal | What it means |
|---|---|---|
| **Runaway** | tool calls far above normal, no gaps | The agent worked flat out and got nowhere. A healthy worker's p90 is ~105 tool calls; the threshold is 300. Measured on 494 workers, only two ever passed 300 and **both failed** — it is close to a certain predictor. The goal is too big or the agent is thrashing. |
| **Hung** | a long silence mid-run | The agent stopped emitting events entirely. Inside a working agent the largest normal gap is about a minute, so a 15-minute silence is never work in progress. Field cases ran 5 and 8 hours silent. |
| **Oversized** | long but healthy | Many tool calls spread evenly, no gaps, and it finishes. Nothing is broken — the contract was simply too big for one sitting. The fix is upstream, in define-goal. |

**These are reporting-only.** Nothing in this skill or in dispatch stops an
agent on these thresholds. They were set from one repo mix and need real data
behind them before anything acts on them; report them, name the mode, and let
the owner decide.

## Publishing the report

Chat output is the norm and the fallback. When the session's tools include the
**Artifact** tool (built into Claude Code, needs a claude.ai login, can be
disabled, absent on Droid and headless), ALSO publish the report as a designed
page — it is a dense table-and-trend document and reads far better as one.

- ONE publish per invocation.
- Reuse the SAME artifact across runs so the owner keeps one stable URL:
  find it with the Artifact tool's `list` action (its title is
  `Factory Report`), read it, and republish to that `url`. Only mint a new
  artifact when none exists.
- The markdown/terminal output stays canonical. The page is a reading surface,
  never a second source of truth.

Where the tool is absent, print the helper's output verbatim and stop. Never
write an HTML file to the repo as a substitute.

## Enabling the event log

The hooks ship with the plugin but are **opt-in and inert by default** — the
log directory is the switch, so installing flywheel changes nothing until
someone turns it on:

```bash
mkdir -p ~/.local/state/pg-factory     # enable
rm -rf   ~/.local/state/pg-factory     # disable, and delete what was collected
```

When the report says `no event log yet`, offer that one line. Do not enable it
silently — it starts recording on someone's machine.

What it records, per event: timestamp, harness, session id, agent id and type,
working directory, tool NAME, and — for a `chore(goals):` commit — the verb and
goal id. What it never records: prompt text, tool inputs, tool outputs, file
contents, environment values, or command bodies. A free-text prompt leaves only
the fact that a prompt happened; a slash command leaves only its name.

The log rotates at 64 MB and costs about 9 ms and 100 bytes per tool call.

If the log stays empty after enabling, the hook path failed silently — `async: true`
hides hook errors on Claude Code. Re-run one probe with `async` removed from the
installed `hooks/hooks.json` and the real error prints.

## Boundaries

- Never claims, amends, blocks, or retires a goal — that is `/dispatch` and
  `/define-goal`.
- Never edits a contract or a plan on the strength of a slow number. A slow
  goal is evidence for the owner, not a licence to rewrite the queue.
- Never presents stamped `claimed_at`/`settled_at` durations as the measurement
  when git disagrees; git wins, and a disagreement is itself worth reporting.
- For what is currently OPEN in one repo's queue, that is `/goals-status` — this
  skill measures history, not the work in front of you.
