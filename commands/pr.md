---
description: PR review — comprehensive single-pass review using GPT-5.4 xHigh with auto git context
argument-hint: '[--base main] [--scope full|staged|unstaged] [--focus security|performance|types] [--provider droid|opencode]'
allowed-tools: mcp__mcp-do__do_pr_review
---

Run a comprehensive PR review through the mcp-do MCP server using the highest reasoning tier.

**Raw arguments:** `$ARGUMENTS`

## Argument Parsing

Parse recognized flags from `$ARGUMENTS`:
- `--base <branch>` — base branch to diff against (default: auto-detect)
- `--scope full|staged|unstaged` — what to review (default: full)
- `--focus <area>` — emphasize an area: security, performance, types, etc.
- `--provider droid|opencode` — backend selection

## Execution

Call `mcp__mcp-do__do_pr_review` with the parsed parameters. If no arguments given, call with no parameters (all defaults).

**Return the result verbatim.** Do not summarize or edit the review findings.
