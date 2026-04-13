---
description: Scan for swallowed errors, empty catches, ignored promises, missing error handling
argument-hint: '[directory or file scope]'
allowed-tools: mcp__mcp-droid__do_silent_scan
---

Run a silent failure scan. Finds swallowed errors, empty catch blocks, ignored promise rejections, and missing error handling on I/O operations.

**Scope:** `$ARGUMENTS`

If `$ARGUMENTS` specifies files or directories, include them in the prompt.
If empty, scan the current project.

Call `mcp__mcp-droid__do_silent_scan` with the assembled prompt.

**Return the result verbatim.**
