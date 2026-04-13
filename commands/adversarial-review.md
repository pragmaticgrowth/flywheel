---
description: Adversarial review that challenges design choices — not just code quality
argument-hint: '[--base <ref>] [--provider droid|opencode] [focus area...]'
allowed-tools: Bash(git:*), mcp__mcp-do__do_adversarial_review
---

Run an adversarial code review that challenges the chosen implementation, design choices, tradeoffs, and assumptions. This is not just a stricter pass over code defects — it questions whether the current approach is the right one.

**Raw arguments:** `$ARGUMENTS`

## Context Gathering

1. Run `git diff --stat` and `git diff --cached --stat` to see what changed
2. If there are no changes, check `git diff --stat main...HEAD` (or the base ref) for branch changes
3. If still no changes, tell the user there's nothing to review and stop
4. Run the appropriate `git diff` to get the full diff

## Scope

- Default: all staged + unstaged changes
- If the user specified files or directories in `$ARGUMENTS` (after flags), limit `git diff` to those paths
- If the user specified `--base <ref>`, use `git diff <ref>...HEAD` instead

## Focus Text

Any text in `$ARGUMENTS` that isn't a flag is treated as adversarial focus — areas to pressure-test. Examples:
- "challenge whether this was the right caching design"
- "look for race conditions and question the chosen approach"
- "focus on rollback safety and data loss scenarios"

## Provider

- If `--provider droid` or `--provider opencode` is specified, pass it as the `provider` parameter
- Otherwise, let the MCP server use its configured default

## Execution

Build the review prompt by combining:
1. The diff output
2. Any focus text from arguments

Pass the assembled prompt to `mcp__mcp-do__do_adversarial_review`. **Return the result verbatim.**

Do NOT fix issues. Do NOT apply patches. Do NOT add commentary. Review only.
