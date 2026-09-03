# AGENTS.md

## Commands

No build step, no package manager. Python 3 + pytest is the whole toolchain.

```bash
python3 -m pytest -q                                  # full suite (repo root; discovers script tests too)
python3 -m pytest -q skills/dispatch/scripts/test_pg_validate.py          # one file
python3 -m pytest -q skills/goals-status/scripts/test_goals_status.py -k index_unreadable   # one test
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
skills/<name>/SKILL.md            # 9 flywheel skills (root plugin)
skills/<name>/scripts/*.py        # deterministic helpers + their pytest files
agents/*.md                       # 5 read-only subagents — review: gate-reviewer, contract-red-team · recon: recon-locator, recon-analyzer, recon-patterns
README.md                         # short public overview — GitHub is the only surface (no website)
```

As of v8.0.0 the marketplace ships **flywheel only** — the html-artifacts,
autoresearch, and human-writing sibling plugins were removed (recoverable via
`git show v7.0.0:plugins/<name>`).

**The pipeline.** The nine flywheel skills compose into one flow around a file-based
queue that lives in *target* repos (`docs/goals/index.yaml` + `docs/goals/NNN-slug.md`):

`ideate` (fuzzy idea → approved PLAN at `docs/goals/plans/` — code-shaped design,
vertical-slice phases, owner-resolved open questions; v11) → `define-goal` (plan/want →
measurable, red-teamed goal contract; plan-backed wants get zero question rounds;
stamps a per-goal `model:` execution tier — `heavy|medium|light|inherit`,
legacy opus/sonnet/haiku read as aliases) → `dispatch` (drains ready goals by
default, auto-parallel lanes when `config.parallel` opts in) → `goals-status`
(read-only queue view). `loop-architect` designs the unattended
cadence; `factory-doctor` preflights the environment.

**The standard of completion** (v12.4.0, from Factory's 2026-08-27 study: an agent
that authors its own definition of done stops early, and a standard that can soften
stops measuring). Two rules cut across the pipeline, and they protect each other —
without the ratchet, self-heal could route a failing outcome check into an amend and
weaken the check that was measuring the whole:

- **The whole is measured, not just each piece.** At 3+ phases a plan's LAST phase is
  its OUTCOME CHECK — a verification-only goal that builds nothing, depends on every
  other phase, and runs every bullet of `## What will be true when done`. Those
  bullets each name an exact command (or keep `**needs independent review**`), must
  FAIL at the plan's base commit, must be COMMITTED tests the suite discovers, and
  must DRIVE a real surface. So `status: done` on a plan means its outcome check
  PASSED, not that its pieces got built — with no new dispatch machinery, since
  phases already map 1:1 onto goals.
- **The standard only ratchets up.** An amend classifies every edit against
  `git show HEAD:docs/goals/<id>.md`; weakening (criterion deleted, threshold
  loosened, a runnable command traded for a vouched-for assertion, a drivable-surface
  check traded for a code-reading one, a lost BEFORE, a removed review marker,
  `touches:` narrowed) STOPS FOR THE OWNER, drain waiver or not. Plans are ratcheted
  the same way on iteration, which is what closes the back door of softening the
  plan and contracting the goal honestly from weaker text. Enforced at reality-check
  item 10 and red-team item 15 — the red-team being the one thing the waiver never
  waives. A `needs independent review` marker cannot launder a weakening (v12.4.1).

**Dispatch's execution model** (the part that requires reading several files to grasp):
one goal INTEGRATES at a time, committed **directly on the currently checked-out
branch** — no PRs, no remote branches. Building may parallelize: `--parallel` (or a
flagless drain with `config.parallel` present) builds provably-disjoint goals in
disposable local worktree lanes, still integrating strictly one at a time behind the
same gate — on BOTH harnesses since v12.5.0 (Claude Code spawns the wave as concurrent
plain `Agent` calls, Droid as concurrent awaited `Task` calls in one
message; background-plus-poll lane emulation stays banned everywhere). Since v12.6.0 the
WAIT is doctrine too: on Claude Code a helper's report arrives at a turn BOUNDARY, so a
factory spawn never carries `name:` (a named agent reports by mailbox, not by
notification) and the orchestrator never builds a wait out of sleep loops, blocking shell
waits, or repeated agent listings — those hold the turn open and starve the delivery. A
silent helper is checked against its own on-disk transcript before it is ever called
dead. Each goal is bracketed by two anchors: `anchor`
(pre-claim clean HEAD) and `gate_base` (HEAD after the claim commit). One
implementer commits; then the orchestrator runs the LOCAL gate over `gate_base..HEAD` —
an independent fresh adversarial reviewer, then `skills/dispatch/scripts/pg_validate.py`,
then the repo's `config.verify` commands. PASS → squash to one `feat(goal NNN)` commit +
`completed`. FAIL → `git reset --hard gate_base` + `blocked`. CI is a non-blocking
post-push observation, never a gate.

**Queue invariants.** Status lives ONLY in `index.yaml`, never in goal frontmatter
(dual-write drifts). Goal files are immutable contracts, `define-goal --amend <id>` on a
`blocked` goal the sole exception (immutable to implementers and while claimable) — and
since v12.4.0 that exception is RATCHETED: an amend may make a contract stricter or more
correct, never easier, and a weakening one stops for the owner even under the Self-heal
drain waiver. Statuses:
`not_started | in_progress | completed | blocked | retired` (retired = terminal,
archive-bound, for disproven-premise goals — v12.0.0). Every status write is flip-one-entry
→ commit (`chore(goals): claim|complete|block|archive|retire <id>`, plus define-goal's
`chore(goals): amend <id>` requeue — in-run via dispatch's Self-heal drain waiver, by
hand otherwise). Since v12.2.0 the claim flip also stamps `claimed_at:` and every
terminal flip `settled_at:` (UTC ISO-8601) on the entry — metadata for duration
visibility, written only by dispatch, never read for control flow, optional on
pre-existing entries; timestamps are not status, so status-only-in-index holds.

The full rationale, the config-block schema, the model-routing rubric, and the history
of superseded models (v3 worktree/PR model, retired `wish` and `telegram-message` skills)
live in `CLAUDE.md` — read it before changing skill mechanics.

## Conventions

- **Skills-first.** Don't add MCP servers, commands, hooks, or new agents without an
  explicit ask. The six `agents/` definitions (three review roles, three riptide-adapted
  recon roles) are the one standing exception; they
  stay read-only-by-tools on both harnesses (no Edit/Write/Create/ApplyPatch/Agent/Task;
  the allowlist names both shell tools `Bash` + `Execute`, and only tool IDs one of the two
  harnesses actually defines — an unknown ID is a validation error on Droid), pin no
  `model:`, and every
  skill that spawns one keeps a generic-type inline-brief fallback (`general-purpose` on
  Claude Code, `worker` on Droid).
- **Portability.** Skills run in arbitrary repos — never embed user-specific absolute
  paths (`/Users/...`). Resolve helpers via `$CLAUDE_PLUGIN_ROOT` (Droid aliases it),
  then the `~/.claude/plugins` glob, then the `~/.factory/plugins/cache` glob.
- **Docs stay minimal.** There is no website (deleted 2026-08-12 — owner decision;
  `git show v11.0.0:public/index.html` recovers it). `README.md` is a SHORT public
  overview: update it only when a user-facing fact changes (a skill's purpose,
  invocation, install, or the config model), and never grow it into a manual.
  Mechanics and rationale belong in `CLAUDE.md`. No full-doc-sync ritual.
- **Every version bump is a release — and nothing else.** Bump the root
  `plugin.json`, add a `## [X.Y.Z] — <date>` block to `CHANGELOG.md` (canonical
  history — never delete), then annotated tag `vX.Y.Z` + `gh release create` with
  notes taken from that changelog section. Docs/changelog-only edits do NOT need a
  plugin version bump.
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
