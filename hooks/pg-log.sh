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
command -v jq >/dev/null 2>&1 || exit 0

input=$(cat 2>/dev/null) || exit 0
[ -n "$input" ] || exit 0

# Harness from the plugin cache path this script was loaded out of.
case "$0" in
  */.factory/*) H=droid ;;
  *)            H=cc ;;
esac

LOG="$DIR/events.ndjson"

# Rotate on session start only — one stat per session, not per tool call.
case "$input" in
  *'"SessionStart"'*)
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
