#!/bin/sh
# flywheel — factory event log.
#
# OPT-IN: does nothing unless the log directory already exists.
#   enable:  mkdir -p ~/.local/state/pg-factory
#   disable: rm -rf ~/.local/state/pg-factory
#
# Writes ONE ndjson line per event to a single machine-wide file shared by every
# repo and both harnesses. METADATA ONLY — never a prompt body, tool input, tool
# output, file content, or environment value. The one string it reads out of a
# command is a `chore(goals):` queue flip, and it keeps only the verb and goal id.
#
# Runs on every tool call, so it must stay cheap: one jq, one append, exit 0
# always. A failure here must never break the session.

set -u

DIR="${PG_FACTORY_LOG_DIR:-$HOME/.local/state/pg-factory}"
[ -d "$DIR" ] || exit 0

# A missing jq is otherwise a SILENT death: every jq-shaped line below would fail and
# the log would just stay empty (or stop growing) forever, with no visible error and
# no way to tell "opted out" from "broken" apart. Leave a marker factory-doctor's
# event-log check can see (and BLOCK on) even from a different shell/session than the
# one that noticed jq was gone; clear it once jq is back so the check stays honest.
if ! command -v jq >/dev/null 2>&1; then
  : > "$DIR/jq-missing" 2>/dev/null
  exit 0
fi
[ -f "$DIR/jq-missing" ] && rm -f "$DIR/jq-missing" 2>/dev/null

input=$(cat 2>/dev/null) || exit 0
[ -n "$input" ] || exit 0

# Harness from the plugin cache path this script was loaded out of.
case "$0" in
  */.factory/*) H=droid ;;
  *)            H=cc ;;
esac

LOG="$DIR/events.ndjson"

# Rotate on SessionStart AND Stop — a stat per turn is cheap, and SessionStart alone
# only checks once per session: one marathon session can blow past 64MB long before
# it ever ends.
case "$input" in
  *'"SessionStart"'*|*'"Stop"'*)
    if [ -f "$LOG" ]; then
      sz=$(wc -c <"$LOG" 2>/dev/null || echo 0)
      [ "$sz" -gt 67108864 ] && mv -f "$LOG" "$DIR/events.$(date -u +%Y%m%d%H%M%S).ndjson"
    fi
    ;;
esac

printf '%s' "$input" | jq -c \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg h "$H" '
  def s: if type == "string" then . else null end;
  ((.tool_input.command // "") | s // "") as $cmd
  | ((.prompt // "") | s // "") as $prompt
  | (if ($cmd | test("chore\\(goals\\): (claim|complete|block|retire|amend) "))
     then ($cmd | capture("chore\\(goals\\): (?<v>claim|complete|block|retire|amend) (?<g>[A-Za-z0-9._-]+)"))
     else null end) as $goal
  | {
      ts:    $ts,
      h:     $h,
      ev:    (.hook_event_name // "unknown"),
      sid:   (.session_id | s),
      cwd:   (.cwd | s),
      aid:   (.agent_id | s),
      at:    (.agent_type | s),
      tool:  (.tool_name | s),
      src:   (.source | s),
      why:   (.reason | s),
      cmd:   (if ($prompt | test("^/[a-z]")) then ($prompt | capture("^/(?<c>[a-z][a-z0-9-]*)") | .c) else null end),
      task:  (.task_name | s),
      err:   (if (.task_error // null) != null then 1 else null end),
      ms:    (.session_duration_ms // .elapsed_time // null),
      ntool: (.tool_execution_count // null),
      nmsg:  (.message_count // null),
      gv:    ($goal.v // null),
      gid:   ($goal.g // null)
    }
  | with_entries(select(.value != null and .value != ""))
' >>"$LOG" 2>/dev/null

exit 0
