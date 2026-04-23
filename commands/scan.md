---
description: Scan for swallowed errors, empty catches, ignored promises, missing error handling
argument-hint: '[directory or file scope]'
allowed-tools: mcp__mcp-do__do_review
---

Run a silent-failure-focused code review. Finds swallowed errors, empty catch blocks, ignored promise rejections, and missing error handling on I/O operations.

**Scope:** `$ARGUMENTS`

If `$ARGUMENTS` specifies files or directories, limit the review to them. If empty, scan the current project.

Call `mcp__mcp-do__do_review` with a prompt that leads with this focus:

> Focus: find silent failures only — swallowed exceptions, empty catch blocks, ignored promise rejections (missing `.catch()` or `await`), errors logged but not handled, missing error handling around I/O (fs, network, child_process). Order findings by production risk. Ignore style, naming, and non-error code paths.
>
> Scope: `$ARGUMENTS` (or the current project if unspecified).

**Return the result verbatim.**
