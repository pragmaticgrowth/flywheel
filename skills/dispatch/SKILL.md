---
name: dispatch
description: Factory dispatcher — use when the user says "/dispatch", "run the factory", wants the docs/goals queue worked, or wants to work one specific queued goal in this session ("work goal 005"). Shepherds factory PRs through review, claims queued goals, and spawns one isolated implementer agent per goal. Designed to run as `/loop 15m /dispatch` (Claude Code) or `CronCreate` same_session every 15m (Droid); iterations are idempotent, and parallel sessions are safe. Works in any repo with a docs/goals/ queue. Orchestrates only — never implements in its own context.
---

# Dispatch — the factory orchestrator

**CLI detection**: this skill works in both Claude Code and Droid (Factory CLI). Detect
your runtime: if Droid-specific tools (CronCreate, CreateAutomation) are available or
`$DROID_PLUGIN_ROOT` is set, you are in Droid. Otherwise Claude Code. Both CLIs set
`$CLAUDE_PLUGIN_ROOT` (Droid provides it as an alias for `$DROID_PLUGIN_ROOT`), so path
resolution using that env var works in both. Where this document references `/loop`,
the Droid equivalent is `CronCreate` with `same_session: true`. Where it references
`.claude/settings.local.json`, the Droid equivalent is `.factory/settings.local.json`.
Where it references `~/.claude/plugins/`, also check `~/.factory/plugins/`.

You are depth 0: a thin orchestrator. Your context stays small; implementers (depth 1) and
their nested helpers (depth 2+, system cap depth=5) hold the mess. Compose existing skills —
never re-derive what a skill already encodes. The queue is `docs/goals/index.yaml`
(see `define-goal` for the format); PRs live on GitHub (`gh` authenticated) when a remote
host exists.

Read the queue's `config:` block first; defaults when absent:
`base` = the repo's default branch (the integration branch goals branch FROM and merge
BACK to — main, staging, or any other), `merge: pr` (human merges; `auto` = the
orchestrator merges back after gates), `wip: 2`, `model: inherit`, `skills: []`,
`validation: risk_based` (off | risk_based | required — whether a deterministic PR
check runs before auto-merge; see the Validate step in Integration). When `validation` is
on, `llm_validation: off` (off | on — opt-in adversarial LLM check on top of the
deterministic gate; costs tokens), `validator_model: sonnet` (never `inherit`),
`validation_attempts: 2` (LLM FAIL→repair rounds before blocked) govern the LLM layer
(step 2c).
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
- WIP cap: at most `config.wip` goals `in_progress` at once, AND **every iteration ends
  with `min(config.wip, ready)` implementers live** — after you claim and spawn one goal,
  re-check the slot count and claim again, repeating until the cap is full or no ready goal
  remains. "One claim-protocol round at a time" is about commit atomicity (one entry, one
  commit), NOT a one-claim-per-iteration cap; a fire triggered by a single implementer's
  exit must refill every empty slot, not just the one that opened.
- No-progress rule: same PR fails the same way twice with no progress → stop retrying,
  set the goal `blocked` with a `reason`, move on.

## Claim protocol — every status write, multi-session safe

Parallel sessions may work the same queue; `origin/<base>` push acceptance is the arbiter.

1. On the `<base>` checkout: `git fetch origin && git pull --ff-only origin <base>`.
2. Edit exactly one entry, updating fields in place (keep `branch:`/`pr:` for history;
   dates YYYY-MM-DD). Claiming writes
   `{status: in_progress, claimed: <date>, branch: goal/<id>}`. One commit per transition:
   `chore(goals): claim|complete|block|archive <id>`. The queue commit and its push are
   their OWN command — never bundle them with branch pruning, worktree cleanup, or any
   other optional or destructive op. A denial or failure of bundled hygiene must never take
   down a queue write.
3. Push. Rejected → `git pull --rebase` and look again: if another session took your goal,
   discard your claim commit (`git rebase --skip` it, or hard-reset to the remote) so your
   tree matches `origin/<base>`, then re-pick from ready; if your entry survived, push
   again. Max 3 attempts per transition (a re-pick starts a new one), then stop and report.

If the repo forbids pushing `<base>` directly, parallel sessions are NOT safe — run a
single dispatcher, keep queue commits local, and say so in the report.

## Re-entrancy — how iterations coexist with running work

The scheduler (`/loop` in Claude Code, `CronCreate` with `same_session: true` in Droid)
fires between turns, so a new iteration never interrupts a dispatch turn in progress;
missed fires don't stack. Implementers run as background agents, so your turn ends quickly
while they keep working. Each iteration must be idempotent:

**Direct `/dispatch` (no loop/cron) has no recovery fire.** A transient death mid-turn — yours
(a 500/529 processing an implementer's completion) or an implementer's — is NOT recovered
automatically the way a scheduled fire would. The work isn't lost (claims and branch commits are
already pushed), so just **re-run `/dispatch`**: the next iteration's Phase 1 shepherds whatever
the implementers finished, and the stale-claim rule respawns anything that died. For unattended
runs prefer `/loop 15m /dispatch` (Claude Code) or `CronCreate` same_session every 15m (Droid)
so these recover on their own.

1. **The index is the claim ledger.** A claim is a pushed status flip made BEFORE spawning —
   never claim from inside a worktree, and never spawn a second implementer for an
   `in_progress` goal that has a live background agent (under `execution: herdr`, a
   `lanes`-visible pane) or an open PR.
2. **Stale claim**: `in_progress` + no open PR + no live agent → the implementer died.
   Live = a background agent spawned this session that hasn't finished; from a fresh
   session you can't see prior agents — treat no new commits on `goal/<id>` since
   `claimed` as dead. If the implementer's final report named a blocker, set `blocked`
   with that reason. Otherwise respawn — but distinguish a transient infrastructure death
   (connection closed mid-response, parse error, 529 overloaded: NOT a work failure) from a
   logic blocker. A transient death is not a "fail" toward the no-progress rule; don't let
   it burn the respawn budget — retry it, up to ~3 transient respawns per goal per session,
   after which a goal that still can't make any commit progress IS blocked (named
   `blocked: repeated transient death`) so it can't livelock. Otherwise only a real blocker
   in the final report, or repeated failure to make ANY commit progress, sets `blocked`
   (a goal must never sit blocked for hours over one flaky connection). When you
   respawn a goal whose branch has fallen far behind `<base>` (many merges landed since
   `claimed`), branch fresh from `origin/<base>` and pass the stale branch's plan as
   optional context — don't burn a long rebase resuming a now-worthless checkpoint. Under
   `execution: herdr`, "live" instead
   means a `lanes`-visible pane on `goal/<id>` (cross-session visible via the herdr
   server), and respawn-once is tracked by the mission's `respawned` flag — see
   `references/herdr-mode.md`.
3. **Shepherd before claiming** (Phase 1 before Phase 2) so finished work always beats new work.

## Phase 0 — sync and read the queue

Switch the main checkout to `<base>` and `git pull --ff-only` (dirty or diverged checkout →
stop and report rather than stash silently). If `docs/goals/index.yaml` is missing, report
"no goals queue — create goals with /define-goal" and end the iteration. Read the queue with
a real YAML parser (`python3 -c 'import yaml,sys; …'`), never line-greps or ad-hoc `jq` —
grep probes on the queue invent phantom statuses and miscounts that cost an extra
verification round every fire. Cheap doctor pass, flagged in the report rather than silently
fixed: every entry has its goal file and vice versa; no circular `depends_on`; no
`depends_on` pointing at a missing entry; warn when a goal and its dependency declare
different `base` branches.

On any environment failure you can't handle (gh unauthenticated, no merge allow-rule,
protected base blocking the claim protocol), stop the iteration and surface "run
`/factory-doctor`" under needs-you — it diagnoses and fixes setup so the loop stops failing
the same way every fire instead of burning quota on a wall it can't clear.

**Implementer-cost awareness.** When `config.model: inherit` resolves to an expensive model
(you are running on opus) and the queue is mostly `type: chore` (mechanical, no-behavior-
change work), note once in the report that implementers inherit your model and that
`config.model: sonnet` would cut cost sharply with little risk on chores — the owner decides,
you don't override.

**Execution substrate (`config.execution`, default `native`).** `native` = this
document's in-process background-agent path (Phases 1–3, Integration). `herdr` = spawn
each implementer as a fresh `claude` in an isolated herdr worktree pane; when set,
**follow `references/herdr-mode.md`** for the spawn substrate (Phases 1/3, monitoring,
block handling, integration mechanics) — the claim protocol, queue rules, `config`
semantics, Integration, the permission-stall protocol, and Phase 4 reporting in this
file are unchanged and still authoritative. One behavioral addition: herdr mode adds a
`config.autonomy`-gated tier that can auto-answer a blocked implementer before falling
back to the no-progress/`blocked` rule (reference, Phase 4b). If `execution: herdr` but
herdr is unreachable, degrade to `native` and note it in the report. **Droid note:**
herdr mode currently supports the `claude` backend only; a `droid` backend is planned but
not yet implemented. In Droid, `execution: herdr` degrades to `native` today.

## Phase 1 — shepherd in_progress goals

For each `in_progress` entry, find its PR (the `pr:` field, else an open PR from
`branch: goal/<id>`):

1. **PR merged** → set `{status: completed, completed: <date>}` via the claim protocol;
   delete the merged `goal/<id>` branch and prune its worktree. Merged or completed by
   someone else (a watching human, or a parallel session) is the SAME case, never an error
   to reconcile defensively — adopt the result and move on. Under `merge: auto` on a slow
   loop this is common: a PR you open this fire is usually still mid-CI when the fire ends,
   so it gets merged a later fire (or by the human first). To do your share, sweep
   merge-ready PRs at the TOP of every fire — Phase 1 runs before Phase 2 precisely so
   finished work merges before you claim more.
2. **CI red** → spawn one agent in that PR's branch worktree to diagnose and push a minimal
   fix. It must use the `systematic-debugging` skill, then `verification-before-completion`
   before pushing.
3. **Unaddressed review comments** (bot or human) → spawn one agent in that worktree to
   address every comment using the `receiving-code-review` skill — verify feedback
   technically, don't blindly apply; a comment that doesn't hold up gets a reasoned reply,
   not a change. Converged = every blocking comment resolved and only cosmetic nits remain;
   stop there (cap ~3 review rounds per PR, then surface leftover nits under needs-you)
   rather than chasing fresh nits each cycle. A converged PR counts as "comments addressed"
   for case 4 — cosmetic nits parked under needs-you don't hold it open. If review keeps
   flagging the same pattern that the goal's OWN acceptance criteria mandated, the contract
   is the problem, not the PR — keep the goal `in_progress` and surface it under needs-you as
   a contract amendment for the human (never `blocked`, which would free the slot; never edit
   the contract yourself) instead of merging the same contract-mandated defect across PR
   after PR.
4. **Green + comments addressed** → under `merge: pr`, comment a one-paragraph
   plain-language status on the PR and surface it under needs-you; do not merge. Under
   `merge: auto`, run Integration below.
5. **PR newly opened since last iteration** → record `pr: <number>` via the claim protocol.

Apply the stale-claim rule from above to entries with no PR and no live agent.

## Integration (merge: auto) — orchestrator only, one goal at a time

**Merge-rights preflight** (once per session, before the first integration spends
anything on sync or gates): the merge step runs the verified-merge wrapper
`python3 "$SAFEMERGE"` — resolve `$SAFEMERGE` once like `$PM`
(`$CLAUDE_PLUGIN_ROOT/skills/dispatch/scripts/pg_safe_merge.py`, else newest
`~/.claude/plugins/{cache,marketplaces}/*/pg-plugin/*/skills/dispatch/scripts/pg_safe_merge.py`
or `~/.factory/plugins/{cache,marketplaces}/*/pg-plugin/*/skills/dispatch/scripts/pg_safe_merge.py`),
so the allow-rule it needs is `Bash(python3 <abs path>/pg_safe_merge.py:*)` — narrow to
that one script, NOT the broad `Bash(gh pr merge:*)`. Check `permissions.allow` for it in
the repo's `.claude/settings.json` / `.claude/settings.local.json` (Claude Code) or
`.factory/settings.json` / `.factory/settings.local.json` (Droid), or user-scope settings.
No rule found and the session is unattended (this iteration was fired by a schedule, not
typed by a human — no one can approve a prompt) → go straight to the permission-stall
protocol below instead of burning gates on a merge that will be denied. `/factory-doctor`
writes this rule for you. Interactive sessions proceed; the permission prompt arbitrates.

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
2b. **Validate (deterministic gate — only when `config.validation != off` and the goal is
   in-scope: `risk_based` requires it for `type: bug|feature` and risk-flagged chores;
   `required` for all; `off` skips to step 3). A chore is **risk-flagged** if its changed
   paths touch auth/payments/migrations/deploy/prod config/deps, or span >12 files (low-risk
   mechanical chores skip validation — they already prove no-behavior-change before/after).
   Create a fresh detached worktree of the synced PR head (`git worktree add --detach <tmp>
   <head-sha>`); resolve `$PGVALIDATE`
   like `$SAFEMERGE`/`$PM` and run `python3 "$PGVALIDATE" --pr <n> --goal <id> --base <base>
   --goal-file docs/goals/<id>.md --worktree-root <tmp>`. Read the JSON `verdict` field to
   split FIXABLE vs CONTRACT (both FAILs exit 3, so the exit code alone is insufficient;
   PASS=0, INCONCLUSIVE=4). `PASS` → record the validated `sha_head`/`sha_base` and use them
   as Merge's `--expected-head/--expected-base`; `FAIL_FIXABLE` → spawn ONE worker-repair
   agent in the branch worktree with the findings (cap one repair; an identical second FAIL
   → `blocked`/needs-you); `FAIL_CONTRACT` → keep the goal `in_progress` (holds its slot),
   surface a contract amendment under needs-you, never churn the worker; `INCONCLUSIVE` →
   transient, retry next fire, never default-PASS. **Leave this worktree in place —
   step 2c (LLM validator, if enabled) reuses it, and it is pruned once after step 3
   Merge.** A deterministic FAIL overrides everything —
   never route around it with a manual merge.
2c. **Validate (LLM, semantic — only when `config.llm_validation: on` AND step 2b's
   deterministic gate PASSED).** Skipped if `llm_validation: off` (default), or if step 2b
   didn't PASS (a deterministic FAIL always wins — never run the LLM layer over a PR the
   deterministic gate already rejected). Spawn ONE background Agent (`isolation: worktree`
   REUSING the step-2b worktree, `run_in_background: true`, `model: <config.validator_model>`)
   with the LLM-VALIDATOR BRIEF below (filled in). It is strictly read-only. Read its final
   message for `VERDICT: <PASS|FAIL_FIXABLE|FAIL_CONTRACT|INCONCLUSIVE> — <reason> | evidence: …`
   and act: PASS with all required evidence present → proceed to Merge (SHAs already validated
   in 2b); PASS MISSING required evidence (no commands run / no criterion→diff map / no
   adversarial probe) → malformed, respawn the validator ONCE insisting on the evidence, still
   malformed → INCONCLUSIVE/needs-you; FAIL_FIXABLE → spawn ONE worker-repair agent with the
   findings (cap = `config.validation_attempts`, default 2; identical second FAIL →
   `blocked`/needs-you); FAIL_CONTRACT → keep the goal `in_progress` (holds its slot), surface
   a contract amendment under needs-you, never churn the worker; INCONCLUSIVE → retry once
   next fire, never default-PASS. A NON-actionable FAIL (no concrete file:line/criterion/
   command) is invalid → treat as PASS-with-warning (proceed to Merge, but report the
   unactionable finding under needs-you), never bounce the worker on vibes.

   **LLM-VALIDATOR BRIEF** (fill in `<id>`, `<base>`, `<head-sha>`, `<base-sha>`):

   ```
   You are an INDEPENDENT validator for goal <id> (read-only — never edit, push, or merge).
   You are adversarial: your default verdict is FAIL; PASS must be EARNED with evidence you
   produce and the orchestrator can re-run. You are given ONLY the contract and the change —
   not the author's reasoning.

   Inputs: the goal contract at docs/goals/<id>.md (read it first); branch goal/<id> at head
   SHA <head-sha> off <base> (<base-sha>); the raw diff (git diff origin/<base>..<head-sha>).
   Do NOT read any PR body, plan, or commit messages — judge the change on its own merits.

   Produce your verdict by doing ALL of:
   1. criterion→diff map: for every acceptance criterion in the contract, cite the file:line
      hunk that satisfies it (FAIL if a criterion has no corresponding change). For every
      changed hunk, name the criterion/constraint it serves (flag any change with no
      criterion = scope creep).
   2. outcome check: does the change satisfy the contract's Outcome sentence (not just make
      the named commands exit 0)? State the one user/API-visible behavior you'd point to.
   3. adversarial probe: write ONE check the author did NOT write, derived from the contract,
      run it on this checkout, and paste the command + output.
   4. no-op reasoning: if you null-reverted the core change, which existing tests would fail?
      Name them. If none would, that is a red flag — say so.

   Your FINAL line must be EXACTLY:
   VERDICT: <PASS|FAIL_FIXABLE|FAIL_CONTRACT|INCONCLUSIVE> — <one-sentence reason> | evidence:
   <commands run + exit codes; criterion→diff map summary; adversarial-probe result;
   residual-risk note>

   Rules: never merge, never edit docs/goals/, never push, stay read-only. A PASS without the
   evidence above is not a PASS.
   ```
3. **Merge**: `python3 "$SAFEMERGE" --pr <n> --goal <id> --base <base> --expected-head
   <the SHA Validate recorded; or, if validation was off/skipped, the gate-verified head SHA>
   --expected-base <likewise>` when a PR exists. The
   wrapper re-verifies branch/body/base/checks/SHAs and that the PR touches no `docs/goals/`
   file, then merges with the repo's allowed method and `--delete-branch`. Exit 3 = it
   REFUSED (a verification failed — read the reasons, treat as a real blocker; do NOT route
   around it with raw `gh pr merge`); exit 4 = environment/gh failure (transient — retry
   next fire); exit 0 = merged. With no remote host, `git merge --no-ff goal/<id>` on the
   `<base>` checkout and push. Push rejected → base moved again → back to step 1 (max 3
   attempts this iteration, then leave it for the next). A permission denial of the wrapper
   command itself is NOT a push race — permission-stall protocol below.
4. Flip `completed` via the claim protocol; prune the worktree.

### Permission stall — the harness denies the orchestrator's merge

A denied merge wrapper is an environment blocker, not a work failure: don't route around
it with raw `gh pr merge`/`git merge`, don't retry it blindly each fire, and don't flip the goal
`blocked` — the work is finished and verified, and `blocked` would free its wip slot,
letting the factory pile up more PRs against the same wall. Instead:

1. Keep the goal `in_progress` (with `pr:` recorded) — it holds its slot on purpose.
   State the gate-verified head and base SHAs in your report; that record is what a
   later fire (or fresh session) compares against. No record → treat as moved.
2. needs-you carries the exact fix, verbatim: run `/factory-doctor` (it writes the rule),
   or merge the PR manually (`gh pr merge <n> --squash --delete-branch`), or add
   `"Bash(python3 <abs path>/pg_safe_merge.py:*)"` to `permissions.allow` in
   `.claude/settings.local.json` (Claude Code) or `.factory/settings.local.json` (Droid)
   — one-time, unblocks every future auto-merge.
3. Send the stalled-factory notification (Phase 4), once.
4. Later fires probe cheaply instead of re-running Integration: PR merged by a human →
   Phase 1 case 1; allow rule now present → resume Integration, re-running gates only
   if the PR head or base moved since you verified them (the one exception to "a gate
   that passed before the sync doesn't count" — valid only while both are provably
   unmoved). Neither → nothing further this fire beyond the Phase 4 report line; no
   repeat notification.

## Phase 2 — claim the next goal(s)

Ready = `status: not_started` AND every `depends_on` entry is `completed` — a `blocked`
dependency makes dependents not-ready; report the stuck chain. Loop, filling every free
slot in this one iteration: **while `in_progress` count < `config.wip` AND a ready goal
remains** — pick `priority: high` first, then top-most in the file; claim via the protocol
BEFORE spawning; spawn (Phase 3); then loop back and fill the next slot. Each claim is one
atomic protocol round (one entry per commit), but you do as many rounds as there are free
slots — spawning a background agent returns immediately, so filling all of them costs one
turn, not one turn per goal. A per-goal `base:` field in the index entry overrides
`config.base` for that goal (epic integration branches).

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
(`git switch -c goal/<id> origin/<base>` if not already). Run every command from THIS
worktree — never `cd` into the main checkout path: doing so silently measures and edits
the base branch, not your work, and a baseline that suddenly looks "unfinished" is the #1
sign you ran in the wrong tree. Use paths relative to your worktree, or `git -C <this
worktree>`. Run project setup (install deps) and the repo's test baseline; a dirty
baseline is reported, never built on. Failures that are already red on origin/<base>
(unrelated suites, missing-secret/env environments) are pre-existing, not your regression:
note them and move on — do not fix them, and they do not block your goal.

Skills are mandatory — invoke each via the Skill tool:
1. BEFORE touching the work they cover: <config.skills + the goal frontmatter's skills:>.
2. `writing-plans` first if the change spans >2 files.
3. `test-driven-development` for every code change (failing test first). Let other
   domain skills trigger as relevant — check the available-skills list. When the goal
   cites a bug, finding, or root-cause hypothesis, reproduce it against the real code
   FIRST — upstream findings are hypotheses, not facts, and some will be wrong. If the
   code is already correct, lock it in with a test and say so in the PR; never "fix" code
   you cannot first demonstrate is broken.
4. `verification-before-completion` before claiming done: run every command in the
   goal's acceptance criteria and show output. For UI work, run the goal's SCRIPTED browser
   check (start the dev server, drive it with `agent-browser`, ASSERT a concrete visible
   result — element/text/count — not just a page-load) and attach the screenshot as evidence;
   a screenshot with no assertion is not verification.

Finish: before committing, review your diff and stage only the files you meant to change —
revert stray lockfile / dependency-manager / formatter churn — or any file you didn't
intend to touch — that the toolchain introduced (never `git add -A` blind). Then push goal/<id> and open a PR targeting <base> —
`gh pr create --base <base>` — with body containing "Goal: <id>", a plain-language summary
a non-engineer can read, and the verification evidence. Do NOT merge anything — the
orchestrator integrates per the queue config.

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

`[dispatch] <done>/<total> done [<bar>] · ready: <count> · running: <count>/<wip> (<ids>) · blocked: <count> · shepherded: <PRs+outcome or none> · claimed: <id(s) or none> · model: <implementer model> · needs-you: <mergeable PRs / human-blocked goals / nothing>`

Lead with **progress** (`<done>/<total>`), never `ready/total` — a bare `ready/total` reads
as "nothing done" to a human. Every number carries its label. The four counts partition
`total` and must sum to it (computed from the index after this iteration's mutations):
- `done` = completed · `running` = in_progress implementers · `ready` = not_started with all
  `depends_on` completed (claimable now) · `blocked` = the rest (`blocked` status or
  not_started with an unmet dependency).

The bar is 20 cells: `filled = round(20 × done ÷ total)` (0.5 rounds up), clamped to [0, 20];
empty = 20 − filled. Filled cells = █, empty = ░; omit the whole bar when total = 0.
Anchor example: 19/21 → round(18.10) = 18 filled → `[██████████████████░░]`.

needs-you lists everything currently waiting on the human: mergeable PRs and every goal with
explicit `blocked` status — for each, note the dependents stuck behind it. A **dep-blocked**
goal (not_started, waiting on another goal that is still running or not yet ready) is NOT
human-blocked: it unblocks on its own as its dependency merges, so it never appears here on
its own — only as a "dependent stuck behind" a goal that is human-blocked. Every iteration,
not only new ones.

**Stalled factory → one real notification.** A report line in an unattended scheduled run
has no reader. The fire that first finds the factory fully stalled — needs-you non-empty,
zero live implementers, and nothing this iteration could do about it (a fresh permission
denial counts immediately, on the fire it happens, even while implementers are still
running — it gates everything they will produce) — sends the needs-you line via the
PushNotification tool (ToolSearch loads it if deferred) in Claude Code. In Droid there is
no PushNotification tool; surface the stalled state in the report line only (a Droid
same-session cron has no external reader either). One notification per distinct
blocker set; identical no-op fires after it send no further notifications, though the
report line still goes out every fire — new blocker content notifies again.

## Hygiene

When `completed` entries crowd the index (~20+), move their files to `docs/goals/done/`
and their entries to `docs/goals/archive.yaml` in one `chore(goals): archive` commit.
Run `git worktree prune`. Before deleting any `goal/*` branch, confirm its PR is actually
MERGED (`gh pr view <branch> --json state`) — never delete a branch whose PR is still open;
that closes the PR and destroys unmerged work. Prune as its own step, never fused to a queue
commit (see the claim protocol); lingering merged branches are harmless, so when in doubt
leave them. Agents read the whole index every iteration — keep it small.
