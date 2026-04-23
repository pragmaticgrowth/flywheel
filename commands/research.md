---
description: Web research via headless AI — structured findings with source citations
argument-hint: '[--fast] [--provider droid|opencode] <research question>'
allowed-tools: mcp__mcp-do__do_research
---

Forward a research question to `do_research`. Results stay in the headless model's context, keeping the main conversation clean.

**Raw arguments:** `$ARGUMENTS`

## Depth

- If `--fast` is present, pass `depth: "fast"` (concise <200-word answer, MiniMax model)
- Otherwise, omit `depth` (defaults to `"deep"` — thorough structured report with sources, GLM-5-Turbo)

## Provider

- If `--provider droid` or `--provider opencode` is specified, pass it as the `provider` parameter
- Otherwise, let the server use its configured default

## Execution

Strip flags from `$ARGUMENTS` and pass the remaining text as the `prompt` parameter.

If `$ARGUMENTS` is empty after stripping flags, ask the user what they want researched.

**Return the result verbatim.** Do not paraphrase or add commentary.
