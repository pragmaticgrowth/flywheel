---
description: TypeScript type design review — flags any leaks, unsafe casts, missing nullability
argument-hint: '[directory or file scope]'
allowed-tools: mcp__mcp-do__do_review
---

Run a type-focused code review. Finds `any` leaks, unsafe casts, missing nullability, incorrect generics, and types that don't reflect runtime reality.

**Scope:** `$ARGUMENTS`

If `$ARGUMENTS` specifies files or directories, limit the review to them. If empty, review the current project.

Call `mcp__mcp-do__do_review` with a prompt that leads with this focus:

> Focus: TypeScript type design only. Flag `any` leaks (including implicit), `as` casts that weaken safety, missing nullability (`T | null` / `T | undefined` that should exist), wrong/missing generics, types that claim guarantees the runtime does not provide, and discriminated unions where a plain union would be unsafe. Only report types that could cause runtime errors or lose type safety. Ignore style.
>
> Scope: `$ARGUMENTS` (or the current project if unspecified).

**Return the result verbatim.**
