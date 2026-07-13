---
name: goals-status
description: Use when the user runs "/goals-status" or asks what's in the docs/goals queue — what's left, what's blocked, what's in progress, or "show me the open goals". Prints a read-only view of the OPEN goals (in_progress, blocked, not_started), each with its title and brief; completed goals are hidden. Shows the queue only — never claims a goal, changes queue state, or implements anything (that's /dispatch).
---

# Goals Status

Show the open work in a repo's `docs/goals` queue at a glance: every goal that is
**in_progress**, **blocked**, or **not_started**, with its title and a one-line
brief. Completed goals are hidden (just counted). This is a **read-only** view —
it never writes to `docs/goals/` (dispatch owns queue state).

The shipped helper does all the parsing deterministically; you just run it and
present its output.

## Run

1. **Resolve the helper path.** `$GS` = `goals_status.py`, via the same fallback
   chain the other flywheel scripts use:
   `$CLAUDE_PLUGIN_ROOT/skills/goals-status/scripts/goals_status.py`, else the
   newest match of
   `~/.claude/plugins/{cache,marketplaces}/*/flywheel/*/skills/goals-status/scripts/goals_status.py`.
   Hold the resolved absolute path in `$GS`.

2. **Run it** from the target repo (it finds `docs/goals/` from the git root):
   - `python3 "$GS"` — default detailed view (grouped, title + brief + reason /
     waiting-on).
   - `python3 "$GS" --compact` — one line per goal.
   - `python3 "$GS" --json` — machine-readable, for scripting or further work.
   - `python3 "$GS" --dir <path/to/docs/goals>` — point at a queue explicitly.

   It exits `0` on success (including an empty or all-completed queue) and `2`
   when there is no `docs/goals/index.yaml` (it prints a hint to run
   `/factory-doctor`). If the index exists but is malformed YAML, it still shows
   a best-effort read and emits a `⚠ … best-effort` warning (on stderr for the
   text views, and as a `warning` field in `--json`) — surface that, don't treat
   a short/empty result as authoritative. It is read-only and never mutates.

3. **Present the output verbatim.** The helper's formatting is the deliverable —
   don't re-summarize or reorder it. If the run needs a decision (e.g. the queue
   is missing or malformed), relay the helper's message.

   `--json` shape: `{"open": N, "completed": M, "goals": [ {id, status, title,
   type, model, brief, reason, waiting_on, ready} … ] }` (plus `warning` on a
   malformed index; `{"error": …}` with exit 2 when there's no queue).

## Reading the output

- Groups render in the order **in_progress → blocked → not_started**; within a
  group, goals are id-sorted.
- Each goal shows `id`, a `type · model` tag, its **title**, and a `›` **brief**
  (the goal file's `## Outcome (plain language)` paragraph).
- A **blocked** goal shows its `✗ reason:` (from the index entry). A
  **not_started** goal that is waiting on an unfinished dependency shows
  `⏳ waiting on <ids>`; a not_started goal with no note is ready to dispatch.
- The header counts completed goals (in the index plus `archive.yaml`) but never
  lists them — this view is about what's still open.

## Boundaries

Read-only and reporting only. This skill never claims, completes, blocks, or
edits a goal, never touches `index.yaml`, and never starts implementation work —
that is `/dispatch`. To add goals use `/define-goal`; to fix a missing or broken
queue use `/factory-doctor`.
