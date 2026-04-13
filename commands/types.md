---
description: TypeScript type design review — flags any leaks, unsafe casts, missing nullability
argument-hint: '[directory or file scope]'
allowed-tools: mcp__mcp-do__do_type_check
---

Run a TypeScript type design review. Finds `any` leaks, unsafe casts, missing nullability, incorrect generics, and types that don't reflect runtime reality.

**Scope:** `$ARGUMENTS`

If `$ARGUMENTS` specifies files or directories, include them in the prompt.
If empty, review the current project.

Call `mcp__mcp-do__do_type_check` with the assembled prompt.

**Return the result verbatim.**
