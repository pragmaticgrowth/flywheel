# AGENTS.md

## Commands

No build step, no package manager. Python 3 + pytest is the whole toolchain.

```bash
python3 -m pytest -q                                  # full suite (repo root; discovers script tests too)
python3 -m pytest -q skills/dispatch/scripts/test_pg_validate.py          # one file
python3 -m pytest -q skills/goals-status/scripts/test_goals_status.py -k index_unreadable   # one test
wrangler deploy                                       # redeploy the public site (needs CLOUDFLARE_API_TOKEN)
```

`docs/goals/index.yaml` declares `verify: python3 -m pytest -q` — that is the gate
command dispatch runs in this repo.

## Architecture

This repo *is* a single-plugin marketplace (`pragmatic-growth`) for **Claude Code
and Factory Droid** (dual-target since v7.0.0; Droid installs the Claude-layout
plugin via its compatibility translation), not an application. Everything ships
as Markdown skills read by an agent at runtime; the only executable code is a
handful of stdlib-Python helper scripts the skills shell out to.

```
.claude-plugin/marketplace.json   # lists one plugin; root plugin.json = flywheel version
skills/<name>/SKILL.md            # 6 flywheel skills (root plugin)
skills/<name>/scripts/*.py        # deterministic helpers + their pytest files
agents/*.md                       # 3 read-only review subagents (gate-reviewer, fresh-check, contract-red-team)
public/index.html                 # the public site, self-contained; deployed via wrangler.jsonc
```

As of v8.0.0 the marketplace ships **flywheel only** — the html-artifacts,
autoresearch, and human-writing sibling plugins were removed (recoverable via
`git show v7.0.0:plugins/<name>`).

**The pipeline.** The six flywheel skills compose into one flow around a file-based
queue that lives in *target* repos (`docs/goals/index.yaml` + `docs/goals/NNN-slug.md`):

`ideate` (fuzzy idea → approved design) → `define-goal` (design → measurable, red-teamed
goal contract; stamps a per-goal `model:` execution tier — `heavy|medium|light|inherit`,
legacy opus/sonnet/haiku read as aliases) → `dispatch` (works ready goals one at a
time) → `goals-status` (read-only queue view). `loop-architect` designs the unattended
cadence; `factory-doctor` preflights the environment.

**Dispatch's execution model** (the part that requires reading several files to grasp):
one goal at a time, committed **directly on the currently checked-out branch** — no PRs,
no worktrees, no parallel implementers. Each goal is bracketed by two anchors: `anchor`
(pre-claim clean HEAD) and `gate_base` (HEAD after the claim commit). One foreground
implementer commits; then the orchestrator runs the LOCAL gate over `gate_base..HEAD` —
an independent fresh adversarial reviewer, then `skills/dispatch/scripts/pg_validate.py`,
then the repo's `config.verify` commands. PASS → squash to one `feat(goal NNN)` commit +
`completed`. FAIL → `git reset --hard gate_base` + `blocked`. CI is a non-blocking
post-push observation, never a gate.

**Queue invariants.** Status lives ONLY in `index.yaml`, never in goal frontmatter
(dual-write drifts). Goal files are immutable contracts, `define-goal --amend <id>` on a
`blocked` goal the sole exception (immutable to implementers and while claimable). Statuses:
`not_started | in_progress | completed | blocked`. Every status write is flip-one-entry
→ commit (`chore(goals): claim|complete|block <id>`, plus define-goal's
`chore(goals): amend <id>` requeue).

The full rationale, the config-block schema, the model-routing rubric, and the history
of superseded models (v3 worktree/PR model, retired `wish` and `telegram-message` skills)
live in `CLAUDE.md` — read it before changing skill mechanics.

## Conventions

- **Skills-first.** Don't add MCP servers, commands, hooks, or new agents without an
  explicit ask. The three `agents/` definitions are the one standing exception; they
  stay read-only-by-tools on both harnesses (no Edit/Write/Create/ApplyPatch/Agent/Task;
  the allowlist names both shell tools `Bash` + `Execute`, and only tool IDs one of the two
  harnesses actually defines — an unknown ID is a validation error on Droid), pin no
  `model:`, and every
  skill that spawns one keeps a generic-type inline-brief fallback (`general-purpose` on
  Claude Code, `worker` on Droid).
- **Portability.** Skills run in arbitrary repos — never embed user-specific absolute
  paths (`/Users/...`). Resolve helpers via `$CLAUDE_PLUGIN_ROOT` (Droid aliases it),
  then the `~/.claude/plugins` glob, then the `~/.factory/plugins/cache` glob.
- **Docs move with the skills.** Changing what a skill does, how it's invoked, plugin
  boundaries, install, or the queue/config model means updating `README.md` AND
  `public/index.html` in the SAME change. Stale docs = stale ship.
- **Every version bump is a release.** Bump the root `plugin.json`, add a
  `## [X.Y.Z] — <date>` block to `CHANGELOG.md` (canonical history — never delete),
  bump the site `.ver-pill`/`<title>` and the README version badge, then annotated tag
  `vX.Y.Z` + `gh release create` with notes taken from that changelog section.
  Site/changelog-only edits do NOT need a plugin version bump.
- **Push every time.** Commit AND push (`origin main`) on every completed unit of work —
  pre-authorized, no need to ask. End turns with a clean `git status` and no unpushed
  commits or tags; the installed plugin refreshes from GitHub, so unpushed = unshipped.
  Only `CLAUDE.local.md` and `.claude/settings.json` stay local.
- **The remote is public and permanent.** No secrets (a `pre-push` hook enforces this),
  and stay mindful of real client/project names in files, messages, and history.
  `docs/` is tracked and pushed.
- **Skill edits are tested.** Changed skill mechanics get a subagent dry-run (scenario +
  "cite the section that decides each answer"). For compliance-critical rules, add a RED
  baseline: run the same scenario against `git show HEAD:<file>` and confirm the old text
  decided differently. Run the `plugin-dev:plugin-validator` agent after manifest or
  structure changes.
