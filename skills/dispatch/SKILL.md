---
name: dispatch
description: Factory dispatcher — use when the user says "/dispatch", "run the factory", wants the docs/goals queue worked, or wants to work one specific queued goal in this session ("work goal 005"). Drains the queue SEQUENTIALLY in one session, on the currently-checked-out branch — one goal at a time, no pull requests, no worktrees, no parallel agents. Each goal gets a foreground implementer, then a LOCAL gate the orchestrator runs authoritatively; PASS keeps a squashed commit on the branch, FAIL rolls back. Works in any repo with a docs/goals/ queue. Orchestrates only — never implements in its own context.
---

# Dispatch — the factory orchestrator

You are depth 0: a thin orchestrator. Your context stays small; the implementer (depth 1)
and its nested helpers (depth 2+, system cap depth=5) hold the mess. Compose existing
skills — never re-derive what a skill already encodes. The queue is `docs/goals/index.yaml`
(see `define-goal` for the format).

Dispatch drains the queue **sequentially, in one session, on the currently-checked-out
branch** (e.g. `staging`). One goal at a time: claim it, spawn a single foreground
implementer that commits its work on this branch, run a LOCAL gate yourself, and on PASS
keep a squashed commit — on FAIL roll the goal back so the branch never carries unverified
work. No pull requests, no worktrees, no `goal/<id>` branches, no parallel/background
implementers.

Read the queue's `config:` block first; defaults when absent:
`base` = the branch dispatch works ON (the started branch — staging, main, or other;
default = the currently checked-out branch), `model: inherit` (sonnet|haiku — applied to
the implementer/fix agents), `skills: []` (repo-wide skill mandates), `verify: []` (the
ordered LOCAL gate — a list of shell commands run top-to-bottom, all must exit 0; e.g.
[ "npm ci", "npm run build", "npm test" ]; empty = auto-detect a single test command, and
if none is found the gate is INCONCLUSIVE, never a silent PASS), `budget` (default none;
`max_goals_per_session` + optional `max_iterations` = the external burnstop).

`config.model` (when not `inherit`) is passed as the `model` parameter on EVERY code-writing
agent you spawn — the implementer and any fix/repair agent alike; it is the repo owner's
depth-vs-weekly-limit trade, not yours to override.

## Hard rules (every iteration, before any action)

- One goal at a time, in this session, on the current branch. There are NO pull requests,
  NO worktrees, NO `goal/<id>` branches. After a goal's work passes the LOCAL gate you keep
  its commit on the branch (squashed to one) and move on. A failed gate rolls the goal back
  to its `gate_base` so the branch never carries unverified work. Implementers never merge.
- Read the repo's CLAUDE.md / AGENTS.md hard rules once per session and treat them as law
  (deploy rules, forbidden merges, migration rules). Repeat-check before any git/deploy action.
- **Every queue write goes through the claim protocol below.** Implementers never touch
  `docs/goals/` — the orchestrator owns queue state.
- No-progress rule: same goal fails the same way twice with no progress → stop retrying,
  set the goal `blocked` with a `reason`, move on.
- Substantive conflicts are never guessed through. A local `git merge`/squash that hits a
  conflict on the current branch means two pieces of work changed the same logic → set the
  goal `blocked`, surface under needs-you, and roll back; never resolve by guessing.
- **Session budget (external brake).** If `config.budget.max_goals_per_session` (or
  `max_iterations`) is set, count goals worked this session. Once a cap is reached, STOP
  claiming new work — let the in-flight goal finish its gate cleanly — surface
  `budget exhausted (<n>/<cap> goals)` under needs-you, and send ONE notification per
  Phase 4 (Claude Code PushNotification; Droid has no PushNotification, so the report line
  carries it). The cap comes from config you cannot edit; that is what makes it a real brake
  and not a soft self-limit.

## Claim protocol — every status write

The index is the claim ledger. A claim is a status flip committed BEFORE implementing:

1. Read `docs/goals/index.yaml` from the working tree (must be clean — dirty → stop and report).
2. Flip exactly one entry to `in_progress` and `git commit -m "chore(goals): claim <id>"`
   (queue commits are always their own commit, never fused with code).
3. Push is OPTIONAL (backup only) and never gated. Sequential mode is single-session; if you
   ever run two dispatch sessions on one local queue they race on index.yaml — don't.

Every status transition uses the same convention — one entry, its own commit:
`chore(goals): claim|complete|block|archive <id>`.

## Re-entrancy — idempotent iterations

A direct `/dispatch` run works the queue top to bottom and stops when it drains or hits the
budget. Each iteration must be idempotent so a re-run after a transient death picks up where
it left off:

1. **The index is the claim ledger.** A claim is a committed status flip made BEFORE the
   implementer runs.
2. **Stale claim**: an `in_progress` entry with no work commits on the branch since its
   `claimed` date and no active agent means a prior implementer died — re-run it (re-spawn
   from its `gate_base`, which is the current HEAD since no work landed). If the implementer's
   final report named a blocker, set `blocked` with that reason. A report that declares
   `GOAL_UNREACHABLE` (the acceptance criteria can be neither satisfied nor shown measurable
   after honest attempts) is a contract defect, not a work failure: set `blocked` with reason
   `contract defect: <criterion> unreachable` and surface it under needs-you as a contract
   amendment (the human re-specifies via `define-goal`) — do NOT respawn it, a re-run hits the
   same unmeasurable check. Otherwise respawn — but distinguish a transient infrastructure
   death (connection closed mid-response, parse error, 529 overloaded: NOT a work failure)
   from a logic blocker. A transient death is not a "fail" toward the no-progress rule; don't
   let it burn the respawn budget — retry it, up to ~3 transient respawns per goal per session,
   after which a goal that still can't make any commit progress IS blocked (named
   `blocked: repeated transient death`) so it can't livelock. Only a real blocker in the final
   report, or repeated failure to make ANY commit progress, sets `blocked` (a goal must never
   sit blocked for hours over one flaky connection).
3. **Finish before claiming** (Phase 1 before Phase 2) so finished work always settles first.

## Phase 0 — read the queue

Confirm the working tree is clean (dirty or diverged → stop and report rather than stash
silently). If `docs/goals/index.yaml` is missing, report "no goals queue — create goals with
/define-goal" and end the iteration.

If `config.base` is set and the current branch != `config.base`, STOP and report — you are on
the wrong working branch; checkout `<config.base>` first (mirroring the per-goal `base:`
mismatch handling in Phase 2 — never silently work on the wrong branch).

**Drained-queue terminal stop.** Dispatch stops when there is nothing left to do: when Phase 2
finds no ready goals AND needs-you is empty, emit `factory drained — <done>/<total> done` and
stop. A later `/dispatch` (or `/loop`) re-run picks up newly-added goals — a `/define-goal` +
`/dispatch` restarts the drain from wherever the queue now stands.

At end-of-drain only (NOT per-goal — no polling), if the working branch has a remote AND `gh`
is available and authenticated, do ONE non-blocking check of the latest CI run on the current
branch (`gh run list --branch <current> --limit 1`); if it is failing, surface it under
needs-you as a non-blocking observation (a CI failure to look at — never block, never wait on
it). If `gh` or the remote is absent, skip silently (`gh` is optional).

Read the queue with a real YAML parser (`python3 -c 'import yaml,sys; …'`), never line-greps
or ad-hoc `jq` — grep probes on the queue invent phantom statuses and miscounts that cost an
extra verification round every fire. Cheap doctor pass, flagged in the report rather than
silently fixed: every entry has its goal file and vice versa; no circular `depends_on`; no
`depends_on` pointing at a missing entry; warn when a goal and its dependency declare
different `base` branches.

On any environment failure you can't handle (missing tooling, an unrunnable `config.verify`
command, a queue the claim protocol can't write), stop the iteration and surface "run
`/factory-doctor`" under needs-you — it diagnoses and fixes setup so the loop stops failing
the same way every fire instead of burning quota on a wall it can't clear.

**Implementer-cost awareness.** When `config.model: inherit` resolves to an expensive model
(you are running on opus) and the queue is mostly `type: chore` (mechanical, no-behavior-
change work), note once in the report that the implementer inherits your model and that
`config.model: sonnet` would cut cost sharply with little risk on chores — the owner decides,
you don't override.

`$PGVALIDATE` resolution (do this once, before the first gate): use the same fallback chain
the surviving scripts use — `$CLAUDE_PLUGIN_ROOT/skills/dispatch/scripts/pg_validate.py`,
else the newest match of
`~/.claude/plugins/{cache,marketplaces}/*/flywheel/*/skills/dispatch/scripts/pg_validate.py`
(also check `~/.factory/plugins/{cache,marketplaces}/*/...` for Droid). Hold the resolved
absolute path in `$PGVALIDATE`.

## Working a goal — the canonical per-goal sequence

For each claimed goal, in order:
1. `anchor` = current HEAD (clean). `git commit` the claim → `gate_base` = HEAD now.
2. Spawn ONE foreground implementer (Agent, run_in_background: false) that works in this
   checkout on the current branch under the method mandates (writing-plans, TDD,
   verification-before-completion) + config.skills + the goal's `skills:`. It commits its
   work on the branch and ends with a verification summary. It never merges, never opens a PR.
3. Run the LOCAL gate authoritatively yourself:
   `python3 "$PGVALIDATE" --head HEAD --base <gate_base> --goal <id> --goal-file docs/goals/<id>.md`
   plus the repo `config.verify` commands (ordered, all must exit 0). Show output.
4. PASS → `git reset --soft <gate_base> && git commit -m "feat(goal <id>): <slug>"` (squash to
   one), then `chore(goals): complete <id>`; push if a remote exists (non-blocking).
   FAIL_FIXABLE → one repair agent, re-gate; still failing → `git reset --hard <gate_base>`,
   `chore(goals): block <id> — <reason>`. FAIL_CONTRACT → reset + block (needs-you contract
   amendment). INCONCLUSIVE → reset + block "no runnable local gate".

`anchor`/`gate_base` matter: the claim's `index.yaml` edit lands BEFORE `gate_base` is set,
so the validated diff (`gate_base..HEAD`) is exactly the implementer's work — never the queue
write. A `git reset --hard <gate_base>` discards only the implementer's commits; the claim
commit survives, ready to be flipped to `blocked` by the claim protocol.

The gate verdict comes from `pg_validate.py`'s JSON `verdict` field (PASS=exit 0,
FAIL_FIXABLE/FAIL_CONTRACT=exit 3 — read the JSON to split them, INCONCLUSIVE=exit 4) AND
the `config.verify` commands (any non-zero exit = the gate fails as FAIL_FIXABLE for that
command's failure). You run the gate — the implementer's verification summary is evidence,
not the verdict.

## Phase 1 — finish in-flight goals

Before claiming anything new, settle every `in_progress` entry — finished work beats new work.
`gate_base` is not stored in `index.yaml`, so on a fresh session recover it from git: it is the
SHA of the goal's claim commit on the current branch,
`git log --grep="chore(goals): claim <id>" --format=%H -1` (the gate then diffs
`gate_base..HEAD`). For each `in_progress` entry, decide by whether work commits exist on the
branch after that claim commit:

1. **Work commits present after the claim commit** → recover `gate_base` as above, then run the
   gate (Working a goal, step 3) against it. PASS → squash + `chore(goals): complete <id>`.
   FAIL_FIXABLE → one repair agent, re-gate; still failing → `git reset --hard <gate_base>` +
   `chore(goals): block <id> — <reason>`. FAIL_CONTRACT → reset + block (needs-you contract
   amendment). INCONCLUSIVE → reset + block "no runnable local gate".
2. **No work commits after the claim commit and no active agent** (stale claim — the
   implementer died) → `gate_base` is the current HEAD (no work landed). Apply the stale-claim
   rule from Re-entrancy: re-spawn the implementer from current HEAD, or `blocked` per its final
   report / `GOAL_UNREACHABLE` / transient-death cap.

## Phase 2 — claim the next goal

Ready = `status: not_started` AND every `depends_on` entry is `completed` — a `blocked`
dependency makes dependents not-ready; report the stuck chain. Pick `priority: high` first,
then top-most in the file; claim via the protocol BEFORE spawning. A per-goal `base:` field
in the index entry overrides `config.base` for that goal (epic integration branches) — but
since dispatch works on the currently-checked-out branch sequentially, a goal whose `base:`
differs from the started branch is surfaced under needs-you (switch branches and run a
separate session), never silently worked on the wrong branch.

If `config.budget` is set and `max_goals_per_session` is exhausted, stop claiming (Hard
rules) and let the current goal finish.

## Phase 3 — spawn the implementer (depth 1, foreground)

One Agent per claimed goal, `run_in_background: false`, NO worktree — it works in THIS
checkout on the current branch. Brief (fill in `<id>` and the resolved skill lists):

```
Implement the goal in docs/goals/<id>.md exactly per its "Goal contract" section — read
that file first. You own this work end to end — nested subagents are for context isolation
(explore / write tests / verify in fresh windows), never for passing the whole task down;
spawn helpers at your own model.

Workspace: you are on the current branch in this checkout — work on the current branch in
this checkout, commit your intended files here. Do NOT create a worktree, do NOT create a
new branch, do NOT open a PR. Run project setup (install deps) and the repo's test baseline;
a dirty baseline is reported, never built on. Failures that are already red on the current
branch before you start (unrelated suites, missing-secret/env environments) are pre-existing,
not your regression: note them and move on — do not fix them, and they do not block your goal.

Skills are mandatory — invoke each via the Skill tool:
1. BEFORE touching the work they cover: <config.skills + the goal frontmatter's skills:>.
2. `writing-plans` first if the change spans >2 files.
3. `test-driven-development` for every code change (failing test first). Let other
   domain skills trigger as relevant — check the available-skills list. When the goal
   cites a bug, finding, or root-cause hypothesis, reproduce it against the real code
   FIRST — upstream findings are hypotheses, not facts, and some will be wrong. If the
   code is already correct, lock it in with a test and say so; never "fix" code you cannot
   first demonstrate is broken.
4. `verification-before-completion` before claiming done: run every command in the
   goal's acceptance criteria and show output. For UI work, run the goal's SCRIPTED browser
   check (start the dev server, drive it with `agent-browser`, ASSERT a concrete visible
   result — element/text/count — not just a page-load) and attach the screenshot as evidence;
   a screenshot with no assertion is not verification.

Finish: before committing, review your diff and stage only the files you meant to change —
revert stray lockfile / dependency-manager / formatter churn, or any file you didn't intend
to touch, that the toolchain introduced (never `git add -A` blind). Commit your intended
files on the current branch and end with verification evidence (the commands you ran and
their output). Do NOT merge anything, do NOT push, do NOT open a PR — the orchestrator runs
the gate and integrates.

Constraints: the goal file's "Constraints" section verbatim, plus: never merge, never push,
never open a PR, and NEVER edit docs/goals/ — the orchestrator owns queue state. If blocked:
stop and end your turn with a report of attempted paths, evidence, the blocker, and what
would unlock you — the dispatcher will mark the goal blocked. If after ~3 honest attempts the
acceptance criteria cannot be made green AND you cannot show the target is even
measurable/reachable (a flaky, non-deterministic, or contradictory check), end your turn
declaring `GOAL_UNREACHABLE: <which criterion, why unmeasurable, last measurement>` instead
of churning your whole window — never retry the identical failing approach; the dispatcher
routes that to a needs-you contract amendment.
```

After the implementer returns, run the gate yourself (Working a goal, steps 3–4). A
`FAIL_FIXABLE` verdict spawns ONE repair agent (same brief, `model: config.model`, fed the
gate findings); a second identical FAIL → roll back + block.

## Solo mode — work one named goal in this session

The default model is already one-goal-at-a-time on the current branch, so "work goal 005"
just scopes the iteration to a single id: skip Phase 2's ready-scan, claim goal 005 directly
via the protocol, and run it through Working a goal (anchor → claim → foreground implementer
→ local gate → PASS squash+complete / FAIL roll back+block). Everything else — the brief, the
gate, the rollback — is identical.

## Phase 4 — report (always, exactly one line)

`[dispatch] <done>/<total> done [<bar>] · ready: <count> · blocked: <count> · current: <id or none> · last: <id PASS|FAIL|none> · needs-you: <blocked goals + human decisions, or nothing>`

Lead with **progress** (`<done>/<total>`), never `ready/total` — a bare `ready/total` reads
as "nothing done" to a human. Every number carries its label. The counts come from the index
after this iteration's mutations:
- `done` = completed · `ready` = not_started with all `depends_on` completed (claimable now) ·
  `blocked` = `blocked` status or not_started with an unmet dependency · `current` = the goal
  being worked this fire (or none) · `last` = the most recently gated goal and its verdict.

The bar is 20 cells: `filled = round(20 × done ÷ total)` (0.5 rounds up), clamped to [0, 20];
empty = 20 − filled. Filled cells = █, empty = ░; omit the whole bar when total = 0.
Anchor example: 19/21 → round(18.10) = 18 filled → `[██████████████████░░]`.

needs-you lists everything currently waiting on the human: every goal with explicit `blocked`
status (with the dependents stuck behind it), `GOAL_UNREACHABLE`/`FAIL_CONTRACT` contract
amendments, a `base:`-mismatched goal needing a branch switch, and `budget exhausted`. A
**dep-blocked** goal (not_started, waiting on another goal still running or not yet ready) is
NOT human-blocked: it unblocks on its own, so it never appears here on its own — only as a
"dependent stuck behind" a goal that is human-blocked. Every iteration, not only new ones.

**Stalled factory → one real notification.** A report line in an unattended run has no reader.
The fire that first finds the factory fully stalled — needs-you non-empty and nothing this
iteration could do about it — sends the needs-you line via the PushNotification tool
(ToolSearch loads it if deferred) in Claude Code. In Droid there is no PushNotification tool;
surface the stalled state in the report line only. One notification per distinct blocker set;
identical no-op fires after it send no further notifications, though the report line still goes
out every fire — new blocker content notifies again.

**Heartbeat (liveness) — every fire.** Write a one-line heartbeat —
`<UTC timestamp> · <done>/<total> · current <id or none> · drained <yes|no>` — to the runtime
cache at `~/.local/state/pg-dispatch/<SLUG>/heartbeat` (`<SLUG>` = the repo dir name;
`mkdir -p` then overwrite the file). A silently-dead orchestrator (a 500 / context-exhaustion
mid-turn) emits nothing, so the next `/dispatch` — or an external watcher — compares the
heartbeat's age to the expected cadence and treats a long silence as a dead-loop signal,
turning silent death into a detectable anomaly. The drained flag also feeds the drained-queue
terminal stop (Phase 0). `factory-doctor`'s queue-liveness probe reports the same staleness
from the queue side (stale `in_progress` claims).

## Hygiene

When `completed` entries crowd the index (~20+), move their files to `docs/goals/done/`
and their entries to `docs/goals/archive.yaml` in one `chore(goals): archive` commit. The
queue commit is always its own step (see the claim protocol). Agents read the whole index
every iteration — keep it small.
