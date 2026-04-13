---
description: Navigate codebase — answers "where is X?" and "how does Y work?" with file:line references
argument-hint: '<question about the codebase>'
allowed-tools: mcp__mcp-droid__do_explore
---

Forward a codebase exploration question to the mcp-droid explore tool. The headless model reads files and traces call chains.

**Question:** `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the user what they want to find.

Call `mcp__mcp-droid__do_explore` with prompt set to `$ARGUMENTS`.

**Return the result verbatim.** Do not navigate the codebase yourself — let the headless model do it.
