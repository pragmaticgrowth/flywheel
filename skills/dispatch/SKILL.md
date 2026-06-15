---
name: dispatch
description: Factory dispatcher — use when the user says "/dispatch", "run the factory", wants the docs/goals queue worked, or wants to work one specific queued goal in this session ("work goal 005"). Shepherds factory PRs through review, claims queued goals, and spawns one isolated implementer agent per goal. Designed to run as `/loop 15m /dispatch`; iterations are idempotent, and parallel sessions are safe. Works in any repo with a docs/goals/ queue. Orchestrates only — never implements in its own context.
---

# Dispatch — the factory orchestrator

You are depth 0: a thin orchestrator. Your context stays small; implementers (depth 1) and
their nested helpers (depth 2+, system cap depth=5) hold the mess. Compose existing skills —
never re-derive what a skill already encodes. The queue is `docs/goals/index.yaml`
(see `define-goal` for the format); PRs live on GitHub (`gh` authenticated) when a remote
host exists.

Read the queue's `config:` block first; defaults when absent:
`base` = the repo's default branch (the integration branch goals branch FROM and merge
BACK to — main, staging, or any other), `merge: pr` (human merges; `auto` = the
orchestrator merges back after gates), `wip: 2`, `model: inherit`, `skills: []`.
`config.model` (when not `inherit`) is passed as the `model` parameter on EVERY
code-writing agent you spawn — implementers, CI-fix, review-response, and sync agents
alike; it is the repo owner's depth-vs-weekly-limit trade, not yours to override.
`execution` (default `native`) and `autonomy` (default `balanced`, herdr-mode only)
are read here too — see the execution-substrate note in Phase 0.

## Hard rules (every iteration, before any action)

- Merging follows `config.merge`. Under `pr` the human merges — leave even fully verified
  PRs open and surface them under needs-you. Under `auto`, merging back is the
  orchestrator's own job: you are expected to run `gh pr merge` yourself per Integration,
  sequentially, on a synced and re-verified branch. Implementers never self-merge in
  either mode. Never push protected branches.
- Read the repo's CLAUDE.md / AGENTS.md hard rules once per session and treat them as law
  (deploy rules, forbidden merges, migration rules). Repeat-check before any git/deploy action.
- **Every queue write goes through the claim protocol below**, from the `<base>` checkout.
  Implementers never touch `docs/goals/` — reject PRs that do.
- WIP cap: at most `config.wip` goals `in_progress` at once. Fill free slots one
  claim-protocol round at a time.
- No-progress rule: same PR fails the same way twice with no progress → stop retrying,
  set the goal `blocked` with a `reason`, move on.

## Claim protocol — every status write, multi-session safe

Parallel sessions may work the same queue; `origin/<base>` push acceptance is the arbiter.

1. On the `<base>` checkout: `git fetch origin && git pull --ff-only origin <base>`.
2. Edit exactly one entry, updating fields in place (keep `branch:`/`pr:` for history;
   dates YYYY-MM-DD). Claiming writes
   `{status: in_progress, claimed: <date>, branch: goal/<id>}`. One commit per transition:
   `chore(goals): claim|complete|block|archive <id>`.
3. Push. Rejected → `git pull --rebase` and look again: if another session took your goal,
   discard your claim commit (`git rebase --skip` it, or hard-reset to the remote) so your
   tree matches `origin/<base>`, then re-pick from ready; if your entry survived, push
   again. Max 3 attempts per transition (a re-pick starts a new one), then stop and report.

If the repo forbids pushing `<base>` directly, parallel sessions are NOT safe — run a
single dispatcher, keep queue commits local, and say so in the report.

## Re-entrancy — how iterations coexist with running work

`/loop` fires between turns, so a new iteration never interrupts a dispatch turn in progress;
missed fires don't stack. Implementers run as background agents, so your turn ends quickly
while they keep working. Each iteration must be idempotent:

1. **The index is the claim ledger.** A claim is a pushed status flip made BEFORE spawning —
   never claim from inside a worktree, and never spawn a second implementer for an
   `in_progress` goal that has a live background agent or an open PR.
2. **Stale claim**: `in_progress` + no open PR + no live agent → the implementer died.
   Live = a background agent spawned this session that hasn't finished; from a fresh
   session you can't see prior agents — treat no new commits on `goal/<id>` since
   `claimed` as dead. If the implementer's final report named a blocker, set `blocked`
   with that reason. Otherwise respawn once with a note of what already exists on its
   branch; if it dies again, set `blocked`. Under `execution: herdr`, "live" instead
   means a `lanes`-visible pane on `goal/<id>` (cross-session visible via the herdr
   server), and respawn-once is tracked by the mission's `respawned` flag — see
   `references/herdr-mode.md`.
3. **Shepherd before claiming** (Phase 1 before Phase 2) so finished work always beats new work.

## Phase 0 — sync and read the queue

Switch the main checkout to `<base>` and `git pull --ff-only` (dirty or diverged checkout →
stop and report rather than stash silently). If `docs/goals/index.yaml` is missing, report
"no goals queue — create goals with /define-goal" and end the iteration. Cheap doctor pass,
flagged in the report rather than silently fixed: every entry has its goal file and vice
versa; no circular `depends_on`; no `depends_on` pointing at a missing entry; warn when a
goal and its dependency declare different `base` branches.

**Execution substrate (`config.execution`, default `native`).** `native` = this
document's in-process background-agent path (Phases 1–3, Integration). `herdr` = spawn
each implementer as a fresh `claude` in an isolated herdr worktree pane; when set,
**follow `references/herdr-mode.md`** for the spawn substrate (Phases 1/3, monitoring,
block handling, integration mechanics) — the claim protocol, queue rules, `config`
semantics, Integration, the permission-stall protocol, and Phase 4 reporting in this
file are unchanged and still authoritative. If `execution: herdr` but herdr is
unreachable, degrade to `native` and note it in the report.

## Phase 1 — shepherd in_progress goals

For each `in_progress` entry, find its PR (the `pr:` field, else an open PR from
`branch: goal/<id>`):

1. **PR merged** → set `{status: completed, completed: <date>}` via the claim protocol;
   delete the merged `goal/<id>` branch and prune its worktree.
2. **CI red** → spawn one agent in that PR's branch worktree to diagnose and push a minimal
   fix. It must use the `systematic-debugging` skill, then `verification-before-completion`
   before pushing.
3. **Unaddressed review comments** (bot or human) → spawn one agent in that worktree to
   address every comment using the `receiving-code-review` skill — verify feedback
   technically, don't blindly apply.
4. **Green + comments addressed** → under `merge: pr`, comment a one-paragraph
   plain-language status on the PR and surface it under needs-you; do not merge. Under
   `merge: auto`, run Integration below.
5. **PR newly opened since last iteration** → record `pr: <number>` via the claim protocol.

Apply the stale-claim rule from above to entries with no PR and no live agent.

## Integration (merge: auto) — orchestrator only, one goal at a time

**Merge-rights preflight** (once per session, before the first integration spends
anything on sync or gates): the merge step needs the harness to permit `gh pr merge` —
check for an allow rule matching it (e.g. `Bash(gh pr merge:*)`) in `permissions.allow`
of the repo's `.claude/settings.json` / `.claude/settings.local.json` or user-scope
settings. No rule found and the session is unattended (this iteration was fired by a
schedule, not typed by a human — no one can approve a prompt) → go straight to the
permission-stall protocol below instead of burning gates on a merge that will be denied.
Interactive sessions proceed; the permission prompt arbitrates.

Never merge two goals in one breath — re-sync between merges. For the one goal being
integrated:

1. **Sync**: the branch must contain current `origin/<base>`. If behind, spawn one agent
   in the branch worktree (background is fine — integration then resumes at step 2 on a
   later iteration; never merge an unsynced head just to save a fire) to rebase onto
   `origin/<base>` (or merge base in, matching the repo's convention), resolve conflicts,
   re-run the goal's acceptance commands, and push. Its final message must say either
   "synced and verified" or "substantive conflict: <what collided>" — that signal is what
   you act on. Substantive conflicts — both sides changed the same logic — are never
   guessed through: set `blocked`, surface under needs-you.
2. **Gate after sync**: CI green on the synced head; no CI → the goal's acceptance
   commands re-run in the worktree with output shown. A gate that passed before the sync
   doesn't count. Never sit waiting for CI inside an iteration — end the turn; the next
   fire re-checks.
3. **Merge**: `gh pr merge --squash --delete-branch` when a PR exists; with no remote
   host, `git merge --no-ff goal/<id>` on the `<base>` checkout and push. Push rejected →
   base moved again → back to step 1 (max 3 attempts this iteration, then leave it for
   the next). A permission denial of the merge command itself is NOT a push race —
   permission-stall protocol below.
4. Flip `completed` via the claim protocol; prune the worktree.

### Permission stall — the harness denies the orchestrator's merge

A denied `gh pr merge` is an environment blocker, not a work failure: don't route around
it with raw `git merge`, don't retry it blindly each fire, and don't flip the goal
`blocked` — the work is finished and verified, and `blocked` would free its wip slot,
letting the factory pile up more PRs against the same wall. Instead:

1. Keep the goal `in_progress` (with `pr:` recorded) — it holds its slot on purpose.
   State the gate-verified head and base SHAs in your report; that record is what a
   later fire (or fresh session) compares against. No record → treat as moved.
2. needs-you carries the exact fix, verbatim: merge the PR manually (`gh pr merge <n>
   --squash --delete-branch`), or add `"Bash(gh pr merge:*)"` to `permissions.allow` in
   `.claude/settings.json` — one-time, unblocks every future auto-merge.
3. Send the stalled-factory notification (Phase 4), once.
4. Later fires probe cheaply instead of re-running Integration: PR merged by a human →
   Phase 1 case 1; allow rule now present → resume Integration, re-running gates only
   if the PR head or base moved since you verified them (the one exception to "a gate
   that passed before the sync doesn't count" — valid only while both are provably
   unmoved). Neither → nothing further this fire beyond the Phase 4 report line; no
   repeat notification.

## Phase 2 — claim the next goal(s)

Ready = `status: not_started` AND every `depends_on` entry is `completed` — a `blocked`
dependency makes dependents not-ready; report the stuck chain. While `in_progress` count
< `config.wip`: pick `priority: high` first, then top-most in the file; claim via the
protocol BEFORE spawning, one goal per round. A per-goal `base:` field in the index entry
overrides `config.base` for that goal (epic integration branches).

## Phase 3 — spawn the implementer (depth 1, background, worktree isolation)

One Agent per claimed goal, `isolation: worktree`, `run_in_background: true` — always the
Agent tool, never a Workflow run: a workflow dies with your session leaving nothing to
respawn, while a background agent's branch commits plus the stale-claim rule make crashed
work recoverable. Brief (fill in `<id>`, `<base>`,
and the resolved skill lists):

```
Implement the goal in docs/goals/<id>.md exactly per its "Goal contract" section — read
that file first. You own this work end to end — nested subagents are for context isolation
(explore / write tests / verify in fresh windows), never for passing the whole task down;
spawn helpers at your own model.

Workspace: you are in an isolated worktree. Before anything else: `git fetch origin`,
then make sure you are on branch goal/<id> created from origin/<base>
(`git switch -c goal/<id> origin/<base>` if not already). Run project setup (install
deps) and the repo's test baseline; a dirty baseline is reported, never built on.

Skills are mandatory — invoke each via the Skill tool:
1. BEFORE touching the work they cover: <config.skills + the goal frontmatter's skills:>.
2. `writing-plans` first if the change spans >2 files.
3. `test-driven-development` for every code change (failing test first). Let other
   domain skills trigger as relevant — check the available-skills list.
4. `verification-before-completion` before claiming done: run every command in the
   goal's acceptance criteria and show output. For UI work, verify in the browser
   (project browser skill if present, else agent-browser) and capture a screenshot.

Finish: push goal/<id> and open a PR targeting <base> — `gh pr create --base <base>` —
with body containing "Goal: <id>", a plain-language summary a non-engineer can read, and
the verification evidence. Do NOT merge anything — the orchestrator integrates per the
queue config.

Constraints: the goal file's "Constraints" section verbatim, plus: never merge, never
push protected branches or <base> itself, stay inside your worktree, and NEVER edit
docs/goals/ — the orchestrator owns queue state. If blocked: stop and end your turn with
a report of attempted paths, evidence, the blocker, and what would unlock you — the
dispatcher will mark the goal blocked.
```

## Solo mode — work one named goal in this session

When the user points at a specific goal ("work goal 005"), act as a one-goal orchestrator
instead of spawning: claim it via the protocol; get an isolated workspace with the
`using-git-worktrees` skill (native worktree tool preferred) on `goal/<id>` from
`origin/<base>`; implement under the same skill mandates as the brief above, honoring
`config.model` for any helpers you spawn (your own in-session work necessarily runs on
the session model — mention it if config.model differs); merge back per `config.merge`
(PR, or the Integration steps); flip status via the protocol from the `<base>` checkout. Parallel solo sessions are safe — the claim protocol arbitrates.

## Phase 4 — report (always, exactly one line)

`[dispatch] queue: <ready>/<total> · shepherded: <PRs+outcome or none> · claimed: <id(s) or none> · running: <count>/<wip> · needs-you: <mergeable PRs / blocked goals / nothing>`

Count `ready`/`total` after this iteration's mutations (total = all index entries).
needs-you lists everything currently waiting on the human — mergeable PRs and ALL blocked
goals (noting dependents stuck behind them), every iteration, not only new ones.

**Stalled factory → one real notification.** A report line in an unattended /loop has no
reader. The fire that first finds the factory fully stalled — needs-you non-empty, zero
live implementers, and nothing this iteration could do about it (a fresh permission
denial counts immediately, on the fire it happens, even while implementers are still
running — it gates everything they will produce) — sends the needs-you line via the
PushNotification tool (ToolSearch loads it if deferred). One notification per distinct
blocker set; identical no-op fires after it send no further notifications, though the
report line still goes out every fire — new blocker content notifies again.

## Hygiene

When `completed` entries crowd the index (~20+), move their files to `docs/goals/done/`
and their entries to `docs/goals/archive.yaml` in one `chore(goals): archive` commit.
Run `git worktree prune` and delete merged `goal/*` branches while you're there. Agents
read the whole index every iteration — keep it small.
