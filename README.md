# pg-plugin

Pragmatic Growth workflow skills for Claude Code, distributed via the
`pragmatic-growth` marketplace.

A skills-only plugin — no MCP servers, no commands, no hooks. Three skills
that together form a plain-language → autonomous-execution pipeline:

| Skill | What it does |
|---|---|
| **wish** | Turns plain-language wants ("I want…", "it bothers me that…", `/wish`) — or whole documents of them — into agent-ready GitHub issues with measurable goal contracts. Never implements. |
| **dispatch** | Factory orchestrator. Shepherds factory PRs through review, claims agent-ready issues, and spawns one isolated implementer agent per issue. Designed to run as `/loop 15m /dispatch`. |
| **loop-architect** | Designs the loop contract (prompt + verification + stop conditions) for autonomous, scheduled, or long unattended runs instead of just firing off the task. |

The intended flow: capture wants with **wish** → work the queue with
**dispatch** → keep it running unattended with a loop designed by
**loop-architect**.

## Install

```bash
# Add the marketplace, then install the plugin
/plugin marketplace add pragmaticgrowth/pg-plugin
/plugin install pg-plugin@pragmatic-growth
```

Skills activate automatically when the conversation matches their
description, or invoke them directly: `/wish`, `/dispatch`.

## Layout

```
pg-plugin/
├── .claude-plugin/
│   ├── plugin.json        # plugin manifest
│   └── marketplace.json   # pragmatic-growth marketplace
└── skills/
    ├── wish/SKILL.md
    ├── dispatch/SKILL.md
    └── loop-architect/SKILL.md
```

## License

MIT
