---
description: Deep web research via headless AI — structured findings with source citations
argument-hint: '[--fast] [--provider droid|opencode] <research question>'
allowed-tools: mcp__mcp-droid__do_research, mcp__mcp-droid__do_research_fast
---

Forward a research question to the mcp-droid research tool. Results stay in the headless model's context, keeping main conversation clean.

**Raw arguments:** `$ARGUMENTS`

## Tool Selection

- If `--fast` flag is present: use `mcp__mcp-droid__do_research_fast` (quick lookup, <200 words)
- Otherwise: use `mcp__mcp-droid__do_research` (thorough, parallel web search)

## Provider

- If `--provider droid` or `--provider opencode` is specified, pass it
- Otherwise, let the server use its configured default

## Execution

Strip flags from `$ARGUMENTS` and pass the remaining text as the `prompt` parameter.

If `$ARGUMENTS` is empty after stripping flags, ask the user what they want researched.

**Return the result verbatim.** Do not paraphrase or add commentary.
