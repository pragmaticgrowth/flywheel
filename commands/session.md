---
description: Continue or list droid sessions
argument-hint: '<continue <id> "prompt" | list [--all] [--search "query"]>'
allowed-tools: mcp__mcp-do__do_session_continue, mcp__mcp-do__do_session_list
---

Session management for droid sessions.

**Raw arguments:** `$ARGUMENTS`

## Subcommand Routing

- `continue <session_id> <prompt>`: Call `mcp__mcp-do__do_session_continue` with the session_id and prompt
- `list`: Call `mcp__mcp-do__do_session_list` with `scan_disk: true` for complete results
- `list --all`: Call `do_session_list` with `all: true`
- `list --search "<query>"`: Call `do_session_list` with `search: "<query>"`
- No arguments: Call `do_session_list` to show recent sessions

**Return results verbatim.**
