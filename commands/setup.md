---
description: Verify droid + opencode installations, check config, sync opencode agents
argument-hint: '[--sync-agents] [--check-only]'
allowed-tools: Bash(which:*), Bash(droid:*), Bash(opencode:*), Bash(node:*), Bash(cat:*), Bash(ls:*), Bash(cp:*), Bash(mkdir:*), mcp__mcp-do__do_list_models, AskUserQuestion
---

Verify and configure the "do" plugin environment.

**Raw arguments:** `$ARGUMENTS`

## Checks (always run)

1. **droid CLI**: Run `which droid` — report path or "not found"
2. **opencode CLI**: Run `which opencode` — report path or "not found"
3. **MCP server**: Call `mcp__mcp-do__do_list_models` — if it responds, server is alive; count models
4. **Config file**: Check if `~/.config/mcp-droid/config.json` exists, read and report `default_provider`
5. **Opencode agents**: Check if `~/.config/opencode/agents/research.md`, `review.md`, `droid-explore.md` exist

## Agent Sync (if --sync-agents)

Copy canonical agent definitions from `${CLAUDE_PLUGIN_ROOT}/opencode-agents/` to `~/.config/opencode/agents/`:
```bash
mkdir -p ~/.config/opencode/agents
cp "${CLAUDE_PLUGIN_ROOT}/opencode-agents/research.md" ~/.config/opencode/agents/
cp "${CLAUDE_PLUGIN_ROOT}/opencode-agents/review.md" ~/.config/opencode/agents/
cp "${CLAUDE_PLUGIN_ROOT}/opencode-agents/droid-explore.md" ~/.config/opencode/agents/
```

## Report

Present results as a checklist:
```
- [x] droid CLI: /path/to/droid
- [x] opencode CLI: /path/to/opencode (v1.4.x)
- [x] MCP server: responding (N custom models)
- [x] Config: default_provider = droid
- [ ] Opencode agents: NOT synced (run /do:setup --sync-agents)
```

If `--check-only`, report only — don't create or modify anything.
