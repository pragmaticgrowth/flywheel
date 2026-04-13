---
description: Architecture analysis — evaluates structure, risks, and recommends improvements with trade-offs
argument-hint: '[--provider droid|opencode] <what to analyze>'
allowed-tools: mcp__mcp-do__do_architect, Bash(git:*)
---

Run architecture analysis using the deepest analysis model (GLM-5.1 for droid, equivalent for opencode).

**Raw arguments:** `$ARGUMENTS`

## Context Gathering

Optionally run `git log --oneline -20` to include recent commit context in the prompt.

## Execution

Call `mcp__mcp-do__do_architect` with the analysis request from `$ARGUMENTS`.

If `$ARGUMENTS` is empty, ask the user what they want analyzed.

**Return the result verbatim.**
