# flywheel

**Turn plain-language wants into autonomous execution.**
A skills-first plugin for [Claude Code](https://claude.com/claude-code) and
[Factory Droid](https://factory.ai), from Pragmatic Growth.

[![Version](https://img.shields.io/badge/version-11.2.0-8b5cf6)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-64748b)](LICENSE)

---

## What it does

You say *"I want the pricing page to load in under 1.2 seconds."* flywheel
investigates your codebase, turns that into a **measurable contract** (what
"done" means and how to verify it), drops it into a **queue that lives in your
repo** (`docs/goals/`), and then works that queue: an implementer commits with
TDD on your branch, an independent reviewer plus your build/test commands gate
the diff, and only work that passes is kept — failures roll back cleanly.

The `pragmatic-growth` marketplace ships **one plugin** — `flywheel` — with six
skills and six read-only subagents: three reviewers (`gate-reviewer`,
`fresh-check`, `contract-red-team`) and three recon roles (`recon-locator`,
`recon-analyzer`, `recon-patterns`) that ground every contract and plan in how
the code actually works. No MCP servers, no hooks, no daemons, no build step.

## Install

**Claude Code**

```bash
/plugin marketplace add pragmaticgrowth/flywheel
/plugin install flywheel@pragmatic-growth
```

**Factory Droid**

```bash
droid plugin marketplace add https://github.com/pragmaticgrowth/flywheel
droid plugin install flywheel@flywheel
```

Update later with `/plugin marketplace update pragmatic-growth`, or
`droid plugin marketplace update` + `droid plugin update`.

## Quick start

```bash
/factory-doctor                                       # 1. get the repo + machine ready
/ideate what if signups had a referral loop           #    (optional) explore a fuzzy idea
/define-goal I want the API p95 latency under 200ms   # 2. capture a want as a contract
/dispatch                                             # 3. work the queue
```

## The skills

| Skill | What it does |
|---|---|
| **ideate** | Fuzzy idea → an approved **plan** with vertical-slice phases and open questions only you can answer. Never writes goals or code. |
| **define-goal** | Plain-language want → a measurable, red-teamed goal contract in the queue (or a whole document of them). `--amend <id>` repairs a blocked goal's contract and requeues it. Never writes code. |
| **dispatch** | The orchestrator: claim, implement with TDD, review, gate, keep or roll back. Drains the queue by default; `--count N` limits the run, `--serial` forces one goal at a time, `--parallel [K]` builds disjoint goals concurrently. |
| **goals-status** | Read-only view of what's open — in progress, blocked, not started. |
| **loop-architect** | Designs the loop contract (prompt + verification + stop conditions) for unattended runs. |
| **factory-doctor** | One-pass preflight/doctor. Auto-fixes everything local, reports the rest with exact fixes. |

Skills also activate automatically when your message matches what they're for,
so most of the time you don't type the name.

## How the queue works

Goals are plain Markdown files in your repo — `docs/goals/NNN-slug.md` plus an
`index.yaml` ledger. Status lives **only** in `index.yaml`
(`not_started | in_progress | completed | blocked`).
Goal files are immutable contracts — `define-goal --amend <id>` on a blocked goal is the sole exception.

dispatch works **one goal at a time on the branch you have checked out** — no
pull requests, no remote branches. Each goal is bracketed by two anchors, so
after the implementer commits, the local gate runs over exactly that diff:

1. **Independent review** — a fresh read-only adversarial reviewer over the diff
   plus the contract. The implementer never grades its own work.
2. **Deterministic checks** — your `config.verify` commands (build + tests) and
   a per-goal acceptance/structural validation, including a secrets scan.

**PASS** squashes the work into one `feat(goal NNN)` commit and marks the goal
completed. **FAIL** resets the branch and marks it blocked with a reason. CI, if
you have it, is a non-blocking observation afterwards — never a gate.

## Configuration

The `config:` block at the top of `docs/goals/index.yaml`. Everything has a
default — an unconfigured repo just works.

```yaml
config:
  base: main              # branch dispatch works on and commits to
  model: inherit          # execution tier for code agents: inherit | heavy | medium | light
  skills: []              # skills every implementer must invoke
  verify:                 # ordered local build + test gate
    - pnpm build
    - pnpm test
  budget:                 # optional ceiling for long unattended runs
    max_goals_per_session: 1
  parallel:               # optional — enables dispatch's concurrent build lanes;
    max_lanes: 2          #   its PRESENCE also auto-parallelizes flagless drains
    auto: true            #   (set auto: false to keep lane mode flag-only)
```

`model` sets the repo-wide default tier for code agents; each goal's own
frontmatter overrides it. Review and orchestration agents always stay on your
session model. `budget` always outranks the run — even a full drain stops at
the cap.

## Running it unattended

`/dispatch` drains the queue and reports progress per goal
(`6/8 done ████████████████░░░░ · ready 0 · blocked 2`). `/loop /dispatch`
re-drains on a cadence. On subscription plans a usage limit silently kills an
in-session loop, so the durable pattern is a **window-timed attended drain**:
start `/dispatch` right after each limit reset and let it drain the window.
Every cycle is idempotent, so a run killed mid-goal costs nothing.

## Layout

```
flywheel/
├── .claude-plugin/        # plugin manifest + the pragmatic-growth marketplace
├── skills/                # the six skills (+ their Python helpers)
├── agents/                # six read-only roles: 3 reviewers + 3 recon
├── CHANGELOG.md           # canonical version history
├── CLAUDE.md              # contributor guide — design invariants, release flow
└── AGENTS.md              # short contributor brief
```

## Contributing

This repo is the single source of truth; the plugin refreshes from GitHub. If
you're editing skills, read [CLAUDE.md](CLAUDE.md) first. Run the suite with
`python3 -m pytest -q`.

## License

[MIT](LICENSE) © Pragmatic Growth
