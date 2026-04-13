---
description: Power-user passthrough — every droid/opencode flag exposed
argument-hint: '<prompt> [--model <model>] [--provider droid|opencode] [--auto low|medium|high]'
allowed-tools: mcp__mcp-do__do_exec
---

Generic execution passthrough for power users who need full flag control.

**Raw arguments:** `$ARGUMENTS`

Parse recognized flags from `$ARGUMENTS`:
- `--model <model>` — model override
- `--provider droid|opencode` — backend selection
- `--auto low|medium|high` — autonomy level (droid only)

Everything else becomes the prompt.

Call `mcp__mcp-do__do_exec` with the parsed parameters.

**Return the result verbatim.** This is the escape hatch when specialized commands don't fit.
