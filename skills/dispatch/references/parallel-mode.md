# Parallel mode — the lane model (`--parallel` / auto-parallel drains; both harnesses)

Read this file when a run carries `--parallel`, when a flagless drain auto-enters lane
mode (v11.0.0: `config.parallel` exists, ≥2 co-schedulable ready goals —
the flag and the auto-entry run the identical lifecycle below; `--serial` suppresses
auto-entry), or when Phase 1 finds lane-backed claims to settle.

Parallel mode is the merge-queue architecture localized: N goals BUILD concurrently in
isolated worktree lanes; ONE integration lock admits them onto the branch strictly one
at a time, re-gating each on the exact tree the branch is about to become. Parallelism
never touches the gate's authority — it moves wall-clock, never the bar. Everything not
restated here (claim protocol, briefs, gate arms, budgets, escalation ladder, report,
heartbeat, settle triage) is exactly the canonical per-goal sequence.

**Harness support (v12.5.0 — Droid enabled).** BOTH harnesses run lane mode. The lane
model, admission control, the integration lock and every failure ruling below are
harness-neutral; only the wave spawn call differs.

- **Claude Code**: all wave implementers go out as concurrent FOREGROUND `Agent` spawns
  in ONE message — the same proven mechanism the lens panel uses.
- **Droid**: all wave implementers go out as concurrent FOREGROUND `Task` spawns in ONE
  message — `subagent_type: worker`, `await: true`, `complexity:` from the goal's
  resolved tier. This is a live-verified Droid capability, not an emulation: the
  2026-08-31 audit of `~/.factory/task-invocations.json` (Droid 0.208.2, 1,017 recorded
  invocations) found routine 7–8-way concurrent foreground bursts, including
  write-capable `worker` spawns running 9–14 minutes apiece (2026-08-26 `aj-leads`,
  7 concurrent `worker`s; 2026-08-27 `mfa`, 8 concurrent; 2026-08-28 `flywheel`,
  8 concurrent). K on Droid obeys the same default and hard cap 4. Worktree lanes
  themselves are field-proven on Droid too: a 2026-08-17 run built 4 goals concurrently
  in real `~/.local/state/pg-dispatch/<SLUG>/lanes/<id>` worktrees off `staging` — its
  ONLY defect was launching those Tasks in the BACKGROUND and polling them, which is the
  shape banned below.

Three Droid-only lane rules follow:

- **A Droid Task subagent INHERITS the session's cwd.** Every recorded invocation's
  `cwd` equals its parent session's, and Task takes no cwd parameter. So the lane
  Workspace paragraph must name the lane as an ABSOLUTE path and the implementer must
  address it explicitly in every Execute call (`git -C <lane> …`, or `cd <lane> && …`) —
  never assume the lane is the working directory. A lane implementer that commits into
  the main checkout because it assumed cwd is exactly the two-writers-in-one-tree
  failure lanes exist to prevent.
- **A Droid subagent has no Task tool**, so an in-lane fresh-check panel uses the
  sanctioned `droid exec` path exactly as the implementer brief specifies, with
  `--cwd <lane path>` added so the lens reads the LANE's tree and not the main checkout.
- **Long in-lane commands must be detached, then waited on ONCE.** Droid's foreground
  shell has been observed killing a long-running command with its process group at
  roughly a minute (measured 2026-08-13: a `droid exec` lens produced zero output until
  it was re-run detached). An in-lane build/test run or `droid exec` lens that can
  outlive that goes `setsid <cmd> > <log> 2>&1 &`, then ONE wait, then read `<log>` —
  the Arm A join rule verbatim. One wait, never a `sleep`+`ps` or task-status poll loop.

**Lane creation blocked by trust or permission (Droid).** Lane worktrees live outside
the repo under `~/.local/state/pg-dispatch/`, which must sit inside a Droid trusted
folder. A `git worktree add` or a lane spawn that fails on a trust or permission error
is environment, not work, so it is a ONE-strike ruling (unlike the two-strike rebase
misprediction below — a trust error reproduces identically for every later lane, so a
second attempt buys nothing): discard that lane, KEEP the goal claimed and work it
SERIALLY from the current branch HEAD as a fresh implementer spawn, let any lanes
already running finish and integrate normally, open no further lanes for the rest of
the run, and surface needs-you class `environment failure` naming the path. Never a
poll emulation, and never a silent fall-back to lanes on the next wave.

**The background-poll ban stays, on BOTH harnesses.** What v12.0.0 banned on Droid was
never concurrency — it was EMULATING lanes with `runInBackground: true` Task spawns plus
a `TaskOutput` poll loop (measured 2026-08-17: a Droid run emulating 4 lanes burned 293
poll calls, 34 % of its turns, and exhausted the account balance mid-drain). A repeated
non-blocking task-status poll with no intervening work is a compliance miss on any
harness. Foreground concurrent spawns have the opposite shape by construction: K spawns
in one message, ONE wait, K results, zero polls.

**Admission control — which ready goals may share a wave.** Walk the ready list in
normal priority order; a goal joins the wave only when ALL hold against every goal
already in it:

1. No `depends_on` path between them, in either direction, transitively.
2. Disjoint `touches:` globs at the DIRECTORY level. A goal with no `touches:`
   frontmatter is not parallel-eligible — it runs in a wave of one (define-goal stamps
   `touches:` on recon-backed goals; since v10.0.0 a missing field on a recon-backed
   feature/bug goal is a contract defect at definition time, so new queues should
   rarely hit this).
3. No conflict-domain membership — any of these makes the goal exclusive (wave of one):
   it adds/removes a dependency (manifest + lockfile), touches DB migrations/schema,
   regenerates generated artifacts, or touches CI/workflow files or global config
   (env schema, tsconfig/build config).
4. Disjoint drivable surfaces: two goals whose acceptance drives a live dev
   server/port are never co-scheduled (v9.0.0 serializes them; no port juggling).
5. Same `base:` branch.

Anything uncertain → not co-scheduled. A wave of one is always legal and is just the
serial cycle. `config.budget` outranks the wave: never start more lanes than the
remaining budget allows.

**Lane lifecycle (per wave-member goal):**

1. Claim exactly as the protocol requires — K claims are K separate
   `chore(goals): claim <id>` commits on the branch, made before any lane spawns
   (claim commits are index-only and cannot conflict with lane work).
2. Create the lane:
   `git worktree add ~/.local/state/pg-dispatch/<SLUG>/lanes/<id> -b lane/<id> <branch-HEAD>`.
   `lane/<id>` is LOCAL, never pushed, deleted at settle — a disposable build
   directory, not v3's remote PR branch. If `config.parallel.setup` is set (e.g.
   `pnpm install --prefer-offline`), run it in the lane; lanes persist across fires to
   amortize setup, and factory-doctor reports orphans. A fresh worktree contains NO
   gitignored local files: if the suite needs one (a `.dev.vars`, a local env file),
   copy it from the main checkout at lane creation or add it to
   `config.parallel.setup` — a missing local secret fails as auth errors that read
   exactly like a real regression and burns a full gate cycle (measured on a real
   lane 2026-08-13: 6 failures in the lane, 7/7 green once `.dev.vars` was copied).
3. Spawn ALL wave implementers foreground in ONE message (the lens-panel concurrency
   pattern — concurrent, returning synchronously; never background-then-poll) — `Agent`
   spawns on Claude Code, `Task` spawns with `await: true` on Droid, per the Harness
   support section. Each
   brief is the canonical implementer brief (references/implementer-brief.md) with ONE
   substitution — the Workspace
   paragraph becomes: "Workspace: your lane is the worktree at the ABSOLUTE path
   `~/.local/state/pg-dispatch/<SLUG>/lanes/<id>` on local branch `lane/<id>` — work
   and commit THERE only. Do not assume it is your working directory: address it
   explicitly in every shell call (`cd <lane> && …` or `git -C <lane> …`) and confirm
   with `git -C <lane> rev-parse --abbrev-ref HEAD` before your first commit. Never
   touch the main checkout, never switch branches, do NOT
   create further worktrees or branches, do NOT push, do NOT open a PR."
4. In-lane gate, per returned implementer: Arm B reviews `<branch-HEAD>..lane/<id>`
   (read-only reviewers of DIFFERENT lanes may spawn concurrently in one message;
   Arm A background commands run inside each lane directory). Verified findings → ONE
   repair round IN the lane (warm resume first, per the escalation-and-repair
   reference); focused re-check in the lane. At most one writing agent
   per lane at any moment — reviews of lane A may overlap a repair in lane B freely.
   A goal is integration-ready when its lane gate has no open findings.
5. **Integration lock — strictly serial, one goal at a time, in wave order of
   readiness**: rebase `lane/<id>` onto the CURRENT branch HEAD (later wave members
   replay over freshly integrated work). If the rebased range carries ANY commit
   touching `docs/goals/**`, restore those paths to the branch's copy before gating
   (`git checkout <branch> -- docs/goals/` in the lane) — queue state is written
   ONLY by the orchestrator on the branch, never through a lane. Then re-run Arm A
   (pg_validate over the
   rebased range + every `config.verify` command) INSIDE the rebased lane — this
   verifies the exact tree the branch is about to become, which is where cross-goal
   interference is caught. PASS → collapse the lane to one commit IN THE LANE
   (`git reset --soft <branch-HEAD>` then commit as `feat(goal <id>): <slug>`), and
   fast-forward the working branch to the lane tip from the main checkout
   (`git merge --ff-only lane/<id>`). NEVER `git merge --squash` (v11.4.1): it
   re-merges the lane against the branch and can conflict on files the rebase
   already settled — on 2026-08-13 exactly that put conflict markers INTO a
   committed `index.yaml`; the rebase-then-ff-only path cannot conflict by
   construction. Then
   `chore(goals): complete <id>`, delete the lane and its branch, push (non-blocking),
   surface needs-independent-review criteria exactly as the canonical sequence's
   step 4. The branch moves ONLY
   by fast-forward to verified trees — strictly stronger than serial mode's
   commit-then-maybe-reset.
6. Report line + heartbeat per settled goal, exactly as Phase 4 (each settle = one
   fire for the cross-fire brake). In parallel mode `current:` lists the live lane
   ids (e.g. `current: 131+134`).
   **Idle-drain (Claude-Code-only).** The orchestrator must consume or dismiss
   pending `idle_notification` teammate-inbox messages before the closing turn
   so a leftover ping cannot open the next turn. Droid has no teammate surface
   — skip this step there. Never spawn a teammate, agent, or hook to drain one.

**Failure rulings (every scenario, decided in advance):**

- **Conflict on `docs/goals/**` at integration** — NOT a touch-set misprediction:
  implementers never write the queue, so the conflict means queue commits rode
  into the lane range. Take the BRANCH's copy of the conflicted queue paths,
  never the lane's: mid-rebase that is
  `git checkout <branch> -- docs/goals/ && git add docs/goals/ &&
  git rebase --continue` (a queue commit emptied by this resolves with
  `git rebase --skip`); after a clean rebase it is step 5's restore. Then
  continue integration. Absolute rule regardless of file: a tree with conflict markers is
  NEVER committed — any `<<<<<<<` in `git status`/`git diff` output means stop,
  restore, re-integrate; markers committed into `index.yaml` corrupt the queue
  every later fire reads.
- **Rebase conflict at integration** (goal-work files) — the touch-set prediction was wrong. Never
  resolve by guessing (the standing conflict rule). Discard the lane's commits,
  delete the lane, KEEP the goal claimed, and re-run it serially from the new branch
  HEAD as a fresh implementer spawn (worst case = today's serial cost). Surface
  needs-you class `parallel-conflict`. TWO mispredictions in one run → degrade the
  rest of the run to serial (self-throttle) and say so in the report.
- **Arm A fails on the integrated tree though the lane's own gate passed** (semantic
  interference, no textual conflict) — ONE integration-repair spawn in the rebased
  lane scoped to the failing commands' output, re-run Arm A; still failing → block
  the goal with reason `integration interference`, delete the lane, continue the
  wave (needs-you class `integration interference`). The environment brake still
  applies if the failure is infrastructure-shaped.
- **Flaky test at integration** — the step-3 flake protocol applies unchanged
  (isolated re-run once; never a repair, never a second retry).
- **A lane implementer dies transiently** (stream death, empty return) — the
  Re-entrancy transient rules apply per lane; other lanes are unaffected. A lane
  respawn continues from the lane's current state. Death needs evidence first
  (Re-entrancy's two-sample rule, v11.6.0): a spawn that has not RETURNED is never
  declared dead on one silent probe — check twice with real minutes between and
  require zero new lane commits between; a respawn onto a live lane agent is two
  writers in one lane (three false dead-calls measured in one real 2026-08-15 run).
- **CONTRACT_AMBIGUOUS / NEEDS_CONTEXT / BLOCKED / GOAL_UNREACHABLE from a lane** —
  identical routing to serial mode (escalation ladder, contract-defect classes);
  ladder re-spawns continue in the lane; a goal that blocks discards its lane.
- **Lockfile churn from parallel installs** — the brief's stray-churn rule already
  reverts it; a goal that legitimately changes dependencies never shares a wave
  (conflict domain 3).
- **Crash / usage-limit death mid-wave** — recovery is derivable with no new state:
  `git worktree list` + `lane/<id>` branch names ARE the lane ledger
  (status-only-in-index holds; nothing new is written to the queue). See Phase 1.
- **Crash between fast-forward and the `complete` flip** — Phase 1's existing
  detection: a `feat(goal <id>)` commit on the branch for an `in_progress` entry →
  flip to complete, no re-gate.
- **Token burn** — a wave spends the same tokens per goal, faster; that is the point
  of a window-timed drain. `config.budget` always outranks the wave size.
