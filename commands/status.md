---
description: Show available models, profiles, and system status
argument-hint: '[models | profiles]'
disable-model-invocation: true
allowed-tools: mcp__mcp-droid__do_list_models, mcp__mcp-droid__do_list_profiles
---

Show system status information.

**Raw arguments:** `$ARGUMENTS`

## Routing

- `models`: Call `mcp__mcp-droid__do_list_models` and present as a table
- `profiles`: Call `mcp__mcp-droid__do_list_profiles` and present as a table
- Empty: Call both and present a combined summary
