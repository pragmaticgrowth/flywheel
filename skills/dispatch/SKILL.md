---
name: dispatch
description: Factory dispatcher — use when the user says "/dispatch", "run the factory", wants the docs/goals queue worked, or wants to work one specific queued goal in this session ("work goal 005"). Works ONE ready goal per run, on the currently checked-out branch — no pull requests, no worktrees, no parallel implementers. The single foreground implementer follows TDD and a lightweight subagent-driven quality loop, then the orchestrator runs the LOCAL gate authoritatively. Works in any repo with a docs/goals/ queue. Orchestrates only — never implements in its own context.
---

# Dispatch — the factory orchestrator

You are depth 0: a thin orchestrator. Your context stays small; the implementer (depth 1)
and its nested helpers (depth 2+, system cap depth=5) hold the mess. Compose existing
skills — never re-derive what a skill already encodes. The queue is `docs/goals/index.yaml`
(see `define-goal` for the format).

Dispatch works **one ready goal per run, on the currently checked-out branch**
(e.g. `staging`). One goal at a time: claim it, spawn a single foreground implementer that
commits its work on this branch, run a LOCAL gate yourself, and on PASS keep a squashed
commit — on FAIL roll the goal back so the branch never carries unverified work. No pull
requests, no worktrees, no `goal/<id>` branches, no parallel/background implementers, no
agent-team teammates.
This sequential, single-branch, worktree-free shape is deliberate scar tissue, not an
unfinished simplification: v3's per-goal worktree PRs + parallel `wip` implementers +
CI-gated auto-merge livelocked on real autonomous runs — PR-shepherding churn, CI runners
blocking every merge, and stale `goal/*`/`worktree-agent-*` branch garbage (see CHANGELOG
4.0.0). Do NOT reintroduce worktrees or cross-goal parallelism without re-reading why they
were removed; the extra concurrency lives INSIDE one goal (read-only recon/review), never
across goals.
Use `/loop /dispatch` (Claude Code) or a same-session Droid cron to repeat this one-goal
cycle until the queue is drained.

Read the queue's `config:` block first; defaults when absent:
`base` = the branch dispatch works ON (the started branch — staging, main, or other;
default = the currently checked-out branch), `model: inherit` (opus|sonnet|haiku — the
repo-wide DEFAULT for implementer/fix agents; a goal file's own frontmatter `model:`
overrides it per goal), `skills: []` (repo-wide skill mandates), `verify: []` (the
ordered LOCAL gate — a list of shell commands run top-to-bottom, all must exit 0; e.g.
[ "npm ci", "npm run build", "npm test" ]; empty = auto-detect a single test command, and
if none is found the gate is INCONCLUSIVE, never a silent PASS), `budget` (default none;
`max_goals_per_session` + optional `max_iterations` = the external burnstop).

**Implementer-model resolution — per goal, before each spawn.** Resolve the model for a
goal's code-writing agents in this order: the goal file's frontmatter `model:` field
(`inherit | opus | sonnet | haiku` — stamped by define-goal at contract-writing time as the
goal author's difficulty call), else `config.model`, else `inherit`. A non-`inherit` value is
passed as the `model` parameter on EVERY code-writing agent you spawn for THAT goal — the
implementer and any fix/repair agent alike; `inherit` means omit the parameter so the agent
runs your session model. This split is the token-efficiency lever: the orchestrator stays on
the session's strong model for claim/gate/review judgment while well-specified goals run
cheap implementers, and only the judgment-heavy goals get the expensive one. Neither field
is yours to override, and neither ever applies to recon/review read-only agents — those
always inherit the session model. In Droid there is no Anthropic alias namespace: resolve
the alias through the queue's `config.droid_models` map (alias → concrete Droid model ID,
e.g. `sonnet: claude-sonnet-4-6` or `opus: custom:<name>`; factory-doctor writes it by
asking the owner) and pass the mapped ID as the spawn's model. No map, no entry for that
alias, or the runtime rejects the mapped ID → resolve to `inherit` and surface it under
needs-you ("model alias unmapped, ran inherit — run /factory-doctor to map models";
informational, the goal still runs). Never invent the translation yourself —
Droid owners can run many custom models, and only the owner's answer (the map) says which
one an alias means.

## Hard rules (every iteration, before any action)

- One goal per run, in this session, on the current branch. There are NO pull requests,
  NO worktrees, NO `goal/<id>` branches. After a goal's work passes the LOCAL gate you keep
  its commit on the branch (squashed to one) and stop the run. A failed gate rolls the goal
  back to its `gate_base` so the branch never carries unverified work. Implementers never
  merge.
- Read the repo's CLAUDE.md / AGENTS.md hard rules once per session and treat them as law
  (deploy rules, forbidden merges, migration rules). Repeat-check before any git/deploy action.
- **Every queue write goes through the claim protocol below.** Implementers never touch
  `docs/goals/` — the orchestrator owns queue state.
- No-progress rule: same goal fails the same way twice with no progress → stop retrying,
  set the goal `blocked` with a `reason`, report, and stop the run. (Orchestrator-level —
  distinct from the implementer's own ~3-honest-attempts rule inside one spawn.)
- Substantive conflicts are never guessed through. A local `git merge`/squash that hits a
  conflict on the current branch means two pieces of work changed the same logic → set the
  goal `blocked`, surface under needs-you, and roll back; never resolve by guessing.
- **Session budget (external brake).** If `config.budget.max_goals_per_session` (or
  `max_iterations`) is set, count this run as one worked goal. Because dispatch never claims
  a second goal in the same run, `max_goals_per_session: 1` is the natural default behavior;
  lower/zero or exhausted caps stop before claiming. Let any in-flight goal finish its gate
  cleanly, surface `budget exhausted (<n>/<cap> goals)` under needs-you, and send ONE
  notification per Phase 4 (Claude Code PushNotification; Droid has no PushNotification, so
  the report line carries it). The cap comes from config you cannot edit; that is what makes
  it a real brake and not a soft self-limit.

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

A direct `/dispatch` run settles in-flight work first, then claims at most one new ready
goal, gates it, reports, and stops. `/loop /dispatch` or Droid same-session cron repeats the
same one-goal cycle. Each run must be idempotent so a re-run after a transient death picks up
where it left off:

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
   **Cross-fire brake (the per-session cap alone is not enough).** The ~3-respawn budget lives
   in this run's context, so under `/loop /dispatch` each fresh fire re-detects the same stale
   claim and restarts the budget from zero — a goal whose implementer keeps dying transiently
   before landing ANY commit would be respawned forever. Add a session-independent brake
   measured in FIRES OBSERVED, never wall-clock: count the heartbeat log's lines (Phase 4
   appends one per fire) timestamped after the claim commit's author date. Three or more
   fires since the claim with still zero work commits → block it
   `blocked: repeated transient death` instead of respawning again. Wall-clock age is NOT a
   valid proxy for attempts: an account usage-limit stop (the subscription's 5-hour or weekly
   window — see loop-architect's limit-proofing) suspends ALL fires for hours and leaves the
   same shape (old claim, zero work commits) with zero attempts actually made. An
   old-but-untried claim — fewer than 3 heartbeat lines since it — is resumed, never blocked.
   Only when no heartbeat log exists at all (e.g. pre-append plugin versions wrote a
   single overwritten line) fall back to the old age heuristic: a claim more than a few
   cadences old (e.g. > ~2h for a 15m loop) is blocked with the same
   `blocked: repeated transient death` reason. This uses only git/index data plus the runtime
   heartbeat cache (no new queue state — status-only-in-index holds), and it is what actually
   stops the cross-fire livelock without mislabeling a quota pause as a dead goal.
3. **Finish before claiming** (Phase 1 before Phase 2) so finished work always settles first.

## Phase 0 — read the queue

**Fire marker — first act of every fire.** `mkdir -p ~/.local/state/pg-dispatch/<SLUG>`
then `date -u +%FT%TZ > ~/.local/state/pg-dispatch/<SLUG>/active` (`<SLUG>` = the repo dir
name, same as the Phase 4 heartbeat). The `telegram-message` notifier gates its hook pings
on this marker's freshness: a permission/idle prompt or API error pings only while a fire
is live. Phase 4 removes it as the fire's last act; every reader treats a marker older
than 4 h as dead, so a crashed fire can't hold the gate open. A fire that legitimately
runs long rewrites the marker at each phase transition (claim, spawn, gate) so it never
ages past the window mid-fire.

Confirm the working tree is clean (dirty or diverged → stop and report rather than stash
silently). If `docs/goals/index.yaml` is missing, report "no goals queue — create goals with
/define-goal" and end the iteration.

If `config.base` is set and the current branch != `config.base`, STOP and report — you are on
the wrong working branch; checkout `<config.base>` first (mirroring the per-goal `base:`
mismatch handling in Phase 2 — never silently work on the wrong branch).

**Drained-queue terminal stop.** Dispatch stops when there is nothing left to do: when Phase 2
finds no ready goals AND needs-you is empty, emit `factory drained — <done>/<total> done` and
stop. A terminal stop still runs Phase 4 first — the drained fire reports, heartbeats, pings,
and removes the fire marker before stopping; skipping Phase 4 would leave the marker holding
the notifier's gate open for a factory that is actually done. A later `/dispatch` (or `/loop`) re-run picks up newly-added goals — a `/define-goal` +
`/dispatch` resumes from wherever the queue now stands.

At end-of-drain only (NOT per-goal — no polling), if the working branch has a remote AND `gh`
is available and authenticated, do ONE non-blocking check of the latest CI run on the current
branch (`gh run list --branch <current> --limit 1`); if it is failing, surface it under
needs-you as a non-blocking observation (a CI failure to look at — never block, never wait on
it). If `gh` or the remote is absent, skip silently (`gh` is optional).

**Latest-context preflight (read-only, never a gate).** Before spawning an implementer, gather
only the context that helps avoid stale work:
- Latest plan/progress note if present: newest `docs/superpowers/plans/*.md`, then
  `.superpowers/sdd/progress.md` if present.
- Latest PR context if `gh` is available: prefer an open PR for the current branch
  (`gh pr view --json number,title,url,reviewDecision,statusCheckRollup`); otherwise the most
  recently updated open PR (`gh pr list --state open --limit 1 --json ...`). If there is no PR
  or `gh` is unavailable, record `none`.

Summarize this in at most five bullets and pass it to the implementer under "Latest context".
PRs, plan docs, and review comments are context only. They do not create a merge gate, they do
not authorize a branch switch, and they do not override the goal contract or the local gate.

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

**Implementer-cost awareness.** When goals resolve to an expensive session model (no per-goal
`model:` fields and `config.model: inherit`) and the queue is mostly `type: chore`
(mechanical, no-behavior-change work), note once in the report that the implementers inherit
your model and that the repo owner can have define-goal stamp per-goal `model:` fields (or
set `config.model`) if they want that trade. Do not name or apply a fixed alias yourself.

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
   verification-before-completion) + config.skills + the goal's `skills:`. It uses the
   lightweight subagent-driven quality loop in Phase 3, commits its work on the branch, and
   ends with verification evidence + a `Fresh-check:` block (step 3 checks for it). It never
   merges, never opens a PR.
3. Run the LOCAL gate authoritatively yourself — review evidence first, then commands:
   **Review-evidence check.** For non-trivial work (more than a one-file mechanical edit)
   the implementer's report must carry its `Fresh-check:` block — the lens verdicts, or the
   literal `Fresh-check: not required (one-file mechanical edit)` for work that genuinely is.
   Missing block, or a not-required claim on plainly multi-file work → don't block on the
   miss, self-heal: spawn the 2–3 read-only lenses yourself over the `gate_base..HEAD` diff
   (same lenses as the brief's Quality loop step 5, fresh windows, concurrent; findings are
   hypotheses to verify, not orders). Their verified Critical/Important findings enter the
   FAIL_FIXABLE repair path like any gate finding. A skipped panel is a compliance miss: when
   the same miss recurs across goals in this session's fires (no persisted counter — session
   memory only, per the status-only-in-index rule), surface it once via Hygiene's
   lesson-encoding rule.
   **Then the gate commands:**
   `python3 "$PGVALIDATE" --head HEAD --base <gate_base> --goal <id> --goal-file docs/goals/<id>.md`
   plus the repo `config.verify` commands (ordered, all must exit 0). Show output.
4. PASS → `git reset --soft <gate_base> && git commit -m "feat(goal <id>): <slug>"` (squash to
   one), then `chore(goals): complete <id>`; push if a remote exists (non-blocking); report
   and stop without claiming another goal.
   FAIL_FIXABLE → one repair agent, re-gate; still failing → `git reset --hard <gate_base>`,
   `chore(goals): block <id> — <reason>`. FAIL_CONTRACT → reset + block (needs-you contract
   amendment). INCONCLUSIVE → reset + block "no runnable local gate: <the failing check's
   `evidence` from the JSON>" — the evidence names the exact cause and operator fix (e.g.
   the Windows symlink privilege below), so it must reach the block reason, not die in the
   gate output.

`anchor`/`gate_base` matter: the claim's `index.yaml` edit lands BEFORE `gate_base` is set,
so the validated diff (`gate_base..HEAD`) is exactly the implementer's work — never the queue
write. A `git reset --hard <gate_base>` discards only the implementer's commits; the claim
commit survives, ready to be flipped to `blocked` by the claim protocol.

The gate verdict comes from `pg_validate.py`'s JSON `verdict` field (PASS=exit 0,
FAIL_FIXABLE/FAIL_CONTRACT=exit 3 — read the JSON to split them, INCONCLUSIVE=exit 4) AND
the `config.verify` commands (any non-zero exit = the gate fails as FAIL_FIXABLE for that
command's failure). You run the gate — the implementer's verification summary is evidence,
not the verdict.

**Windows note.** `type: bug` goals prove repro-direction in a temporary base worktree whose
dep dirs (root `node_modules`/`.venv` & co plus per-workspace-package `node_modules`) are
symlinked from the live checkout. Creating those links needs the Windows symlink privilege —
Developer Mode (Settings → Privacy & security → For developers) or an elevated session;
without it the gate returns an actionable INCONCLUSIVE naming that fix (never a false PASS),
so every bug goal blocks until it's enabled (chore/feature goals never build a base
worktree and are unaffected). `factory-doctor` preflights this
(`symlink-privilege` WARN). The gate's command runner is tunable via `PG_BASH` (full path to
the POSIX shell; auto-resolution already skips the WSL launcher stub) and
`PG_VALIDATE_TIMEOUT` (seconds per acceptance command, default 1800).

## Phase 1 — finish in-flight goals

Before claiming anything new, settle every `in_progress` entry — finished work beats new work.

**Single-`in_progress` invariant (data-loss guard).** A healthy queue has at most ONE
`in_progress` entry (Phase 1 runs before Phase 2, one claim per run). If you find MORE than one
`in_progress` on the current branch, do NOT settle them one at a time: the branch is linear, so
an older goal's `gate_base` is an ancestor of a newer goal's claim + work, and a
`git reset --hard <older gate_base>` on a FAIL would rewind past the newer claim and silently
destroy its committed work. STOP, roll back nothing, and surface
`multiple in_progress claims — manual review` under needs-you. (This state only arises from a
crash between claims, a manual index edit, or a prior buggy run; resume once a human resolves
it.) When exactly one `in_progress` exists, proceed:

`gate_base` is not stored in `index.yaml`, so on a fresh session recover it from git: it is the
SHA of the goal's claim commit on the current branch,
`git log --grep="chore(goals): claim <id>" --format=%H -1` (the gate then diffs
`gate_base..HEAD`). For each `in_progress` entry, decide by whether work commits exist on the
branch after that claim commit:

1. **Work commits present after the claim commit** → recover `gate_base` as above, then run the
   gate (Working a goal, step 3) against it. PASS → squash + `chore(goals): complete <id>`.
   FAIL_FIXABLE → one repair agent, re-gate; still failing → `git reset --hard <gate_base>` +
   `chore(goals): block <id> — <reason>`. FAIL_CONTRACT → reset + block (needs-you contract
   amendment). INCONCLUSIVE → reset + block "no runnable local gate: <evidence>" (same
   evidence-in-reason rule as step 4).
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
rules) and let the current goal finish. Never claim a second goal in the same dispatch run.

## Phase 3 — spawn the implementer (depth 1, foreground)

One Agent per claimed goal, `run_in_background: false`, NO worktree — it works in THIS
checkout on the current branch. Set the spawn's `model` parameter to the goal's resolved
implementer model (Implementer-model resolution above; `inherit` = omit the parameter).
Brief (fill in `<id>` and the resolved skill lists):

```
Implement the goal in docs/goals/<id>.md exactly per its "Goal contract" section — read
that file first.

Latest context from the dispatcher:
<latest plan/progress/PR bullets, or "none">

You own this work end to end. Nested subagents are required when the runtime provides them
and the task is more than a one-file mechanical edit: use them for context isolation,
independent verification, and review in fresh windows — this is `subagent-driven-development`
(invoke the skill when it is available). Two patterns earn their keep here: adversarial
verification (a reviewer tries to REFUTE the change, not rubber-stamp it) and, for bug hunts,
loop-until-dry (keep looking until a pass turns up nothing new). They are never a second
implementer lane. If subagents are unavailable, say so and run the same checklist yourself.

Workspace: you are on the current branch in this checkout — work on the current branch in
this checkout, commit your intended files here. Do NOT create a worktree, do NOT create a
new branch, do NOT open a PR. Run project setup (install deps) and the repo's test baseline;
a dirty baseline is reported, never built on. Failures that are already red on the current
branch before you start (unrelated suites, missing-secret/env environments) are pre-existing,
not your regression: note them and move on — do not fix them, and they do not block your goal.

Quality loop — keep it lightweight, but do not skip it:
1. Plan: before editing, write a short checklist from the goal contract and latest context.
   Use `writing-plans` first if the change spans >2 files or changes architecture; otherwise
   keep the checklist inline.
2. TDD: for every code change, use `test-driven-development` and watch the proving test fail
   before implementation. Bug goals must reproduce the root cause first; upstream findings
   are hypotheses, not facts.
3. Implement on the current branch only. You may use read-only helper subagents for
   exploration and test-design; do not spawn parallel code-writing agents or agent-team
   teammates (a teammate is a second implementer lane by another name). Workflow/mission
   mode is allowed only for bounded read-only fan-out or review when there are ~5+ independent
   checks; never use it to implement across branches or survive the session.
4. Verify: run the goal acceptance commands and any repo baseline command you touched.
5. Fresh check: for non-trivial work (more than a one-file mechanical edit), review the diff
   against the goal contract in fresh read-only windows — not one generalist reviewer but a
   small panel of independent lenses
   run concurrently: (a) contract-conformance (every acceptance criterion met, nothing
   missing), (b) tests + overbuild (proving tests are real, no scope creep), (c) stray files
   + regressions (only intended files touched, baseline still green). Two or three lenses is
   the norm and stays lightweight; escalate to a read-only review Workflow only at the ~5+
   independent-checks threshold from step 3. Treat every finding as something to verify, not
   an order to obey; fix Critical/Important issues or explain why they are false. These
   verdicts go into your final report's `Fresh-check:` block (see Finish) — the orchestrator
   checks for it and runs the panel itself if it is missing.
6. Self-review the final diff, stage only intended files, commit, and report evidence.

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
their output), plus a labeled `Fresh-check:` block: the lens verdicts when Quality loop
step 5 applied, or the literal line `Fresh-check: not required (one-file mechanical edit)`
when it did not. This block is not optional — the orchestrator checks for it and runs the
review panel itself when it is missing OR when a not-required claim doesn't match the diff
(multi-file work claiming a one-file edit). Do NOT merge anything, do NOT push, do NOT open a
PR — the orchestrator runs the gate and integrates.

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

After the implementer returns, run the review-evidence check and the gate yourself
(Working a goal, steps 3–4). A `FAIL_FIXABLE` verdict spawns ONE repair agent (same brief,
same resolved implementer model, fed the gate findings — including any verified Critical/Important
findings from an orchestrator-run review panel); a second identical FAIL → roll back + block.

## Solo mode — work one named goal in this session

The default model is already one-goal-at-a-time on the current branch, so "work goal 005"
just scopes the iteration to a single id: skip Phase 2's ready-scan, claim goal 005 directly
via the protocol, and run it through Working a goal (anchor → claim → foreground implementer
→ local gate → PASS squash+complete / FAIL roll back+block). Everything else — the brief, the
gate, the rollback — is identical. `/dispatch` already stops after that one goal; solo mode
only changes which goal is selected.

## Phase 4 — report (always, exactly one line)

`[dispatch] <done>/<total> done [<bar>] · ready: <count> · blocked: <count> · current: <id or none> · last: <id PASS|FAIL|none> · needs-you: <blocked goals + human decisions, or nothing>`

Lead with **progress** (`<done>/<total>`), never `ready/total` — a bare `ready/total` reads
as "nothing done" to a human. Every number carries its label. The counts come from the index
after this iteration's mutations:
- `done` = completed · `ready` = not_started with all `depends_on` completed (claimable now) ·
  `blocked` = `blocked` status or not_started with an unmet dependency · `current` = the goal
  being worked this fire (or none) · `last` = the most recently gated goal and its verdict.
- Any residual `in_progress` entry this fire could not settle (e.g. one claimed on a different
  `base:` branch) counts into `blocked` (as blocked-pending) so that `done + ready + blocked`
  always equals `total` — the reconciliation the report line promises a human never silently
  breaks.

The bar is 20 cells: `filled = round(20 × done ÷ total)` (0.5 rounds up), clamped to [0, 20];
empty = 20 − filled. Filled cells = █, empty = ░; omit the whole bar when total = 0.
Anchor example: 19/21 → round(18.10) = 18 filled → `[██████████████████░░]`.

needs-you lists everything currently waiting on the human: every goal with explicit `blocked`
status (with the dependents stuck behind it), `GOAL_UNREACHABLE`/`FAIL_CONTRACT` contract
amendments, a `base:`-mismatched goal needing a branch switch, `budget exhausted`, and — on
Droid — `model alias unmapped, ran inherit (run /factory-doctor to map models)` whenever this
fire's Implementer-model resolution fell back because the alias had no `config.droid_models`
entry or the runtime rejected the mapped ID (informational, non-blocking: the goal still ran). A
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

**Heartbeat (liveness) — every fire.** APPEND a one-line heartbeat —
`<UTC timestamp> · <done>/<total> · current <id or none> · drained <yes|no>` — to the runtime
cache at `~/.local/state/pg-dispatch/<SLUG>/heartbeat` (`<SLUG>` = the repo dir name;
`mkdir -p` first; after appending, trim the file to its newest ~50 lines). The log serves two
readers. (1) Liveness: a silently-dead orchestrator (a 500 / context-exhaustion mid-turn)
emits nothing, so the next `/dispatch` — or an external watcher — compares the newest line's
age to the expected cadence and treats a long silence as a dead-loop signal, turning silent
death into a detectable anomaly. (2) The cross-fire brake (Re-entrancy) counts lines after a
stale claim's date to measure fires observed — which is how a usage-limit pause (no fires, so
no lines) is told apart from a goal that keeps failing across live fires. The drained flag
also feeds the drained-queue terminal stop (Phase 0). `factory-doctor`'s queue-liveness probe
reports the same staleness from the queue side (stale `in_progress` claims), and its
limit-resilience probe warns when this loop has no way to survive a usage-limit stop.

**Telegram ping (optional, hook-free) — every fire.** After the report line and
heartbeat, resolve `$PGNOTIFY` once per session with the same fallback chain as
`$PGVALIDATE` (swap the path:
`skills/telegram-message/scripts/pg_telegram_notify.py`), then pipe the report
line to it:
`printf '%s' "<the Phase 4 report line>" | python3 "$PGNOTIFY" dispatch`.
The notifier no-ops instantly unless the owner ran `/telegram-message` for this
project/machine (or set the cloud env vars), always exits 0 so it can never fail
a fire, and works identically in Claude Code, Droid, and cloud runs because it
is a plain script call, not a hook — on Droid, where hooks don't fire under
`droid exec`, this IS the notification path. Skip silently if the script can't
be resolved.

**Fire-marker cleanup — last act of every fire.** After the report, heartbeat, and ping:
`rm -f ~/.local/state/pg-dispatch/<SLUG>/active`. Between loop fires the marker must be
absent — that is what lets a dispatch-gated notifier stay quiet about the loop session's
between-fire idling while still pinging a prompt that stalls a live fire.

## Hygiene

When `completed` entries crowd the index (~20+), move their files to `docs/goals/done/`
and their entries to `docs/goals/archive.yaml` in one `chore(goals): archive` commit. The
queue commit is always its own step (see the claim protocol). Agents read the whole index
every iteration — keep it small.

**Encode recurring lessons.** When the same class of gate failure recurs across different
goals (the same lint family, the same missing verify step, the same scope-creep shape),
that is a system defect, not a string of per-goal bugs: surface ONE needs-you line
proposing where to encode it — a `config.verify` command, a `config.skills` entry, a
CLAUDE.md rule, or a contract fix via define-goal — so future implementers inherit the
rule instead of re-learning it one blocked goal at a time. Propose only; the repo owner
decides what lands.
