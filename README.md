# flywheel

**Turn plain-language wants into autonomous execution.**
A skills-only plugin for [Claude Code](https://claude.com/claude-code) and
[Droid](https://factory.ai) (Factory CLI), from Pragmatic Growth.

[![Website](https://img.shields.io/badge/site-plugin.pragmaticgrowth.com-6366f1)](https://plugin.pragmaticgrowth.com)
[![Version](https://img.shields.io/badge/version-4.0.0-8b5cf6)](CHANGELOG.md)
[![CLIs](https://img.shields.io/badge/runs%20in-Claude%20Code%20%2B%20Droid-0ea66e)](#works-in-both-clis)
[![License](https://img.shields.io/badge/license-MIT-64748b)](LICENSE)

> 🌐 **Full docs:** **<https://plugin.pragmaticgrowth.com>**

---

## What is this?

flywheel gives you a small, focused toolkit for **describing what you want in
plain English and having agents actually build it** — with the guardrails that
keep an unattended agent loop from going off the rails.

You say *“I want the pricing page to load in under 1.2 seconds.”* The plugin
investigates your codebase, turns that into a **measurable contract** (what
“done” means, how to verify it), drops it into a **queue that lives in your
repo**, and then — when you’re ready — works that queue **sequentially**: a
foreground implementer commits each goal directly on your current branch, the
orchestrator runs a local build + test gate, and only work that passes is kept
(failures roll back).

It is **skills-only**: no MCP servers, no slash commands of its own, no hooks,
no background daemons, no build step. Just four
[skills](https://docs.claude.com/en/docs/claude-code/skills) that Claude Code
and Droid load automatically and invoke when the conversation calls for them.

### Why a queue in the repo instead of GitHub issues?

Because issues have body-size limits, need per-repo label bootstrapping, and
drift away from the code. flywheel keeps goals as plain Markdown files
**versioned alongside your code** in `docs/goals/`. The queue is just the to-do
list, and it travels with the repo; verified commits land directly on your
branch through the local gate. (You can still open a PR yourself whenever you
want a review surface — flywheel just doesn't require one.)

---

## The four skills

| Skill | One line | Invoke with |
|---|---|---|
| **define-goal** | Plain-language want → a measurable goal contract (or a whole document of them). Never writes code. | `/define-goal …` · or just say *“I want…”* |
| **dispatch** | The factory orchestrator: drains the docs/goals queue sequentially in one session — claim, implement, local gate, keep or roll back. | `/dispatch` · *”work goal 005”* |
| **loop-architect** | Designs the *loop contract* (prompt + verification + stop conditions) for autonomous, scheduled, or remote runs. | *“keep working on X”* · setting up a `/loop`, routine, or cron |
| **factory-doctor** | One-pass preflight/doctor for the repo + machine. Auto-fixes everything local; reports the rest with exact fixes. | `/factory-doctor` |

In Claude Code these are namespaced — `flywheel:define-goal`, etc. They also
activate **automatically** when your message matches what they’re for, so most
of the time you don’t type the name at all.

### define-goal — capture wants as contracts

The front door. Give it a sentence, a paragraph, or a whole bug-report
document, and it produces **goal contracts** — never implementation.

- **Recon first, by default.** Before writing a single success criterion, it
  sends parallel read-only agents to investigate the actual system (your repo,
  a separate service, a database — wherever it lives). “The description sounded
  clear” is the failure mode this replaces.
- **Two destinations.** It can hand you a copy-pasteable **run-now** line
  (`/goal …` in Claude Code, `droid exec --auto high "…"` in Droid), or **queue**
  a goal file (`docs/goals/NNN-slug.md` + an `index.yaml` entry) to be worked
  later by dispatch.
- **Grounded in your repo.** It copies your `CLAUDE.md` / `AGENTS.md` rules
  verbatim into the contract, fills in *real* verification commands, and
  auto-populates the goal’s `touches:` / `acceptance:` fields from recon.
- **Batch mode.** Hand it a list (feedback doc, meeting notes, a backlog) and
  it drafts every goal, then gates the file writes behind an approval table.

```text
> I want signups to send a welcome email within 30 seconds
  define-goal ▸ recon (3 read-only agents) ▸ contract
  ✓ queued  docs/goals/021-welcome-email.md   type: feature
```

### dispatch — work the queue

The orchestrator. It drains the `docs/goals/` queue **sequentially** in a
single session on the currently checked-out branch — no PRs, no worktrees, no
parallel runners.

Per goal:

1. **Claim** the next `not_started` goal (flip one entry → commit on the
   current branch).
2. **Implement** — a foreground implementer commits work directly on `<base>`.
3. **Local gate** — the dispatch orchestrator runs the repo’s `config.verify`
   commands (build + tests), and `pg_validate.py` runs the per-goal acceptance +
   structural checks on the `gate_base..HEAD` diff.  
   - **PASS** → the implementer’s commits are squashed into one
     `feat(goal NNN)` commit kept on the branch.  
   - **FAIL** → work is rolled back; the goal is marked `blocked`.
4. **Repeat** until the queue is empty or `config.budget` is exhausted.

CI, if present, is a post-push observation — not a gate.  You can also target a
single goal in an interactive session: *”work goal 005.”*

### loop-architect — make it run itself, safely

Automating work is easy to get wrong: a naive “keep doing X” loop never knows
when it’s finished and can burn for hours. loop-architect designs the **loop
contract** instead — the prompt, the verification step, and the **stop
conditions** — and maps the right primitives for your CLI (`/loop` vs
`CronCreate`, `/goal` vs `droid exec`). Use it whenever you want something to
run unattended, on a schedule, or remotely.

### factory-doctor — get the environment ready

Run this **before your first `/dispatch`**, or any time the factory behaves
like the environment isn’t ready. It checks software, `gh` auth + scopes, the
local gate (`config.verify` present and runnable), a clean working tree, the
working branch, CI, and the queue itself — **auto-fixing everything local**
(scaffolding the queue, in both `.claude/` and `.factory/` settings) and
reporting remote/CI issues with the exact fix. It diagnoses and fixes setup; it
never implements goals.

---

## How it all fits together

```mermaid
flowchart TD
    you(["You — plain language"]) --> dg["define-goal<br/>writes measurable contracts"]
    dg -->|queues| q[("docs/goals/ queue<br/>index.yaml + goal files")]
    q -->|claim next goal| dsp{{"dispatch · orchestrator"}}
    dsp -->|foreground implementer<br/>commits on branch| impl["work commits<br/>on &lt;base&gt;"]
    impl --> gate{"local gate<br/>pg_validate.py<br/>build + test"}
    gate -->|PASS| squash[["squash → feat(goal NNN)<br/>kept on &lt;base&gt;"]]
    gate -->|FAIL| rollback["roll back → blocked"]
    squash -.->|next ready goal| q
    fd["factory-doctor<br/>preflight + fixes setup"] -.->|readies| dsp
    la["loop-architect<br/>designs the loop"] -.->|keeps it running| dsp
    classDef brand fill:#059669,stroke:#047857,color:#ffffff;
    classDef store fill:#d1fae5,stroke:#10b981,color:#064e3b;
    classDef neutral fill:#ffffff,stroke:#cbd5e1,color:#0f172a;
    classDef human fill:#0f172a,stroke:#0f172a,color:#ffffff;
    classDef support fill:#f1f5f9,stroke:#cbd5e1,color:#334155;
    classDef warn fill:#fee2e2,stroke:#e11d48,color:#9f1239;
    class dg,dsp,squash brand
    class q store
    class impl,gate neutral
    class you human
    class fd,la support
    class rollback warn
```

The intended flow: **capture** wants with define-goal → **work** the queue with
dispatch → **keep it running** unattended with a loop designed by
loop-architect. factory-doctor makes sure the ground is solid first.

---

## The docs/goals queue

Goals live in the target repo, versioned with the code:

```
docs/goals/
├── index.yaml        # config + queue state — status lives ONLY here
├── 001-faster-checkout.md     # goal contract — content only, never status
├── 002-fix-auth-redirect.md
└── done/             # archived completed goal files
```

**Status lives only in `index.yaml`** (never in goal-file frontmatter —
dual-writing drifts). Goal files are immutable contracts. Statuses move
`not_started → in_progress → completed`, plus `blocked` (always with a reason,
so a blocked goal is surfaced for you rather than re-dispatched into a livelock).

A goal file is just readable Markdown with a little frontmatter:

```markdown
---
id: "001"
type: feature            # bug | feature | chore — shapes the contract
skills: [test-driven-development]
touches: [src/checkout/, src/cart/total.ts]
acceptance: "pnpm test checkout && pnpm playwright test checkout.spec"
---

# Faster checkout

## Success criteria
- [ ] Checkout route renders in < 1.2s (p95) on a cold cache
- [ ] All existing checkout tests stay green

## Out of scope
- Redesigning the cart UI
```

The `type:` shapes the contract: **bugs** must lead with a failing test that
reproduces the root cause; **features** must fill in *Out of scope*; **chores**
must prove no behavior change (suite green before and after).

### The claim protocol

Every status write is **flip one entry → commit** (`chore(goals):
claim|complete|block|archive <id>`) on the current branch — one entry per
commit. The single session owns the branch, so there is no push-arbitration;
push is an optional backup only. Implementer agents work directly on `<base>`
and **never touch `docs/goals/` at all** — only the orchestrator does.

---

## Configuration

The `config:` block at the top of `index.yaml` is the repo owner’s control
panel. Everything has a sensible default — an unconfigured repo just works.

```yaml
config:
  base: main              # branch dispatch works on and commits to
  model: inherit          # inherit | sonnet | haiku (for spawned code agents)
  # --- optional ---
  skills: []              # skills every implementer must invoke
  verify:                 # ordered local build + test gate (run before keeping a commit)
    - pnpm build
    - pnpm test
  budget:                 # external "burnstop" for long unattended runs
    max_goals_per_session: 40
    max_iterations: 200
```

| Key | Default | What it does |
|---|---|---|
| `base` | repo default branch | The branch dispatch works on — implementers commit here directly. Per-goal `base:` override allowed. |
| `model` | `inherit` | Model for spawned **code** agents (`inherit`/`sonnet`/`haiku`). The depth-vs-quota trade. (Recon always runs on sonnet.) |
| `skills` | — | Repo-wide skills every implementer must use (e.g. your TDD or review skills). |
| `verify` | — | Ordered list of local build + test commands. Run by the dispatch orchestrator after each implementation; PASS keeps the squash commit, FAIL rolls it back. |
| `budget` | none | `max_goals_per_session` / `max_iterations` ceilings the session can’t exceed — the external brake on a long run. |

---

## Install

**Claude Code:**

```bash
/plugin marketplace add pragmaticgrowth/flywheel
/plugin install flywheel@pragmatic-growth
```

**Droid (Factory CLI):**

```bash
droid plugin marketplace add https://github.com/pragmaticgrowth/flywheel
droid plugin install flywheel@pragmatic-growth
```

Pull updates later with `/plugin marketplace update pragmatic-growth` (Claude
Code) or `droid plugin marketplace update pragmatic-growth` (Droid).

### Quick start

```bash
/factory-doctor                              # 1. make sure the repo + machine are ready
/define-goal I want the API p95 latency under 200ms   # 2. capture a want → queued contract
/dispatch                                    # 3. work the queue — drains it in one session
```

That’s the whole arc: preflight, capture, work. Add more goals any time —
define-goal appends to the queue, and `/dispatch` (or `/loop /dispatch`) picks
them up. Set `config.budget` in `index.yaml` before long unattended runs.

---

## The local gate

After each implementation, the dispatch orchestrator runs the repo’s
`config.verify` commands (build + tests), and `pg_validate.py` runs the
per-goal acceptance + structural checks on the local `gate_base..HEAD` diff:

- All `verify` commands must exit 0.
- A secret / forbidden-content scan.

It emits a verdict — **PASS** or **FAIL** — and the orchestrator acts on it:
PASS squashes the implementer’s commits into one `feat(goal NNN)` commit kept
on the branch; FAIL rolls the work back and marks the goal `blocked`. CI,
if configured, runs after the push as a non-blocking observation.

---

## Running it autonomously

`/dispatch` drains the whole queue in one session — just run it. Each goal is
handled in turn and the session reports **progress-first**:
`6/8 done ████████████████░░░░ · ready 0 · blocked 2`.

If you add more goals later and want to keep working them without re-running
manually, `/loop /dispatch` keeps firing dispatch after each batch. Use
`config.budget` as the burnstop — an external ceiling the loop **cannot edit
itself**, so a flaky queue can’t burn indefinitely. When the budget is hit (or
the queue drains), dispatch stops and surfaces the reason. Let **loop-architect**
design the loop contract (verification + stop conditions) rather than firing a
bare prompt.

---

## Works in both CLIs

One plugin, two runtimes. Droid auto-translates the `.claude-plugin/` manifest
format, and the skills **detect the runtime** and use the right paths,
commands, and scheduling primitives (`/goal` vs `droid exec`, `/loop` vs
`CronCreate`, `.claude/` vs `.factory/` settings). Everything above works the
same way in each; only the exact command surface differs, and the skills handle
that for you.

---

## Versioning & changelog

- **[CHANGELOG.md](CHANGELOG.md)** — the canonical, human-readable history of
  every release, each entry linked to its commit.
- **Git tags** — every release is tagged `vX.Y.Z` on its commit, so the version
  history is browsable on GitHub.
- **The site** — <https://plugin.pragmaticgrowth.com> hosts the full docs and
  install (canonical version history lives in CHANGELOG.md and GitHub Releases).

The plugin version lives in `.claude-plugin/plugin.json`. The public site is
regenerated and redeployed on each release (see `CLAUDE.md` →
*Public site & changelog*).

---

## Project layout

```
flywheel/
├── .claude-plugin/
│   ├── plugin.json        # plugin manifest (Droid auto-translates this format)
│   └── marketplace.json   # the pragmatic-growth marketplace
├── skills/
│   ├── define-goal/SKILL.md
│   ├── dispatch/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── pg_validate.py         # local gate: per-goal acceptance + structural checks, PASS/FAIL verdict
│   ├── factory-doctor/
│   │   ├── SKILL.md
│   │   └── scripts/doctor_checks.py   # read-only readiness probe
│   └── loop-architect/SKILL.md
├── public/                # the plugin.pragmaticgrowth.com site (index.html + brand SVGs)
├── wrangler.jsonc         # Cloudflare deploy config for the site
├── CHANGELOG.md           # canonical version history
└── CLAUDE.md / AGENTS.md  # contributor guide (AGENTS.md is a symlink — one source)
```

---

## Contributing & maintenance

This repo is the single source of truth — the plugin installs from the
`pragmatic-growth` marketplace and refreshes from GitHub. If you’re editing
skills, read **[CLAUDE.md](CLAUDE.md)**: it documents the queue design
invariants, the release flow (bump `plugin.json` → update `CHANGELOG.md` + the
site → tag → push → refresh), and the rule that skills stay portable (no
user-specific absolute paths). New or changed skill mechanics get a subagent
dry-run before shipping.

---

## License

[MIT](LICENSE) © Pragmatic Growth
