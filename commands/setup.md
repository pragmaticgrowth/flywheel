---
description: Verify droid + opencode installations, check config, sync opencode agents
argument-hint: '[--sync-agents] [--check-only] [--enable-review-gate] [--disable-review-gate]'
allowed-tools: Bash(which:*), Bash(droid:*), Bash(opencode:*), Bash(node:*), Bash(cat:*), Bash(ls:*), Bash(cp:*), Bash(mkdir:*), mcp__mcp-do__do_list_models, AskUserQuestion
---

Verify and configure the "do" plugin environment.

**Raw arguments:** `$ARGUMENTS`

## Review Gate Toggle

If `--enable-review-gate` is present:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/toggle-review-gate.mjs" enable
```

If `--disable-review-gate` is present:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/toggle-review-gate.mjs" disable
```

Run these BEFORE the checks below so the status reflects the change.

## Checks (always run)

1. **droid CLI**: Run `which droid` — report path or "not found"
2. **opencode CLI**: Run `which opencode` — report path or "not found"
3. **MCP server**: Call `mcp__mcp-do__do_list_models` — if it responds, server is alive; count models
4. **Config file**: Check if `~/.config/mcp-do/config.json` exists, read and report `default_provider`
5. **Opencode agents**: Check if `~/.config/opencode/agents/research.md`, `review.md`, `droid-explore.md` exist
6. **Droid profiles**: Check if `~/.factory/droids/pr-reviewer.md` exists
7. **Review gate**: Run `node "${CLAUDE_PLUGIN_ROOT}/scripts/toggle-review-gate.mjs" status` — report enabled/disabled

## Agent Sync (if --sync-agents)

Copy canonical agent definitions from `${CLAUDE_PLUGIN_ROOT}/opencode-agents/` to `~/.config/opencode/agents/`:
```bash
mkdir -p ~/.config/opencode/agents
cp "${CLAUDE_PLUGIN_ROOT}/opencode-agents/"*.md ~/.config/opencode/agents/
```

Copy droid profiles from `${CLAUDE_PLUGIN_ROOT}/droid-profiles/` to `~/.factory/droids/`:
```bash
mkdir -p ~/.factory/droids
cp "${CLAUDE_PLUGIN_ROOT}/droid-profiles/"*.md ~/.factory/droids/
```

## Report

Present results as a checklist:
```
- [x] droid CLI: /path/to/droid
- [x] opencode CLI: /path/to/opencode (v1.4.x)
- [x] MCP server: responding (N custom models)
- [x] Config: default_provider = droid
- [ ] Opencode agents: NOT synced (run /do:setup --sync-agents)
- [ ] Droid profiles: NOT synced (run /do:setup --sync-agents)
- [x] Review gate: disabled (run /do:setup --enable-review-gate to enable)
```

If `--check-only`, report only — don't create or modify anything.
