---
description: Code review against local git state — single model or cross-model (--cross)
argument-hint: '[--cross] [--provider droid|opencode] [focus area...]'
allowed-tools: Bash(git:*), mcp__mcp-do__do_review, mcp__mcp-do__do_cross_review
---

Run a code review through the mcp-do MCP server using intelligent structured prompts.

**Raw arguments:** `$ARGUMENTS`

## Context Gathering

1. Run `git diff --stat` and `git diff --cached --stat` to see what changed
2. If there are no changes, tell the user there's nothing to review and stop
3. Run `git diff` (include both staged and unstaged) to get the full diff

## Scope

- Default: all staged + unstaged changes
- If the user specified files or directories in `$ARGUMENTS` (after flags), limit `git diff` to those paths
- If the user specified `--base <ref>`, use `git diff <ref>...HEAD` instead

## Tool Selection

- If `--cross` flag is present: use `mcp__mcp-do__do_cross_review` (3 models in parallel)
- Otherwise: use `mcp__mcp-do__do_review` (single model, faster)

## Provider

- If `--provider droid` or `--provider opencode` is specified, pass it as the `provider` parameter
- Otherwise, let the MCP server use its configured default

## Execution

Build the review prompt by combining:
1. The diff output
2. Any focus text from arguments (e.g., "focus on error handling")

Pass the assembled prompt to the selected MCP tool. **Return the result verbatim.**

Do NOT fix issues. Do NOT add commentary. Review only.
