# pg-plugin

Pragmatic Growth workflow skills for Claude Code, distributed via the
`pragmatic-growth` marketplace.

A skills-only plugin — no MCP servers, no commands, no hooks. Three skills
that together form a plain-language → autonomous-execution pipeline backed
by a file-based goal queue:

| Skill | What it does |
|---|---|
| **define-goal** | Shapes plain-language wants ("I want…", `/define-goal`) — or whole documents of them — into measurable goal contracts. Hands back a copy-pasteable `/goal` line to run now, or queues a goal file in the repo's `docs/goals/` directory. Never implements. |
| **dispatch** | Factory orchestrator. Shepherds factory PRs through review, claims queued goals from `docs/goals/index.yaml`, and spawns one isolated implementer agent per goal. Designed to run as `/loop 15m /dispatch`. |
| **loop-architect** | Designs the loop contract (prompt + verification + stop conditions) for autonomous, scheduled, or long unattended runs instead of just firing off the task. |

The intended flow: capture wants with **define-goal** (queued into
`docs/goals/`) → work the queue with **dispatch** → keep it running
unattended with a loop designed by **loop-architect**.

## The docs/goals queue

Goals live in the target repo, not on GitHub — no issue-body size limits,
no label bootstrap, versioned with the code. PRs remain the review and
merge surface.

```
docs/goals/
├── index.yaml        # config + queue state — status lives ONLY here
├── 001-<slug>.md     # goal contracts — content only, never status
└── done/             # archived completed goal files
```

Statuses: `not_started` → `in_progress` → `completed`, plus `blocked`
(with a reason). The index's `config:` block sets the integration
branch (`base:` — main, staging, or any other; goals branch from it and
merge back to it), the merge policy (`pr` = human merges, `auto` = the
factory rebases, re-verifies, and merges back itself), the parallelism
cap (`wip:`), the model for spawned code agents (`model:` — inherit,
sonnet, or haiku to stretch weekly limits), and repo-wide `skills:`
every implementer must invoke; goal files add goal-specific `skills:`
and a `type:` (bug | feature | chore) that shapes the contract in
frontmatter.

`define-goal` creates goal files and index entries; status writes go
through dispatch's claim protocol (pull → flip → commit → push, with
push acceptance on the base branch as the arbiter), so parallel
sessions can safely work the same queue. Implementer agents work in
isolated worktrees branched from `origin/<base>` and never touch
`docs/goals/` at all.

## Install

```bash
# Add the marketplace, then install the plugin
/plugin marketplace add pragmaticgrowth/pg-plugin
/plugin install pg-plugin@pragmatic-growth
```

Once installed, the skills surface namespaced as `pg-plugin:define-goal`,
`pg-plugin:dispatch`, and `pg-plugin:loop-architect`. They activate
automatically when the conversation matches their description, or invoke
them directly: `/define-goal`, `/dispatch`.

## Layout

```
pg-plugin/
├── .claude-plugin/
│   ├── plugin.json        # plugin manifest
│   └── marketplace.json   # pragmatic-growth marketplace
└── skills/
    ├── define-goal/SKILL.md
    ├── dispatch/
    │   ├── SKILL.md
    │   ├── references/herdr-mode.md   # config.execution: herdr contract
    │   └── scripts/                   # vendored herdr ops kit (pm.py, MIT)
    └── loop-architect/SKILL.md
```

## License

MIT
