#!/bin/bash
# Droid Mission Manager — tmux helper for Factory.ai missions
# Usage: bash mission-manager.sh <command> [args]

set -euo pipefail

MISSION_PREFIX="mission-"

usage() {
  cat <<EOF
Droid Mission Manager

Usage: bash mission-manager.sh <command> [args]

Commands:
  launch <name> [repo-path]   Create tmux session and start droid
  list                        List all mission tmux sessions
  status <name>               Show last 30 lines of mission output
  attach <name>               Reattach to a mission session
  peek <name> [lines]         Show last N lines without attaching (default: 30)
  kill <name>                 Kill a mission session
  kill-all                    Kill all mission sessions
  monitor [interval]          Watch all missions (default: 10s refresh)

Examples:
  bash mission-manager.sh launch federal-tax-audit /Users/serkan/nt-dev
  bash mission-manager.sh list
  bash mission-manager.sh peek federal-tax-audit 50
  bash mission-manager.sh status federal-tax-audit
  bash mission-manager.sh attach federal-tax-audit
  bash mission-manager.sh kill federal-tax-audit
EOF
}

cmd_launch() {
  local name="${1:?Usage: launch <name> [repo-path]}"
  local repo="${2:-$(pwd)}"
  local session="${MISSION_PREFIX}${name}"

  if tmux has-session -t "$session" 2>/dev/null; then
    echo "Session '$session' already exists. Use 'attach $name' to reconnect."
    exit 1
  fi

  echo "Creating tmux session: $session"
  echo "Repo: $repo"
  echo ""
  echo "After droid starts:"
  echo "  1. Type /enter-mission to begin"
  echo "  2. Type /model → select Orchestrator → pick VP: Opus 4.6 1M (xHigh) [custom]"
  echo "     (CRITICAL: orchestrator defaults to Factory built-in with token limits)"
  echo "  3. Describe your goal and approve the plan"
  echo "  4. Detach with Ctrl+B, D to let it run"
  echo ""

  tmux new -s "$session" -c "$repo" \; send-keys "droid" Enter
}

cmd_list() {
  echo "Active mission sessions:"
  echo "========================"
  tmux ls 2>/dev/null | grep "^${MISSION_PREFIX}" || echo "(none)"
  echo ""
  echo "All tmux sessions:"
  echo "========================"
  tmux ls 2>/dev/null || echo "(no tmux sessions)"
}

cmd_status() {
  local name="${1:?Usage: status <name>}"
  local session="${MISSION_PREFIX}${name}"

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "No session found: $session"
    exit 1
  fi

  echo "=== Mission: $name ==="
  echo "Session: $session"
  echo ""
  tmux capture-pane -t "$session" -p | tail -30
}

cmd_attach() {
  local name="${1:?Usage: attach <name>}"
  local session="${MISSION_PREFIX}${name}"

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "No session found: $session"
    echo "Available sessions:"
    tmux ls 2>/dev/null | grep "^${MISSION_PREFIX}" || echo "(none)"
    exit 1
  fi

  tmux attach -t "$session"
}

cmd_peek() {
  local name="${1:?Usage: peek <name> [lines]}"
  local lines="${2:-30}"
  local session="${MISSION_PREFIX}${name}"

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "No session found: $session"
    exit 1
  fi

  tmux capture-pane -t "$session" -p | tail -"$lines"
}

cmd_kill() {
  local name="${1:?Usage: kill <name>}"
  local session="${MISSION_PREFIX}${name}"

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "No session found: $session"
    exit 1
  fi

  echo "Killing session: $session"
  tmux kill-session -t "$session"
  echo "Done."
}

cmd_kill_all() {
  local sessions
  sessions=$(tmux ls 2>/dev/null | grep "^${MISSION_PREFIX}" | cut -d: -f1)

  if [ -z "$sessions" ]; then
    echo "No mission sessions to kill."
    exit 0
  fi

  echo "Killing all mission sessions:"
  echo "$sessions" | while read -r s; do
    echo "  Killing: $s"
    tmux kill-session -t "$s"
  done
  echo "Done."
}

cmd_monitor() {
  local interval="${1:-10}"

  echo "Monitoring all mission sessions (refresh every ${interval}s)"
  echo "Press Ctrl+C to stop"
  echo ""

  watch -n "$interval" '
    for session in $(tmux ls 2>/dev/null | grep "^mission-" | cut -d: -f1); do
      echo "=== $session ==="
      tmux capture-pane -t "$session" -p 2>/dev/null | tail -10
      echo ""
    done
  '
}

# Main dispatcher
case "${1:-}" in
  launch)   shift; cmd_launch "$@" ;;
  list)     cmd_list ;;
  status)   shift; cmd_status "$@" ;;
  attach)   shift; cmd_attach "$@" ;;
  peek)     shift; cmd_peek "$@" ;;
  kill)     shift; cmd_kill "$@" ;;
  kill-all) cmd_kill_all ;;
  monitor)  shift; cmd_monitor "$@" ;;
  -h|--help|help|"") usage ;;
  *)        echo "Unknown command: $1"; usage; exit 1 ;;
esac
