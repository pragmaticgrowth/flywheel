# Parallel dispatch — lane model + first-pass-yield package (v9 design)

Status: DESIGN — awaiting owner approval. Nothing in this spec is implemented yet.
Author: forensics + design session 2026-08-01.

## 1. The problem, measured (2026-07-24 → 2026-08-01, 11 dispatch sessions)

Transcript forensics over every session on this machine from the last week:

| Where dispatch wall-clock goes | hours | share |
|---|---|---|
| Implementer spawns (29) | 19.8h | 42.8% |
| **Repair spawns (38)** | **18.5h** | **40.1%** |
| Gate reviews (21) | 3.9h | 8.5% |
| Lenses + re-checks + red-team | ~3.5h | ~8% |

- ~1.3 repair passes per implementation. Repairs cost as much as building.
- The whole cycle is strictly serial: implement → lenses → gate review →
  repair → re-check → next goal. Nothing overlaps across goals.
- On top of active time, sessions carry 15–20h of >1h idle gaps (overnight +
  usage-limit pauses) — calendar time, not compute.
- Reviewer token burn is already fixed: pre-v8.4.0 opus gate reviews hit
  100–255k output tokens; post-budget reviews run 10–20k. Confirmed working.
- fresh-check lenses ran 28× on opus vs 40× on sonnet for the SAME job at
  ~2× the token cost (they inherit the implementer's heavy pin).

Two deep-reads classified every repair trigger in the heaviest sessions:

- **Repair causes: ~43 REAL-BUG, ~8 CONTRACT-GAP, ~10 REVIEWER-PEDANTRY,
  ~4 TEST/ENV flakes.** The gate is not too strict — it catches real defects.
- **The dominant implementer failure mode is over-claiming**: full-confidence
  assertions with no precondition check (minting `observed_fact`/1.0 from a
  coincidental AST match; "byte-identical" proven by structural equality) and
  **vacuous proving tests** (catch-and-continue swallowing 12/16 positions; a
  permutation test whose input is sorted before the sweep; a "universal" sweep
  hand-capped at 200/442). One reviewer said it outright: "the immediately
  preceding goal shipped a Critical of exactly this shape."
- **Bundling predicts repairs.** Zero-repair batch (5 goals, ~2h, 0 repairs):
  each goal = ONE finding, narrow touches, simple verify. Repair-heavy batch:
  goals bundling 4–9 findings each (a size-L goal closing 9 DeepSec findings
  = 2 repair passes + 2 re-checks). This is the v8.3.0 ONE-SITTING rule being
  violated in practice.
- **Plumbing waste**: fresh-check panels "spawned but never returned after
  ~45 min of pings" in three goals of one session (the banned poll pattern
  resurfacing); a repair agent killed by `Stream idle timeout` forcing
  near-duplicate work; a repair pass that introduced NEW regressions and
  triggered a full duplicate implementer cycle (~4h); 3 distinct test flakes
  forcing re-gates in one session.

Conclusion: parallelism alone would speed up a factory that wastes 40% of its
time repairing. The design has two equal halves: **(A) first-pass yield** and
**(B) the parallel lane model**. A is cheaper and ships first.

## 2. What stays sacred (constraints)

1. The LOCAL gate is the only merge gate. CI stays a non-blocking observation.
2. The working branch NEVER carries unverified work. (The lane model makes
   this STRONGER than today — see 4.3.)
3. Status lives only in `index.yaml`; goal files immutable; claim protocol
   commits unchanged. No new queue state files.
4. In-subscription, in-session only: no fast mode, no `claude -p`, no cron
   (owner decision 2026-07-28). Parallelism = concurrent subagents inside one
   attended session.
5. No PRs, no remote branches, no CI gating — the v3 scar is about PR/CI
   integration machinery, and none of it returns. Worktrees return ONLY as
   disposable local build isolation with serialized local integration.
6. Serial mode remains the default and stays byte-for-byte the current
   behavior. Parallel is opt-in (`--parallel`), Claude-Code-only at first
   (Droid keeps serial until its Task semantics are live-verified).

## 3. Part A — first-pass yield package (ships first, no invariant changes)

Target: repair passes 1.3 → ≤0.6 per goal. Levers, each grounded in a
classified failure above:

**A1. Anti-overclaim rules in the implementer brief** (Quality loop step 4):
- Every full-confidence claim (an `observed_fact`-style assertion, a
  "byte-identical"/"guaranteed"/"all cases" statement in code or report) must
  name the precondition check that makes it true. No check → downgrade the
  claim or add the check.
- Every proving test that claims generic coverage gets ONE mutation probe
  before commit: change the covered behavior (reverse the tiebreak, corrupt a
  byte, reorder input) and watch the test FAIL. A sweep that cannot be made
  to fail is vacuous. This is TDD's red-green applied to the test itself.
- Ban `catch { continue }` (and equivalents) inside proving loops.

**A2. Same two checks added to the fresh-check tests-overbuild lens and the
gate-reviewer brief** as named look-fors (they already hunt vacuous tests;
name the observed shapes: swallowed errors, capped sweeps, pre-sorted inputs,
mocked-out subject).

**A3. Repair self-check before return**: the repair brief adds "diff your own
repair once against the findings list AND run the tests covering every file
you touched" — the goal-003 duplicate cycle came from a repair introducing a
new defect of the exact class it was fixing. The focused re-check keeps its
collateral scan; this catches it one spawn earlier.

**A4. Bundling enforcement moves from advisory to hard.** define-goal's
red-team Size check: a goal closing >2 independent findings/root-causes is an
unsplit chain — contract-blocking, not advisory (unless Context states why
it is atomic). Evidence: 9-findings-in-one-goal cost 2 repair passes + 2
re-checks; 1-finding goals took 0.
Practical guidance for the owner: feed audit documents through define-goal
batch mode so each finding becomes its own goal, and let `depends_on` chain
them — 5 one-sitting goals gate faster than 1 bundle, even serially.

**A5. Flake protocol in the gate**: a `config.verify` failure whose test is
unrelated to the diff is re-run once in isolation; isolated-pass → recorded
as a flake (not a FAIL, no repair spawn), second occurrence across goals →
needs-you `recurring lesson` proposing quarantine. Three flakes forced
re-gates in one session; none was a defect.

**A6. Lens delivery fix**: the observed 45-min ping-wait means lens spawns
are still sometimes backgrounded or lost. Brief change: lenses spawn
foreground in ONE message, and if any lens returns without a verdict the
implementer respawns THAT lens once as the generic type inline — never
pings, never waits a second round. Two failed deliveries → honest
`Fresh-check: not run`, which already escalates to the orchestrator panel.

**A7. Lens tier pin**: fresh-check lenses spawn on the medium tier
explicitly (`model: sonnet` / Droid `complexity: medium`) instead of
inheriting the implementer's heavy pin. Measured: identical lens job at ~2×
token cost on opus with no findings advantage. The gate-reviewer, re-checks
and red-team stay on the session model with their v8.4.0 budgets — the
budget, not the tier, is their cost control (that rule stands; lenses are
corroborating evidence, not the verdict, so the tier pin is safe there).

**A8. Stall detection**: an implementer/repair spawn is subject to the
existing transient-death rules; add to the orchestrator: a spawn that
returns nothing and whose last activity is >30 min old on re-inspection is
treated as a transient death (respawn budget applies) — the observed
`Stream idle timeout` death burned ~1h40m before its duplicate respawn.

## 4. Part B — the parallel lane model

### 4.1 Shape: parallel build, serialized verified integration

This is the merge-queue architecture (bors / GitHub merge queue / Uber
SubmitQueue), localized with no PRs and no CI: N goals build concurrently in
isolated lanes; ONE integration lock admits verified work onto the branch
strictly one goal at a time, re-verifying each on the exact tree the branch
will become. Parallelism never touches the gate's authority.

```
                    ┌─ lane 1: goal 131  implement → lens panel → review → repair ─┐
 claim K disjoint   ├─ lane 2: goal 134  implement → lens panel → review ──────────┤ integration
 ready goals   ───► ├─ lane 3: goal 136  implement → lens panel → review → repair ─┤ lock (serial):
                    └───────────────── (concurrent, isolated worktrees) ───────────┘ rebase → Arm A on
                                                                                     integrated tree →
                                                                                     squash → ff branch
```

### 4.2 Admission control — which goals may run concurrently

The scheduler co-schedules ready goals only when ALL hold:

1. No `depends_on` path between them (in either direction, transitively).
2. **Disjoint predicted touch-sets.** define-goal stamps a new frontmatter
   field `touches:` (files/dir globs, from recon — recon already knows them;
   the zero-repair goals all had narrow natural touch-sets). A goal without
   `touches:` is not parallel-eligible (runs in the serial slot). Overlap at
   the directory level → not co-scheduled.
3. **No conflict-domain membership.** Always-exclusive domains, any touch →
   the goal runs alone: dependency manifests/lockfiles beyond incidental
   churn (i.e. the goal ADDS a dependency), DB migrations/schema, generated
   artifacts, CI/workflow files, global config (.env schema, tsconfig,
   build config).
4. **Disjoint drivable surfaces** when acceptance needs a live server: two
   goals needing the same dev-server port are not co-scheduled (a repo may
   set `config.parallel.ports: [3001, 3002, …]` to lift this later; v9.0
   just serializes them).
5. Same `base:` branch.

Anything uncertain → not co-scheduled. The scheduler is allowed to run a
wave of 1. Prediction failures are caught mechanically at integration
(rebase conflict → 4.5), so a wrong `touches:` costs a serial re-run, never
corruption.

### 4.3 Lane lifecycle

Per co-scheduled goal:

1. **Claim** on the branch exactly as today (K claims = K separate
   `chore(goals): claim` commits; the claim commits are index-only and never
   conflict with lane work).
2. **Lane setup**: `git worktree add ~/.local/state/pg-dispatch/<SLUG>/lanes/<id> -b lane/<id> <branch-HEAD>`.
   `lane/<id>` is a LOCAL, never-pushed, deleted-at-settle branch — the v3
   scar was remote `goal/*` branches feeding PRs; these are disposable build
   directories, listed and reconciled via `git worktree list`, no new state
   files. Lane deps install via `config.parallel.setup` (e.g.
   `pnpm install --prefer-offline`); lanes persist across fires to amortize
   setup, and `factory-doctor` gains a lane-hygiene probe (orphan lanes,
   stale worktrees).
3. **Implement in the lane**: same brief as today with one workspace line
   changed ("you are in worktree <path> on branch lane/<id>; commit there").
   All K implementers spawn foreground in ONE message (the proven
   lens-panel concurrency pattern) — they run concurrently and return
   together. The one-writer-per-tree rule holds: exactly one writing agent
   per worktree at any moment; the main checkout has no writer during a wave.
4. **In-lane gate, per returned goal** (these overlap freely across lanes —
   read-only reviews of different lanes + at most one repair per lane can
   all run in one message): lens verdicts arrive with the implementer
   report; the orchestrator spawns gate reviewers for ALL returned lanes in
   one message (diff = `<branch-HEAD>..lane/<id>`; read-only, session model,
   v8.4.0 budgets); verified findings → ONE repair agent IN THE LANE;
   focused re-check in the lane. A goal is *integration-ready* when its
   lane passes review with no open findings.
5. **Integration lock — strictly serial, one goal at a time**: rebase
   `lane/<id>` onto current branch HEAD (first wave member: no-op; later
   members: replays over freshly integrated work). Then run **Arm A on the
   integrated lane tree** — `pg_validate.py` over the rebased range + every
   `config.verify` command inside the lane directory. This verifies the
   exact tree the branch is about to become, so cross-goal interference is
   caught at the only place it matters. PASS → squash to
   `feat(goal <id>)`, fast-forward the working branch to the lane tip,
   `chore(goals): complete <id>`, delete `lane/<id>`. The branch moves ONLY
   by fast-forward to verified states — it can never carry unverified work,
   which is strictly stronger than today's commit-then-maybe-reset.
6. **Report + heartbeat** per settled goal, exactly as today (one cycle =
   one fire for the cross-fire brake).

### 4.4 What the invariant becomes

"One goal at a time" was always about integration safety, not build
concurrency. Restated: **at most one goal INTEGRATES at a time, the branch
only ever fast-forwards to gate-verified trees, and every gate verdict is
rendered on the integrated tree.** Build-side concurrency (K ≤
`config.parallel.max_lanes`, default 2, hard cap 4) lives entirely in
disposable lanes.

### 4.5 Edge cases — every scenario judged

| Scenario | Ruling |
|---|---|
| Rebase conflict at integration (touch-set prediction wrong) | Never guess through it (existing rule). Drop the lane's commits, keep the goal claimed, re-run it SERIALLY from the new branch HEAD (fresh implementer — worst case equals today's serial cost). Report `parallel-conflict: <id>×<id>` so the owner sees mispredictions. Two mispredictions in one session → the run degrades to serial for its remainder (self-throttle). |
| Arm A fails on the integrated tree but the lane's own review passed (semantic interference, no textual conflict) | ONE integration-repair spawn in the lane (post-rebase state), re-run Arm A; still failing → block the goal with reason `integration interference`, delete the lane, continue the wave. |
| Both lanes' installs churn the lockfile | Existing brief rule already reverts stray lockfile churn; a goal that legitimately adds a dependency is conflict-domain-exclusive (4.2.3) and never in a wave. |
| Flaky test fails Arm A at integration | A5 flake protocol — isolated re-run once, not a repair. |
| Crash / usage-limit death mid-wave | Recovery is derivable with no new state: `git worktree list` names live lanes; an `in_progress` entry WITH a `lane/<id>` branch resumes at its lane's furthest checkpoint (commits in lane → gate them; no commits → respawn, transient-death budget applies). An `in_progress` entry with commits directly on the working branch is serial-mode leftovers → existing Phase 1 logic. The multiple-`in_progress` data-loss guard is retired ONLY for lane-backed claims — the guard existed because linear-branch resets destroy newer work, and lanes take resets off the branch entirely. Multiple direct-on-branch claims still stop for manual review. |
| Crash between squash/ff and the `complete` index flip | Phase 1 detects `feat(goal <id>)` on the branch for an `in_progress` entry → flip to complete, no re-gate. |
| One wave member stalls (stream-idle death) | The foreground join waits on all members — this is the wave model's real cost. Mitigations: A8 stall detection on rejoin; `--parallel` only in batch/drain runs where the operator is nearby; K small (2–3). If the harness's background-agent + task-notification mode is available (this-machine sessions have it), the orchestrator MAY use background implementer spawns joined by notifications instead of the barrier — integration then starts on the first finisher (better pipelining); the skill text gates this on the harness actually delivering notifications, never polling. |
| Token burn rate | Parallelism spends the same tokens per goal, faster — which is the point of a window-timed drain (fill the quota window with finished goals). `config.budget` still outranks everything; when remaining budget < live lanes, no new lane starts. Waves also share nothing contextually, so there is no cache penalty vs serial. |
| Orchestrator context growth (K goals' reports resident) | Reports stay in files (existing design); the per-goal ≤15-line STATUS keeps K=3 waves ~45 lines — fine. |
| Droid | Serial only in v9.0. Droid subagents can't nest (implementer panels already use `droid exec`), Task-tool concurrency and worktree translation are unverified — parallel mode activates per-harness only after live verification, same doctrine as v7.0.0. |
| `/dispatch <id>` solo, flagless `/dispatch` | Unchanged serial path, zero behavior change. |

### 4.6 Scheduling degenerate cases

- Queue has ready goals but none co-schedulable → wave of 1 (= today).
- `--parallel` without `--count/--unlimited` → applies to the run's claims
  (a flagless parallel run claims up to K goals, settles all, stops).
- Priority: high-priority goals fill lanes first; a high-priority goal that
  is conflict-domain-exclusive runs alone BEFORE lower-priority waves (strict
  priority order is preserved at claim time, as today).

## 5. Expected effect (honest estimates from the measured data)

- Part A (yield): repairs 1.3 → ~0.6/goal ⇒ ~25–30% less wall-clock AND
  tokens per goal. Applies to serial and parallel alike, and to Droid.
- Part B (lanes, K=2–3 on disjoint queues): implementation and review
  wall-clock overlap across goals; integration (Arm A ~3–8 min/goal) is the
  only serial section ⇒ ~2–2.5× goals per active hour during drains.
- Combined during a window-timed `--unlimited --parallel` drain: **~3× goals
  per usage window**, tokens per goal roughly flat (slightly better: fewer
  repairs, minus a small scheduler/lane-setup overhead).
- Not addressed by design (calendar reality): overnight/limit idle gaps —
  that remains loop-architect's window-timed attended drains.

## 6. Rollout

1. **v9.0.0-A (first)**: Part A brief/lens/red-team edits + A7 lens tier pin
   + A5 flake protocol + `touches:` stamping in define-goal. Skill-edit
   dry-runs + RED baselines per repo rules (especially A1/A4: show the
   pre-change text lets the over-claim/bundling scenarios through).
2. **v9.1.0-B**: `--parallel` lane model on Claude Code, default OFF,
   `config.parallel.max_lanes` default 2. New needs-you classes:
   `parallel-conflict`, `integration interference`. factory-doctor lane
   probe. Docs/site/README + CHANGELOG in the same change.
3. Droid parallel: only after live verification of concurrent Task spawns +
   worktree behavior under Droid (separate spec addendum with evidence).

## Appendix: evidence trail

- Aggregation script + per-session numbers: session scratchpad
  `analyze_sessions.py` / `sessions_summary.json` (2026-08-01 session).
- Repair classifications: two Sonnet deep-reads over sessions 231c758e +
  0fe9919e (ideation) and 0d979419 + 483e8171 (nonresidenttax), 2026-08-01.
- Reviewer-budget confirmation: pre/post v8.4.0 gate-review token counts
  (100–255k → 10–20k out per review).
