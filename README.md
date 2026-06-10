# pg-plugin

Pragmatic Growth workflow skills for Claude Code, distributed via the
`pragmatic-growth` marketplace.

A skills-only plugin — no MCP servers, no commands, no hooks. Four skills
that together form a plain-language → autonomous-execution pipeline:

| Skill | What it does |
|---|---|
| **wish** | Turns plain-language wants ("I want…", "it bothers me that…", `/wish`) — or whole documents of them — into agent-ready GitHub issues with measurable goal contracts. Never implements. |
| **dispatch** | Factory orchestrator. Shepherds factory PRs through review, claims agent-ready issues, and spawns one isolated implementer agent per issue. Designed to run as `/loop 15m /dispatch`. |
| **loop-architect** | Designs the loop contract (prompt + verification + stop conditions) for autonomous, scheduled, or long unattended runs instead of just firing off the task. |
| **define-goal** | Shapes a fuzzy intention into a measurable objective and hands back a copy-pasteable `/goal` line with verification evidence and a stop clause. Adapted from OpenAI's curated `define-goal` skill for Claude Code's `/goal`. |

The intended flow: capture wants with **wish** → work the queue with
**dispatch** → keep it running unattended with a loop designed by
**loop-architect**.

## Install

```bash
# Add the marketplace, then install the plugin
/plugin marketplace add pragmaticgrowth/pg-plugin
/plugin install pg-plugin@pragmatic-growth
```

Once installed, the skills surface namespaced as `pg-plugin:wish`,
`pg-plugin:dispatch`, `pg-plugin:loop-architect`, and
`pg-plugin:define-goal`. They activate automatically when the conversation
matches their description, or invoke them directly: `/wish`, `/dispatch`,
`/define-goal`.

## Layout

```
pg-plugin/
├── .claude-plugin/
│   ├── plugin.json        # plugin manifest
│   └── marketplace.json   # pragmatic-growth marketplace
└── skills/
    ├── wish/SKILL.md
    ├── dispatch/SKILL.md
    ├── loop-architect/SKILL.md
    └── define-goal/SKILL.md
```

## License

MIT
