---
name: dispatch
description: Factory dispatcher — use when the user says "/dispatch", "run the factory", or wants the docs/goals queue worked. Shepherds factory PRs through review, claims queued goals, and spawns one isolated implementer agent per goal. Designed to run as `/loop 15m /dispatch`; iterations are idempotent and safe while implementers are still running. Works in any repo with a docs/goals/ queue. Orchestrates only — never implements in its own context.
---

# Dispatch — the factory orchestrator

You are depth 0: a thin orchestrator. Your context stays small; implementers (depth 1) and
their nested helpers (depth 2+, system cap depth=5) hold the mess. Compose existing skills —
never re-derive what a skill already encodes. The queue is `docs/goals/index.yaml`
(see `define-goal` for the format); PRs live on GitHub (`gh` authenticated). No labels needed.

## Hard rules (every iteration, before any action)

- NEVER merge any PR. Merging is the human's job, always. NEVER push protected branches.
- Read the repo's CLAUDE.md / AGENTS.md hard rules once per session and treat them as law
  (deploy rules, forbidden merges, migration rules). Repeat-check before any git/deploy action.
- **You are the only writer of status in `index.yaml`.** Never run two dispatchers against
  the same repo. Implementers never touch `docs/goals/` — reject PRs that do.
- **Queue writes**: one commit per transition on the default branch —
  `chore(goals): claim|complete|block|archive <id>` — updating the entry's fields in place
  (keep `branch:`/`pr:` for history; dates are YYYY-MM-DD). Push if the repo's rules allow
  pushing the default branch, else keep the commits local and say so in the report.
- WIP cap: at most **2** goals `in_progress` at once; claim at most **1** new goal per
  iteration. Raise the cap only if the user explicitly asks.
- No-progress rule: same PR fails the same way twice with no progress → stop retrying,
  set the goal `blocked` with a `reason`, move on.

## Re-entrancy — how iterations coexist with running work

`/loop` fires between turns, so a new iteration never interrupts a dispatch turn in progress;
missed fires don't stack. Implementers run as background agents, so your turn ends quickly
while they keep working. Each iteration must be idempotent:

1. **The index is the claim ledger.** A claim is a committed status flip on the default
   branch, made BEFORE spawning — never claim from inside a worktree, and never spawn a
   second implementer for an `in_progress` goal that has a live background agent or an
   open PR.
2. **Stale claim**: `in_progress` + no open PR + no live agent → the implementer died.
   Live = a background agent spawned this session that hasn't finished; from a fresh
   session you can't see prior agents — treat no new commits on `goal/<id>` since
   `claimed` as dead. If the implementer's final report named a blocker, set `blocked`
   with that reason. Otherwise respawn
   once with a note of what already exists on its branch; if it dies again, set `blocked`.
3. **Shepherd before claiming** (Phase 1 before Phase 2) so finished work always beats new work.

## Phase 0 — read the queue

Read `docs/goals/index.yaml`. If missing, report "no goals queue — create goals with
/define-goal" and end the iteration. Cheap doctor pass: every entry has its goal file and
vice versa; flag mismatches in the report rather than silently fixing.

## Phase 1 — shepherd in_progress goals

For each `in_progress` entry, find its PR (the `pr:` field, else an open PR from
`branch: goal/<id>`):

1. **PR merged** → set `{status: completed, completed: <date>}`, commit
   `chore(goals): complete <id>`.
2. **CI red** → spawn one agent in that PR's branch worktree to diagnose and push a minimal
   fix. It must use the `systematic-debugging` skill, then `verification-before-completion`
   before pushing.
3. **Unaddressed review comments** (bot or human) → spawn one agent in that worktree to
   address every comment using the `receiving-code-review` skill — verify feedback
   technically, don't blindly apply.
4. **Green + comments addressed** → comment a one-paragraph plain-language status on the PR
   and surface it under needs-you in the report. Do not merge; the goal stays `in_progress`
   until the human merges.
5. **PR newly opened since last iteration** → record `pr: <number>` in the index, commit.

Apply the stale-claim rule from above to entries with no PR and no live agent.

## Phase 2 — claim the next goal

Ready = `status: not_started` AND every `depends_on` entry is `completed`. If fewer than 2
goals are `in_progress`: pick `priority: high` first, then top-most in the file. Claim
atomically BEFORE spawning — set
`{status: in_progress, claimed: <date>, branch: goal/<id>}` and commit per the
queue-writes rule.

## Phase 3 — spawn the implementer (depth 1, background, worktree isolation)

One Agent per claimed goal, `isolation: worktree`, `run_in_background: true`, with this brief:

```
Implement the goal in docs/goals/<id>.md exactly per its "Goal contract" section — read
that file first. You own this work end to end — nested subagents are for context isolation
(explore / write tests / verify in fresh windows), never for passing the whole task down.
At most one level of helpers unless the goal is unusually large.

Method (skills are mandatory, in order):
1. If the change spans >2 files, use the `writing-plans` skill first.
2. Use the `test-driven-development` skill for every code change (failing test first).
   Let this project's domain skills trigger as relevant — check the available-skills list.
3. Before claiming done, use the `verification-before-completion` skill: run every command
   in the goal's acceptance criteria and show output. For UI work, verify in the browser
   (project browser skill if present, else agent-browser) and capture a screenshot.
4. Push your work as branch `goal/<id>` and open the PR with the
   `commit-commands:commit-push-pr` skill if available, else `git push` + `gh pr create`.
   PR body must contain: "Goal: <id>", a plain-language summary a non-engineer can read,
   and the verification evidence.

Constraints: the goal file's "Constraints" section verbatim, plus: never merge anything,
never push protected branches, stay inside your worktree, and NEVER edit docs/goals/ —
the dispatcher owns queue state. If blocked: stop and end your turn with a report of
attempted paths, evidence, the blocker, and what would unlock you — the dispatcher will
mark the goal blocked.
```

## Phase 4 — report (always, exactly one line)

`[dispatch] queue: <ready>/<total> · shepherded: <PRs+outcome or none> · claimed: <id or none> · running: <count> · needs-you: <mergeable PRs / blocked goals / nothing>`

Count `ready`/`total` after this iteration's mutations (total = all index entries).
needs-you lists everything currently waiting on the human — mergeable PRs and ALL blocked
goals, every iteration, not only new ones — that line is the user's phone notification.

## Hygiene

When `completed` entries crowd the index (~20+), move their files to `docs/goals/done/`
and their entries to `docs/goals/archive.yaml` in one `chore(goals): archive` commit.
Agents read the whole index every iteration — keep it small.
