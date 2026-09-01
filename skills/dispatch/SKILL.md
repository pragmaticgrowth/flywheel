---
name: dispatch
description: Factory dispatcher — use when the user says "/dispatch" (optionally with a goal id, --count N, --unlimited, --parallel, or --serial), "run the factory", wants the docs/goals queue worked, or wants to work one specific queued goal in this session ("work goal 005", "/dispatch 005"). Works in any repo with a docs/goals/ queue. Works ready goals on the currently checked-out branch and by default DRAINS the queue (keeps working ready goals until empty; --count N limits the run, a goal id scopes it to one); parallel lane mode builds provably-disjoint goals concurrently in local worktree lanes while still integrating them strictly ONE at a time behind the same local gate — entered via --parallel, or automatically on a flagless drain when the queue's config.parallel block exists (--serial forces one-at-a-time) — no pull requests, no remote branches, never two writers in one tree. Orchestrates only — never implements in its own context; the phase procedure lives in the skill body, never in this description.
argument-hint: "[goal-id] [--count N | --unlimited] [--parallel [K] | --serial]"
---

# Dispatch — the factory orchestrator

You are depth 0: a thin orchestrator. Your context stays small; the implementer (depth 1)
and its nested helpers hold the mess. Compose existing skills — never re-derive what a
skill already encodes. The queue is `docs/goals/index.yaml` (see `define-goal` for the
format).

Dispatch works ready goals **on the currently checked-out branch**. Integration is
serial, one goal AT A TIME — and the flagless default is a DRAIN: keep working ready
goals, one fully-settled cycle after another, until the queue is empty or a stop
condition fires (`--count N` limits the run; lane mode, on both harnesses, builds
provably-disjoint goals concurrently in local worktree lanes — references/parallel-mode.md).
Per goal: claim it, spawn a single foreground implementer that commits its work (on this
branch in serial mode; in its lane in parallel mode), run a LOCAL gate yourself, and on
PASS keep one squashed commit — on FAIL roll the goal back so the branch never carries
unverified work. No pull requests, no remote or `goal/<id>` branches, no agent-team
teammates, and NEVER two writers in one working tree.
**The invariant, stated precisely: at most one goal INTEGRATES at a time, the branch only
ever advances to gate-verified trees, and every gate verdict is rendered on the tree the
branch is about to become.** The v3 PR/CI/remote integration machinery livelocked on real
autonomous runs and none of it returns (CHANGELOG 4.0.0): parallel lanes are disposable
local build directories behind the same local gate, serialized at integration, deleted at
settle. Cross-goal parallelism outside the Parallel-mode rules — parallel writes to one
tree, PRs, remote branches, background implementers you poll — stays banned.

## Invocation — `/dispatch [<goal-id>] [--count N | --unlimited] [--parallel [K] | --serial]`

| Invocation | Behavior |
|---|---|
| `/dispatch` | **Drain (the default):** keep working ready goals until the queue drains or a stop condition fires. **Auto-parallel:** when the queue's `config.parallel` block exists (the repo owner's standing opt-in) and ≥2 ready goals are co-schedulable under the admission rules, the drain runs them as `--parallel` waves (K = `config.parallel.max_lanes`, else 2) on either harness; otherwise it works sequentially. `--serial` forces sequential for this run; `config.parallel.auto: false` is the persistent opt-out (keeps the block's tuning for explicit `--parallel` runs only). |
| `/dispatch 087` (also `87`, `087-slug`, or "work goal 087") | Solo mode: work exactly that goal (see Solo mode below). |
| `/dispatch --count N` | Work up to N ready goals, then stop (N ≥ 1). `--count 1` is a deliberate single-goal fire. |
| `/dispatch --unlimited` | Explicit alias of the flagless drain default. |
| `/dispatch --parallel [K]` (combinable with `--count`) | Lane concurrency: build up to K provably-disjoint goals at once in local worktree lanes (default K = `config.parallel.max_lanes`, else 2; hard cap 4), integrating strictly one at a time. Supported on BOTH harnesses — Claude Code spawns the wave as concurrent foreground `Agent` calls, Droid as concurrent foreground `Task` calls (`worker`, `await: true`) in ONE message. What stays banned on every harness is emulating lanes with background workers you poll — a repeated task-status poll with no intervening work is a compliance miss. Read references/parallel-mode.md before claiming a wave. |

Argument rules: a goal id combined with `--count`/`--unlimited`/`--parallel`/`--serial`
→ the id wins; note the ignored flag in the report. `--count` without a valid N ≥ 1, or
an unknown flag → report the usage line above and run the drain default. `--parallel`
without `--count` waves through the drain default; `--serial` disables auto-parallel for
the run (and beats `--parallel` if both are given — note it). The count meters CLAIMS —
lanes change where work builds, never how much is claimed.

**A drain repeats the same settled cycle — it changes nothing about safety.** The
invariant was never "one goal per run"; it is one goal AT A TIME, on one branch, behind
the local gate. Phase 0 and Phase 1 run ONCE at run start (finished work still beats new
work), then per goal the full cycle — Phase 2 claim → Phase 3 implement → the local gate
(Working a goal, steps 3–4) → settle (complete or blocked, branch clean) → Phase 4
report line + heartbeat append — before the next claim. The single-`in_progress`
invariant holds continuously; each per-goal cycle counts as one fire for the heartbeat
and the cross-fire brake. A goal that settles `blocked` does NOT stop the run — the next
ready goal is claimed. The end-of-drain CI observation stays end-of-run, never per-goal.

**The count counts CLAIMS — Phase 1 settles are free, and a spent count claims nothing.**
`--count N` budgets the number of Phase-2 claims this run may make: each claim consumes
one unit BEFORE the implementer spawns, and settling a pre-existing `in_progress` goal
in Phase 1 neither consumes a unit nor licenses an extra claim. When the count is spent,
the run reports and stops even if ready goals remain — the settle is free, the NEXT
claim is what the count meters.

**Stop conditions — first one wins (the ONLY legal reasons a run stops with ready goals
left):**

1. Count reached (`--count N`) — measured in claims.
2. No ready goals left (the drained-queue terminal stop, Phase 0).
3. `config.budget.max_goals_per_session` exhausted — the budget ALWAYS outranks the
   flag (effective cap = min(flag, budget)); it is the external brake precisely because
   this session cannot edit it.
4. **Environment brake:** two CONSECUTIVE goals fail with the same
   infrastructure-shaped cause — the same `config.verify` command failing identically
   in a way the two goals' diffs cannot explain, or two INCONCLUSIVE gate verdicts →
   stop the batch and surface needs-you class `environment brake`. The first goal
   still gets its normal repair attempt; when the SECOND goal's gate failure matches
   the first's infrastructure signature, skip its repair spawn and fire the brake — a
   repair agent cannot fix the environment.

The drain is the default because window-timed drains are the factory's primary
throughput pattern (loop-architect's limit-proofing): start `/dispatch` right after a
usage-limit reset so the run front-loads work into the fresh quota. An in-session drain
still dies silently at a subscription usage limit with no hook fired — the per-goal
heartbeat makes that death detectable and Phase 1 makes the next window's recovery
clean, but nothing restarts a session from inside it; the next drain is a human (or the
next attended session) starting one, never a headless scheduler (owner decision
2026-07-28: no `claude -p` fires).

Read the queue's `config:` block first; defaults when absent:
`base` = the branch dispatch works ON (default = the currently checked-out branch),
`model: inherit` (heavy|medium|light — the repo-wide DEFAULT execution tier for
implementer/fix agents; a goal file's own frontmatter `model:` overrides it per goal),
`skills: []` (repo-wide skill mandates), `verify: []` (the ordered LOCAL gate — a list
of shell commands run top-to-bottom, all must exit 0; empty = auto-detect a single test
command, and if none is found the gate is INCONCLUSIVE, never a silent PASS), `budget`
(default none; `max_goals_per_session` + optional `max_iterations` = the external
burnstop).

**Implementer-tier resolution — per goal, before each spawn.** Resolve the execution
tier for a goal's code-writing agents in this order: the goal file's frontmatter
`model:` (`inherit | heavy | medium | light`), else `config.model`, else `inherit`.

**Execution tiers (canonical alias table).** Legacy values are read as aliases forever —
`opus` → heavy, `sonnet` → medium, `haiku` → light — and never written into new goals or
claims. Spawn-time mapping per harness:

- **Claude Code**: heavy → `model: opus`, medium → `model: sonnet`, and
  light → `model: haiku` on the code-writing agent spawn; `inherit` omits the pin.
- **Droid**: pass `complexity: heavy|medium|light` on the Task spawn; `inherit` omits
  it. Implementers always spawn as the `worker` type regardless of tier.

**Pin-failure fallback.** A spawn (or mid-goal death) whose error names the MODEL,
PROVIDER, or the ACCOUNT'S ACCESS to them rather than the work — `unknown provider for
model …`, `model not found`, a 4xx quoting the pinned id, `insufficient balance` /
`billing_error`, `auth_unavailable`, "provider is currently overloaded", a 403/429/503
from the model endpoint — is infrastructure, NOT a transient work death: retry ONCE with
the pin omitted (the agent inherits the session model), note
`tier-fallback: <id> <tier> → session` in the fire's report, and continue. When the
UNPINNED retry fails with the same infrastructure class, the environment itself is
down — settle CLEANLY instead of hanging: block only the in-flight goal
(`environment: model endpoint unavailable — <error>`, needs-you class
`environment failure`), run Phase 4, release the checkout lock, and stop. Never burn the
~3 transient respawns on an error that reproduces identically by construction, and never
substitute a LIGHTER pin — inherit-the-session-model is the only fallback. A death whose
error names NONE of those classes — `Child session timed out due to inactivity` above
all — is not pin failure: it is a Re-entrancy transient (the transient-vs-work-failure
classification is Re-entrancy rule 2's to make), respawned ONCE at the SAME tier, and
the pin stays on unless the error text also names the model or provider.

A non-`inherit` tier applies to EVERY code-writing agent you spawn for THAT goal — the
implementer and any fix/repair agent alike; `inherit` means omit the mapping. This split
keeps judgment on strong models: the orchestrator stays on the session model for
claim/gate/review calls, features and bugs default to a `heavy` stamp (define-goal's
rubric), and only rote mechanical goals run lighter implementers. Neither field is yours
to override, and neither ever applies to read-only review agents — those always inherit
the session model.

**Named review agents (plugin-shipped).** The plugin ships three read-only agent
definitions for the factory's review roles: gate-reviewer (the gate's independent
second view, also used for focused re-checks), fresh-check (one lens of the gate's
escalated review panel), and contract-red-team (define-goal's draft review). Spawn them
as `flywheel:gate-reviewer` etc. on Claude Code, bare `gate-reviewer` etc. on Droid
(Droid auto-translates plugin agents and registers them unprefixed). Each definition
carries the role brief, the output contract, and a tool allowlist with no write-capable
tools — read-only enforced by the runtime, not by prompt discipline — so a spawn prompt
carries only the per-goal specifics (repo/branch, diff range, goal file, checklist,
evidence to challenge). None pins a `model:`; never pass a review agent a model or
complexity parameter — verdict-rendering roles inherit the session model, and review
cost is controlled by the BUDGET in each role's brief (an unbudgeted "refute this" brief
has no natural stopping point and has measured ~8× the cost for the same findings; the
budget supplies the stopping point at every tier). Fallback is mandatory, never a stop:
when the runtime doesn't list the type (plugin agents disabled, older CLI, a failed
spawn naming the type), spawn the generic read-capable type (`general-purpose` on
Claude Code, `worker` on Droid) and state the role inline. Never use the built-in
Explore type (Claude Code) or `explorer` (Droid) for any review role — search agents;
`explorer` cannot run commands.
**Droid spawns are awaited:** every dispatch spawn on Droid passes `await: true` on the
Task call — a spawn without it runs in the background and its verdict can land AFTER
the gate has ruled. Awaited does NOT mean one-at-a-time: K awaited `Task` calls issued
in ONE message run CONCURRENTLY and return together — exactly how a wave and a review
panel spawn on Droid.

## Hard rules (every iteration, before any action)

- One goal INTEGRATES at a time, in this session, on the current branch. Serial mode
  (the default): the next claim waits for the current goal to fully settle, work commits
  land directly on the branch, and there are NO worktrees. Parallel mode: up to K
  co-schedulable goals build concurrently in local lanes per references/parallel-mode.md —
  but integration stays strictly serial and the branch only ever advances to
  gate-verified trees. In BOTH modes: no pull requests, no remote or `goal/<id>`
  branches, never two writers in one tree. A failed gate rolls the goal back (serial:
  `git reset --hard <gate_base>`; parallel: the lane is discarded) so the branch never
  carries unverified work. Implementers never merge.
- Read the repo's CLAUDE.md hard rules once per session and treat them as law. Repeat-
  check before any git/deploy action.
- **Every queue write goes through the claim protocol below.** Implementers never touch
  `docs/goals/` — the orchestrator owns queue state.
- No-progress rule: same goal fails the same way twice with no progress → stop retrying,
  set the goal `blocked` with a `reason`, report, and claim the next ready goal.
  (Orchestrator-level — distinct from the implementer's own ~3-honest-attempts rule.)
- **The cycle is never a confirmation point.** Claiming, spawning, repairing,
  re-gating, squashing, completing, blocking, and the (pre-authorized) push are this
  skill's own specified steps — execute them without asking. "Want me to run the
  repair?" is a compliance miss, not politeness. The ONLY legal interactive ask is the
  Attended-only rule below; anything else a human must know goes to needs-you or the
  settle-triage inbox, and the run continues. **Declarative stalls are the same miss:**
  a statement that ends forward motion on a step already licensed ("it needs your
  word", "say the word and I'll…") is an invented permission-ask wearing a period, and
  a run never ends on an offer — an action that is genuinely the owner's is emitted as
  a needs-you item WITH a recommendation, never as a question or an offer, including
  in the closing turn.
- **Spawning and waiting — yield the turn, never build a wait.** On Claude Code a
  helper's report reaches you only at a TURN BOUNDARY: the `Agent` call returns
  "launched" immediately, and the report arrives later as a completion notification. So
  after spawning, do the independent work already in hand (read the goal file, its plan,
  the diff) and otherwise let the turn END. Building a wait is the miss, and it is
  self-defeating: a `Monitor` sleep loop, a blocking `TaskOutput` on that sleep task,
  or repeated `ListAgents` all hold the turn OPEN, which starves the very delivery
  being waited on. And NEVER pass `name:` on ANY factory spawn (this is the canonical
  statement — every other file cross-references it): a named agent becomes a persistent
  session teammate whose report goes to a mailbox instead of the notification channel,
  where it can sit unread while the orchestrator wastes the wait or re-does the work.
  Droid is unchanged: awaited `Task` calls return together — K spawns, ONE wait, zero
  polls.
  **When may you stop waiting?** Only on the Death-needs-evidence test in Re-entrancy
  below, which governs EVERY spawn this skill makes: a returned spawn or a terminal
  notification, else two checks with real minutes between them showing zero new records
  in the helper's own transcript and zero new commits. Six silent minutes is not that
  test; neither is impatience.
- Substantive conflicts are never guessed through. A local `git merge`/squash conflict
  on the current branch means two pieces of work changed the same logic → set the goal
  `blocked`, surface needs-you class `conflict`, roll back; never resolve by guessing.
- **Session budget (external brake).** If `config.budget.max_goals_per_session` (or
  `max_iterations`) is set, count each claimed goal against it and NEVER claim past the
  cap. Let any in-flight goal finish its gate cleanly, surface
  `budget exhausted (<n>/<cap> goals)` under needs-you, and send ONE notification per
  Phase 4 via the PushNotification tool.

**Attended-only interactive questions.** Dispatch may ask the human a question
directly — instead of writing the item into needs-you — when and only when ALL THREE
hold: (1) the user invoked `/dispatch` conversationally in this session (a turn visible
in this conversation, not scheduled or piped), AND (2) the run is single-goal-scoped —
solo mode or `--count 1`, AND (3) the run is not `/loop`, `claude -p`, or `droid exec`.
A drain or multi-goal run NEVER asks, whatever the other conditions say (a flag is a
user's word about the run, not evidence about who is watching it). When any one of the
three is unknown or
unverifiable, do NOT ask — write the needs-you item and move on (an interactive
question in an unattended fire hangs the loop or gets auto-answered, strictly worse
than a needs-you line read later; no TTY sniffing or env probing — judge from evidence
already in hand). When you do ask: ONE round, at most 2 questions, concrete options
with a recommended default; an unanswered question falls back to the needs-you item.

## needs-you — the canonical format (every human decision names its command)

needs-you is the factory's only channel to a human, and a diagnosis is not an answer.
Every needs-you item is emitted in ONE shape, defined here and nowhere else — emission
sites name their CLASS and this table supplies the command, so a new class is one new
row, never a new phrasing:

`<id or item> — <reason> → <what to run>`

`<id or item>` is the goal id (or the item name for a queue-wide condition), `<reason>`
is a faithful condensation of the block reason **capped at ~120 characters** — the FULL
reason lives in `index.yaml` and the report file, and the two must agree in substance —
and `<what to run>` is the resolving command from the table, with `<id>` and `<base>`
substituted. Command unclear for a class not in the table? Emit the item with the
closest table command and say what is uncertain — never drop the `→` half.

| class | trigger | what to run |
|---|---|---|
| `contract defect` | reason `contract defect: <detail>` — a criterion ambiguous (CONTRACT_AMBIGUOUS) or unreachable (GOAL_UNREACHABLE), a verified contract-mandated finding (FAIL_CONTRACT), the escalation ladder's too-large/wrong rung, or a `NEEDS_CONTEXT` ask nothing in-run could answer | `/define-goal --amend <id>` |
| `no runnable local gate` | reason `no runnable local gate: <evidence>` (INCONCLUSIVE gate) | `/factory-doctor` |
| `environment brake` | two consecutive infrastructure-shaped gate failures stopped a batch | `/factory-doctor` |
| `environment failure` | tooling, queue, or `config.verify` failure this fire could not handle | `/factory-doctor` |
| `repeated transient death` | ≥3 fires observed since the claim, zero work commits | `/dispatch <id>` once the cause is gone |
| `budget exhausted` | `budget exhausted (<n>/<cap> goals)` | raise or remove `config.budget.max_goals_per_session` in `docs/goals/index.yaml`, then `/dispatch` |
| `base: mismatch` | a goal entry whose `base:` mismatches the started branch | `git checkout <base>` then `/dispatch <id>` |
| `multiple in_progress` | `multiple in_progress claims — manual review` | manual review: pick the entry to keep, fix `index.yaml` by hand, then `/dispatch` |
| `checkout busy` | a dispatch lock fresher than ~2h exists at run start (Phase 0) | wait for that run; or, if you know it is dead, delete `~/.local/state/pg-dispatch/<SLUG>/lock` and re-run `/dispatch` |
| `conflict` | a local squash/merge conflict — two pieces of work changed the same logic | resolve the overlap by hand, or `/define-goal --amend <id>` to re-scope, then `/dispatch <id>` |
| `parallel-conflict` | a lane's rebase conflicted at integration — mispredicted touch-set (goal auto-requeued for a serial re-run) | fix the mispredicted `touches:` via `/define-goal --amend <id>` if it recurs; the re-run itself needs nothing |
| `integration interference` | a lane's gate passed alone but Arm A failed on the integrated tree, and one integration-repair didn't fix it | `/dispatch <id>` serially once the interfering pair is understood, or `/define-goal --amend <id>` to re-scope |
| `unmet dependency` | a named goal whose `depends_on` are not all `completed` | `/dispatch <blocking-id>` first (to change the chain, edit `depends_on` in `index.yaml` by hand) |
| `CI failure` | the branch's latest CI run is red (a non-blocking observation) | `gh run view --log-failed` |
| `recurring lesson` | the same gate-failure class recurring across goals | the proposed encoding site — a `config.verify` command, a `config.skills` entry, a CLAUDE.md rule, or `/define-goal --amend <id>` on a goal already `blocked` by it |
| `needs independent review` | a PASSed goal whose acceptance criteria carry the **needs independent review** marker (a non-blocking observation) | the command or surface from the implementer's report evidence, plus what to look for there (Working a goal, step 4) |

The `contract defect` class keeps its specific detail in the `<reason>` half — the one
row covers every contract-defect shape, and the reason string tells them apart.

**The class set is open and NOT all classes are blocking.** `CI failure` rides this
format as a pure observation, and a class may fire on a PASS. Adding a class = adding
ONE row here — never a second line shape, and never a parallel format section elsewhere.
A class whose "what to run" is prose rather than a fixed command still fills the `→`
half with that prose.

**Two channels, one shape: `needs-you:` is decisions, `fyi:` is observations.** An item
renders under `needs-you:` ONLY when a human decision or human-only action is what
unblocks it — an owner fork (spend, data loss, irreversible or externally visible), or
an item the self-heal pass already tried and could not clear. Pure observations —
`CI failure` (pre-existing red), `recurring lesson`, `needs independent review` on a
PASSed goal, a goal this run retired — render as `fyi:` bullets after the needs-you
items, same line shape, never counted as waiting on the human.

## Self-heal — the run fixes its own blockers before naming a human

Most contract-defect blocks need ~10 minutes of factory work and zero owner input, so
in EVERY dispatch run (the invocation is the standing approval — the same waiver
precedent process-inbox drains use):

1. **A contract-defect settle routes through define-goal's amend machinery IN-RUN,
   not to a human.** When a goal settles (or already sits) `blocked` with a
   `contract defect: …` reason — FAIL_CONTRACT, GOAL_UNREACHABLE, CONTRACT_AMBIGUOUS,
   the escalation ladder's too-large/wrong rung, `needs context` nothing in-run could
   answer — invoke define-goal's amend mode under its **drain waiver**: the red-team
   review runs UNCHANGED, question rounds never happen (take the clearly recommended
   or conservative reading and record it in the amendment note), and the owner
   confirmation is waived. Requeue and re-claim it once (the re-claim consumes a count
   unit like any claim).
2. **A disproven premise RETIRES the goal — there is nothing to amend.** When the
   evidence in hand shows the goal's premise is false or its outcome already true,
   flip the entry to `status: retired` with `reason: retired: <premise disproven |
   already true> — <one-line evidence>`, move the entry to `archive.yaml` and the goal
   file to `docs/goals/done/` in the same `chore(goals): retire <id>` commit. When the
   settle evidence already proves it, retire DIRECTLY — no intermediate block commit.
   Retired is TERMINAL: never requeues, never re-reports, surfaces once as `fyi:` in
   the run that retired it.
3. **Bounds.** ONE amend-and-re-claim per goal per RUN — a goal that blocks on a
   contract defect AGAIN in the same run stays `blocked` and goes to needs-you as
   genuinely stuck. A true owner fork inside the amend — spend, data loss,
   irreversible or externally visible — is never resolved under the waiver: the goal
   stays `blocked` and the needs-you item carries the fork AND your recommendation.
4. **The blocked backlog heals too.** After Phase 1 and before Phase 2's first claim,
   walk every EXISTING `blocked` entry: reasons in the contract-defect family route
   through 1–2 above — under the SAME once-per-goal-per-run cap; `environment`-class,
   `repeated transient death`, and owner-fork reasons stay blocked.

The needs-you table's `contract defect` row names what the RUN does first; a human sees
it only when self-heal already tried and failed. Nothing here touches the gate: amended
goals re-enter the full claim → implement → gate cycle, and the red-team still reviews
every amendment.

## Claim protocol — every status write

The index is the claim ledger. A claim is a status flip committed BEFORE implementing:

1. Read `docs/goals/index.yaml` from the working tree (must be clean — dirty → stop
   and report).
2. Flip exactly one entry to `in_progress` and `git commit -m "chore(goals): claim <id>"`
   (queue commits are always their own commit, never fused with code — sole sanctioned
   exception: the plan-mirror edit rides `chore(goals): complete <id>`). The same entry
   edit stamps `claimed_at:` — see Timestamps below.
3. Mid-run, push is OPTIONAL (backup only) and never gated — but the TERMINAL stop runs
   the Ship step (Phase 0). Sequential mode is single-session; two dispatch sessions on
   one local queue race on index.yaml — Phase 0's checkout lock stops the second run.

Every status transition uses the same convention — one entry, its own commit:
`chore(goals): claim|complete|block|archive|retire <id>`. These five are dispatch's
closed verb set; the one status write dispatch does NOT own is define-goal's
`chore(goals): amend <id>`, which requeues a `blocked` goal after repairing its contract.

**Timestamps — the same entry edit, no extra commit.** The claim flip writes
`claimed_at: <UTC ISO-8601, second precision>` on the entry; every terminal flip —
`complete`, `block`, `retire` — writes `settled_at:` the same way. READ THE CLOCK,
NEVER TYPE THE TIME: the value is the verbatim stdout of `date -u +%Y-%m-%dT%H:%M:%SZ`,
run in the same action that performs the flip — a recalled, inferred, or whole-minute
value is fabricated data (a field audit found 43% of composed stamps wrong; the repos
that ran the command matched git). Rules: dispatch is the only writer; a re-claim
OVERWRITES `claimed_at` and DELETES any stale `settled_at` — each sitting starts its own
clock; in parallel mode `claimed_at` is the lane claim and `settled_at` is integration
settle. These fields are metadata, NEVER control flow: no claim, brake, or gate decision
branches on them — the stale-claim brake counts heartbeat fires, not wall-clock, which
is what survives a usage-limit pause. Missing fields on pre-existing entries are normal,
but a flip THIS run performs always carries its stamp; a missing or malformed field
falls back to the claim/settle commit author dates (git is the recovery path). Archive
moves carry the fields verbatim.

## Re-entrancy — idempotent iterations

Each run must be idempotent so a re-run after a transient death picks up where it left
off:

1. **The index is the claim ledger.** A claim is a committed status flip made BEFORE
   the implementer runs.
2. **Stale claim**: an `in_progress` entry with no work commits since its claim and no
   active agent means a prior implementer died — re-run it (re-spawn from its
   `gate_base`, the current HEAD since no work landed). If the implementer's final
   report named a blocker, set `blocked` with that reason. `GOAL_UNREACHABLE` and
   `CONTRACT_AMBIGUOUS` declarations are contract defects, not work failures: block
   with reason `contract defect: <criterion> unreachable|ambiguous` — never respawn
   (a re-run hits the same wall); the Self-heal pass amends or retires in-run.
   Otherwise distinguish a TRANSIENT infrastructure death — connection closed
   mid-response, parse error, 529 overloaded, a stream-idle timeout, a spawn whose
   tool result comes back empty or as a raw API error, and `Child session timed out
   due to inactivity` above all (NOT a work failure and not a fail toward the
   no-progress rule) — from a logic blocker; the same recognition applies MID-FIRE to
   a spawn that dies under you: respawn it ONCE at the SAME tier under the same
   ~3-attempt budget (the pin comes off only when the error text also names the model
   or provider — never for this timeout alone; Pin-failure fallback). A repeat of the
   same timeout on the respawned
   sitting is not a second free respawn — it re-enters these stale-claim rules, and
   the rule is death-mode generic: ANY second STATUS-less transient death re-enters
   these rules the same way — the resume-from-increments rung while the
   transient-respawn budget has headroom (the re-brief is changed by the larger
   `Landed so far` set), `blocked: repeated transient death` only once it is spent.
   When the dead sitting
   left work commits (`gate_base..HEAD` non-empty), the respawn IS the
   resume-from-increments rung (`$DISPATCH_REFS/escalation-and-repair.md`): read
   `gate_base..HEAD`, re-brief ONE fresh worker with what already landed — never a
   from-scratch respawn.
   **Death needs evidence — a terminal signal or two samples.** An agent is dead when
   its spawn RETURNED (a tool result ended the call) or its completion notification
   says so. Absent that, silence is not death: before respawning over an agent that
   has not returned, check twice with real minutes between and require ZERO new
   commits or file activity between the checks — a respawn onto a live agent puts two
   writers in one tree.
   **A silent helper is not a dead one — read its transcript.** The helper writes its
   own transcript to disk while it runs (Claude Code
   `~/.claude/projects/<cwd-slug>/<session-id>/subagents/agent-*.jsonl`; Droid
   `~/.factory/sessions/<cwd-slug>/<childSessionId>.jsonl`, child ids in
   `~/.factory/task-invocations.json`). Records seconds or minutes old, or a file
   ending mid-tool-call, mean a LIVE agent — keep waiting. Killing a live helper and
   re-running its work in your own context is a compliance miss twice over — it
   destroys the independence the spawn exists to buy, and it pays for the work twice.
   A transient death is not a "fail" toward the no-progress rule; retry up to ~3
   transient respawns per goal per session, after which a goal that still can't make
   any commit progress blocks as `repeated transient death`.
   **Cross-fire brake.** The ~3-respawn budget lives in this run's context, so under
   `/loop /dispatch` each fire would restart it. Count the heartbeat log's lines
   (Phase 4 appends one per fire) timestamped after the claim commit's author date:
   three or more fires since the claim with still zero work commits → block it
   `blocked: repeated transient death`. Wall-clock age is NOT a valid proxy for
   attempts: a usage-limit pause suspends all fires and leaves the same shape with
   zero attempts made — an old-but-untried claim (fewer than 3 heartbeat lines since
   it) is resumed, never blocked. Only when no heartbeat log exists fall back to the
   age heuristic (a claim more than a few cadences old is blocked with the same
   reason).
3. **Finish before claiming** (Phase 1 before Phase 2) so finished work settles first.

## Phase 0 — read the queue

**Checkout lock — one dispatch per checkout.** Before anything else, check
`~/.local/state/pg-dispatch/<SLUG>/lock` (`<SLUG>` = the repo dir name, as in Phase 4).
A lock fresher than ~2 hours means another dispatch run owns this checkout: STOP
without claiming and surface needs-you class `checkout busy` — never work alongside it.
Stale or absent → write the lock, one line — `<UTC timestamp> · <branch> · <one-word
session note>` — re-write it at each per-goal cycle's claim AND settle (the settle
re-write rides the Phase 4 heartbeat append), and DELETE it at every terminal stop. A
crash leaves a lock behind; the ~2h staleness window absorbs that, and the needs-you
row names the manual override. Advisory by design: the claim protocol guards the
QUEUE — the lock guards the TREE, which the commit ledger cannot see.

Confirm the working tree is clean. **A dirty tree is handled, not a refusal.** Foreign
uncommitted changes at run start: FIRST look for a live concurrent writer — a fresh
checkout lock, or foreign files modified within the last ~10 minutes — and if one is
plausible, stop with needs-you class `checkout busy` (never commit into a contested
tree). No live writer → quarantine the dirt in ONE labeled commit, `chore(wip): foreign
tree state at drain start`, name it in the report, and PROCEED — the commit predates
every `gate_base`, so no gate verdict covers it and it is never squashed into any
goal's commit. Never stash silently, and never end a run over dirt nobody is writing. A
DIVERGED branch still stops and reports — that is history surgery, not dirt. If
`docs/goals/index.yaml` is missing, report "no goals queue — create goals with
/define-goal" and end the iteration.

If `config.base` is set and the current branch != `config.base`, STOP and report — you
are on the wrong working branch; checkout `<config.base>` first. Never silently work on
the wrong branch.

**Drained-queue terminal stop.** Dispatch stops when there is nothing left to do: when
Phase 2 finds no ready goals AND needs-you is empty. Exactly ONE closing line ends the
run — never both: a run that worked ≥1 goal closes with Phase 4's final summary line
(`stopped: drained`, inbox pointer per Phase 4); a run that finds the queue already
drained at start (zero goals worked) emits `factory drained — <done>/<total> done`
instead (appending ` · inbox: <N> captured → /process-inbox` when `docs/goals/inbox.md`
has unconverted items) and stops. A terminal stop still runs Phase 4 first. A later
`/dispatch` re-run picks up newly-added goals.

**Ship step — every terminal stop: unshipped is not done.** Before the closing line, if
the target repo's OWN CLAUDE.md/AGENTS.md carries a standing authorization to publish —
"push every time", "commit and push without asking", a named release command declared
pre-authorized — RUN that path now and put the outcome in the closing line
(`shipped: <push|command> ok` / `ship FAILED: <one clause>` as needs-you class
`environment failure`). When those docs declare more than one publish path, run every
declared path the diff touched and report per-service (a path is touched when
`gate_base..HEAD` — or, at a terminal drain stop, the commits this run produced —
intersects a path the declaring doc ties to that publish command; if the docs do not
map paths to services, run every declared path). One shipped and one not is
`ship FAILED: partial (<service> unshipped)`, still class `environment failure`. No
standing authorization in the repo's docs → one clause, `not shipped (no standing
authorization)`, and nothing more — never an offer. The rule keys STRICTLY off the
target repo's own docs; dispatch never invents a deploy.

**Chain to the inbox — a user-invoked flagless drain finishes the loop.** When a
flagless drain the USER invoked ends `stopped: drained` with ≥1 unconverted inbox line,
do not point at `/process-inbox` — INVOKE it, flagless, once. Chain guards, both hard:
never when THIS dispatch run was itself invoked by process-inbox step 6 (the chain
never loops), and at most one chain per session. Count-limited runs, solo mode, and
stops other than `drained` keep the pointer instead.

At end-of-drain only (NOT per-goal — no polling), if the working branch has a remote
AND `gh` is available and authenticated, do ONE non-blocking check of the latest CI run
on the current branch (`gh run list --branch <current> --limit 1`); if it is failing,
surface needs-you class `CI failure` — never block, never wait on it. If `gh` or the
remote is absent, skip silently.

**Latest-context preflight (read-only, never a gate).** Before spawning an implementer,
gather only the context that helps avoid stale work: the newest
`docs/superpowers/plans/*.md` / `.superpowers/sdd/progress.md` if present, and (when
`gh` is available) the open PR for the current branch or the most recently updated open
PR. Summarize in at most five bullets and pass to the implementer under "Latest
context". PRs, plan docs, and review comments are context only — they create no merge
gate, authorize no branch switch, and override neither the goal contract nor the local
gate.

Read the queue with a real YAML parser (`python3 -c 'import yaml,sys; …'`), never
line-greps — grep probes on the queue invent phantom statuses. Cheap doctor pass,
flagged in the report rather than silently fixed: every entry has its goal file and
vice versa; no circular `depends_on`; no `depends_on` pointing at a missing entry; warn
when a goal and its dependency declare different `base` branches. Plan-mirror re-sync
(the one doctor fix applied, not just flagged): scan the `Plan: docs/goals/plans/<file>
— Phase <N>` Context lines of goal files in `docs/goals/` AND `docs/goals/done/`,
resolve each goal's status from `index.yaml`/`archive.yaml`, and rewrite any plan
checkbox that disagrees — plan follows index, never the reverse — stamping
`status: done` on a plan whose phases are all checked; commit `chore(goals): plan-sync`
only when something actually drifted. The sync edits checkbox/status text ONLY — a
plan's `artifact:` page belongs to ideate and is never republished by dispatch.

**What that stamp MEANS.** On a plan of 3+ phases the last phase is the plan's OUTCOME
CHECK — a verification-only goal that runs every bullet of `## What will be true when
done`. Since the stamp fires when the last open phase checks, `status: done` means the
plan's outcome check PASSED — not merely that its pieces got built. A 1–2-phase plan
has no outcome check and its stamp keeps the older, weaker meaning.

On any environment failure you can't handle (missing tooling, an unrunnable
`config.verify` command, a queue the claim protocol can't write), stop the iteration
and surface needs-you class `environment failure` — `/factory-doctor` diagnoses and
fixes setup.

**Implementer-cost awareness.** When goals resolve to an expensive session model (no
per-goal `model:` fields and `config.model: inherit`) and the queue is mostly
`type: chore`, note once in the report that implementers inherit your model and that
the repo owner can have define-goal stamp per-goal `model:` fields. Do not apply a
fixed alias yourself.

`$PGVALIDATE` resolution (once, before the first gate) — ONE bash block (`find`, never
a brace-glob: zsh aborts the whole command when any brace alternative fails to match):

```bash
PGVALIDATE="$CLAUDE_PLUGIN_ROOT/skills/dispatch/scripts/pg_validate.py"
[ -f "$PGVALIDATE" ] || PGVALIDATE=$(find ~/.claude/plugins ~/.factory/plugins/cache -path '*/flywheel/*/skills/dispatch/scripts/pg_validate.py' 2>/dev/null | sort -V | tail -1)
[ -n "$PGVALIDATE" ] || echo "pg_validate.py not found — reinstall/update the flywheel plugin"
DISPATCH_REFS="${PGVALIDATE%/scripts/pg_validate.py}/references"
```

Hold the resolved absolute paths in `$PGVALIDATE` and `$DISPATCH_REFS` — the latter is
where this skill's reference files live, Read on demand at the step that names them.

## Working a goal — the canonical per-goal sequence

For each claimed goal, in order:
1. `anchor` = current HEAD (clean). `git commit` the claim → `gate_base` = HEAD now.
2. Spawn ONE implementer (plain `Agent` spawn — no `name:`, never backgrounded; then
   wait per the Spawning-and-waiting rule) that works in this checkout on the current
   branch under the method mandates (writing-plans, TDD,
   verification-before-completion) + config.skills + the goal's `skills:`. The brief is
   canonical (`$DISPATCH_REFS/implementer-brief.md` — Phase 3). It commits its work on
   the branch, writes its full evidence to a report file, and ends with a terse
   fixed-format `STATUS:` report. It never merges, never opens a PR, and it does NOT
   review its own work — the gate's independent review (step 3) is the second view.
3. Run the LOCAL gate authoritatively yourself. The gate has two independent arms over
   the same frozen `gate_base..HEAD` range — the deterministic commands (Arm A) and the
   independent review (Arm B) — and neither consumes the other's output, so OVERLAP
   them: start Arm A as a background command, spawn Arm B, and join both before any
   verdict (the join obeys the Spawning-and-waiting rule).
   **Arm A — the gate commands, started FIRST, in the background.** ONE Bash call,
   `run_in_background: true`, that runs
   `python3 "$PGVALIDATE" --head HEAD --base <gate_base> --goal <id> --goal-file docs/goals/<id>.md`
   then each `config.verify` command in order, echoing every exit code, so the join
   reads one output file and reconstructs the full result. A background COMMAND is safe
   where a background review spawn is banned: its exit codes and log land in an output
   file you Read at join time — nothing returns through a turn that can be discarded.
   The overlap is an optimization, never a requirement: with no reliable
   background-shell mode (run it foreground on Droid), or when the mechanical carve-out
   skips Arm B, run the same commands in the foreground; the verdict rule is identical.
   **Arm B — independent review, sized by the DIFF (maker–checker, ALWAYS for
   non-trivial work).** Decide the review's size from `git diff <gate_base>..HEAD
   --stat` plus the diff body — never from the implementer's claims about its own work:
   - **Default — ONE reviewer.** Spawn one fresh read-only adversarial reviewer — the
     gate-reviewer plugin agent when the runtime lists it, else the generic type with
     the role inline (Named review agents above; no model parameter) — over the
     `gate_base..HEAD` diff plus the goal file, handing it the implementer's
     report-file path to challenge. It runs even when the diff looks clean.
   - **Escalate to the 2–3-lens PANEL instead of the single reviewer** when the diff
     spans MORE than 3 files, changes test logic, or touches architecture/public
     interfaces: spawn 2–3 fresh-check plugin agents (else generic) as concurrent
     foreground lenses in ONE message — (a) contract-conformance, (b) tests +
     overbuild, (c) stray files + regressions — each read-only, no model parameter.
     The panel REPLACES the single reviewer, never follows it. On Droid the panel is
     K awaited Task calls in one message, exactly like a wave.
   - **The mechanical carve-out (the ONLY legal review skip).** A genuinely one-file
     mechanical edit skips Arm B — legal ONLY when (a) the diff touches exactly one
     file, AND (b) the change is mechanical (a rename, a constant/config value, a
     comment/doc line, a regenerated artifact) with no new branching, no
     signature/API change, no test-logic change; any doubt means not mechanical.
     Judge both from the DIFF itself. State the decision in the fire's reporting
     either way (`last:` carries `reviewed` or `review-skipped: mechanical`) — a
     silent skip is indistinguishable from a forgotten reviewer in a later audit.
     Arm A still runs in full.
   The reviewer/lens brief carries, verbatim where quoted: try to REFUTE the work, not
   confirm it — (a) contract conformance: any acceptance criterion unmet or met
   vacuously; (b) test realness: proving tests assert real behavior, not tautologies —
   hunt the vacuous shapes by name: errors swallowed inside a proving loop, a sweep
   hand-capped below its claimed coverage, input pre-sorted/pre-narrowed so the swept
   variable cannot vary, the subject mocked out of its own test, and a full-confidence
   claim with no precondition check behind it; (c) scope: changes beyond the goal's
   surfaces, or criteria quietly narrowed. Calibration: report half-believed findings
   too, marked uncertain, instead of silently dropping them — the orchestrator is the
   verifier; a Critical finding names the inputs/state that trigger it plus the wrong
   outcome, quoting the offending line. A scope-of-reading BUDGET, and it is a number:
   read the diff once; step outside it for AT MOST TWO risks the reviewer can NAME, one
   cheap read-only command each, both named in the report; the whole review is ~15 tool
   calls (per lens: ~10), and passing that means stop and report what you have. What is
   NEVER a focused check: running the build/lint/typecheck/test suite (Arm A owns
   those, concurrently), mutation-testing a copy of the tree, independently re-deriving
   what the diff computes, probing via a written scratch script — read-only covers the
   shell too. One concurrency rule: Arm A's commands run in this checkout
   concurrently — do read-based verification first and run any named-risk command
   check LAST. Two anti-laundering rules: a stated rationale in the implementer's
   report never downgrades a finding's severity, and a defect the goal contract itself
   mandates is still a finding, labeled contract-mandated. Non-findings (tell the
   reviewer up front): failures already red on the pre-goal baseline per the
   implementer's report, and the gate's auto-exempted test paths — but the baseline
   claim is itself a hypothesis a doubting reviewer reports as uncertain, and you
   verify cheaply (does the same failure reproduce at `gate_base`?).
   It returns a verdict plus findings with severity and `path:line` evidence. Findings
   are hypotheses you verify yourself — never orders; verified Critical/Important
   findings enter the FAIL_FIXABLE repair path — EXCEPT a verified contract-mandated
   finding, which is a contract defect: route it FAIL_CONTRACT (reset + block,
   needs-you class `contract defect`) — a repair agent cannot fix code into a
   defective contract.
   **Join — no verdict before BOTH arms are in hand.** When Arm B returns, Read Arm
   A's output file (commands still running → wait on that task ONCE, then read the
   output — never a repeated sleep+`ps` / task-status poll loop on EITHER harness:
   one wait, then read the output; never grade a partial gate). Show the command
   output. Every `config.verify` command must exit 0.
   **Flake protocol (bounded, logged — never a repair).** When a verify command fails
   on a test the diff does not touch and the goal's surfaces do not reach, re-run THAT
   test once in isolation before the verdict: an isolated pass is a flake — count the
   command as passed, name the flake in the fire's report, and on the second flake in
   one session surface a `recurring lesson` proposing quarantine/deflake; an isolated
   fail is a real FAIL. One retry maximum, never a repair spawn for a flake. A failure
   in anything the diff DOES touch gets no retry: that is the gate working.
4. PASS → `git reset --soft <gate_base> && git commit -m "feat(goal <id>): <slug>"`
   (squash to one), then `chore(goals): complete <id>`; push if a remote exists
   (non-blocking).
   **Plan mirror (plan-backed goals only).** If the goal's Context carries a `Plan:`
   link, flip that phase's `- [ ]` to `- [x]` in the plan file INSIDE the same
   `chore(goals): complete <id>` commit (the claim protocol's one sanctioned
   exception), appending `· as-built: matched` — or one line naming the deviation,
   from the gate review already in hand — and stamping frontmatter `status: done` when
   the last open phase checks. A DISPLAY mirror only: `index.yaml` stays the sole
   status authority, and a missing/unwritable plan file is a one-line report note,
   never a settle blocker.
   **Then, on every PASS, surface the goal's subjective criteria.** Re-read
   `docs/goals/<id>.md` and collect every acceptance criterion carrying the
   **needs independent review** marker. For each, emit an `fyi:` item as class
   `needs independent review` — its `<reason>` half is the criterion's own subject,
   and its `→` half is **what to run and what to look for** — the command, URL, or
   surface the implementer's report actually exercised plus the thing a human should
   judge there, drawn from the report file, never the criterion text repeated
   verbatim. Report evidence too thin to name a surface? Say so in the `→` half and
   name the report path — never drop the item. A goal with no such marker surfaces
   nothing. This is an observation, never a completion gate — a PASS still completes
   the goal and an unattended drain keeps claiming.
   Then run Settle triage (below) and report; the run claims the next ready goal
   unless a stop condition has fired.
   FAIL_FIXABLE → one repair round per `$DISPATCH_REFS/escalation-and-repair.md` —
   warm resume of the goal's own implementer when the harness supports it, else one
   fresh repair agent on the same resolved tier; the COMPLETE verified findings list
   in one go, the receiving-review rules appended, re-gate with the step-3 overlap;
   still failing → `git reset --hard <gate_base>`,
   `chore(goals): block <id> — <reason>`. FAIL_CONTRACT → reset + block, reason
   `contract defect: <the verified finding>` (needs-you class `contract defect`).
   INCONCLUSIVE → reset + block
   `no runnable local gate: <the failing check's evidence from the JSON>` (needs-you
   class `no runnable local gate`) — the evidence names the exact cause and operator
   fix, so it must reach the block reason.

`anchor`/`gate_base` matter: the claim's `index.yaml` edit lands BEFORE `gate_base` is
set, so the validated diff (`gate_base..HEAD`) is exactly the implementer's work. A
`git reset --hard <gate_base>` discards only the implementer's commits; the claim
commit survives, ready to be flipped to `blocked`.

The gate verdict comes from `pg_validate.py`'s JSON `verdict` field (PASS=exit 0,
FAIL_FIXABLE/FAIL_CONTRACT=exit 3 — read the JSON to split them, INCONCLUSIVE=exit 4)
AND the `config.verify` commands (any non-zero exit = FAIL_FIXABLE for that command's
failure). You run the gate — the implementer's verification summary is evidence, not
the verdict.

**Windows note.** `type: bug` goals build a temporary base worktree with symlinked dep
dirs, which needs the Windows symlink privilege (Developer Mode or an elevated
session); without it the gate returns an actionable INCONCLUSIVE naming that fix.
`factory-doctor` preflights this (`symlink-privilege`). The gate's command runner is
tunable via `PG_BASH` and `PG_VALIDATE_TIMEOUT` (seconds per acceptance command,
default 1800).

## Settle triage — nothing survives as prose (every settle, PASS or FAIL)

Chat prose evaporates when the session ends; only committed artifacts survive. BEFORE a
goal's settle commit, walk every loose end this cycle produced — each `Concerns:` line
of a DONE_WITH_CONCERNS report, every reviewer finding verified real but out-of-scope,
every "needs a new goal" / "follow-up" recommendation, every recurring-lesson
proposal — and give each item exactly ONE of these four dispositions —
**unsure → Report-only**: Report-only is the DEFAULT — an item that does not clearly
meet one of the capture bar's three earning shapes is under the bar:

**One carve-out, and it outranks the default.** An item that would FALSIFY a bullet in
the goal's linked plan `## What will be true when done` is NEVER Report-only, however
unsure you are. It carries the `live-defect` earning token by construction — so the
capture item's "if you cannot honestly name one shape → Report-only" cannot re-route
it — and it earns its inbox line. The operative test is narrow: the item qualifies
when, if true, it would make an outcome bullet's COMMAND fail, or make a
`**needs independent review**` bullet false. Being topically related to a bullet is
not enough. This is a carve-out for the WHOLE outcome, not a rollback of the capture
bar — nits, latent findings, fail-safe residuals, and contract-mandated tradeoffs
stay Report-only exactly as they are; the bar filters nits, and an outcome bullet is
the one thing measuring whether the plan delivered.

1. **Repair now** — it breaches THIS goal's own contract → it is a gate finding; route
   it FAIL_FIXABLE. A DONE_WITH_CONCERNS whose concern invalidates an acceptance
   criterion is not a PASS.
2. **Dismiss** — verified false or already tracked → one line of reasoning in the
   goal's report file (the `## Orchestrator` section — "the fire's report" always
   means that FILE, never the chat turn). **Dismiss is for items that are NOT REAL**
   (disproved, or already captured elsewhere). An item that is real but worthless — a
   wrong test caption, a cosmetic nit — is disposition 4, which names those classes
   explicitly; when both seem to fit, take 4. The record must not confuse "this was
   false" with "this was true and under the bar".
3. **Capture** — real, outside this goal's contract, AND over the capture bar → append
   ONE line to `docs/goals/inbox.md` (create on first use), commit
   `chore(goals): inbox <id>`:
   `- [ ] <YYYY-MM-DD> <source-goal-id> <bug|feature|chore> — <one-line description> (earn: live-defect|new-work|owner-decision) (evidence: <report path or path:line>)`
   **The capture bar — exactly three shapes earn an inbox line:** (a) a LIVE defect
   (`live-defect`) — wrong behavior reachable on current code; (b) genuinely NEW work
   (`new-work`) — missing wiring, a missing consumer, a feature gap the owner would
   want built; (c) an OWNER decision (`owner-decision`) — spend, data loss, anything
   irreversible or externally visible.
   **Capture is legal ONLY when the appended line carries its earning token** — the
   `(earn: …)` field naming, in the line itself, which of the bar's three shapes the
   item meets. If you cannot honestly name one shape, the item is not over the bar →
   Report-only. An inbox line without its earning token is a capture that did not
   happen — never append it.
4. **Report-only** (the DEFAULT — unsure lands here) — real but under the bar: latent
   or unreachable-today findings, fail-safe residuals, deliberate contract-mandated
   tradeoffs, test-caption/comment-wording nits, watch items. One line in the goal's
   report file naming the item and this disposition. The bar keeps the inbox a queue
   of work, not a review archive.

A goal does NOT settle `completed` while any loose end is unclassified — that is the
definition of "complete" this factory ships. The inbox is capture-only: no statuses, no
priorities, never touched by implementers. define-goal converts items to real goal
contracts and removes converted lines — that conversion is the ONLY edit anyone but
dispatch makes.

## Parallel mode — the lane model

The full lane model — admission control, the lane lifecycle, the serialized integration
lock, and every failure ruling — lives at `$DISPATCH_REFS/parallel-mode.md`. Read it
BEFORE claiming a wave whenever a run carries `--parallel`, whenever a flagless drain
auto-enters lane mode, and whenever Phase 1 finds lane-backed claims
(`git branch --list 'lane/*'`). The one-paragraph version: N goals BUILD concurrently
in disposable local worktree lanes; admission requires provably-disjoint `touches:` (a
goal without `touches:` runs alone) and excludes conflict domains (lockfile,
migrations, CI, global config); integration stays strictly serial — rebase the lane
onto branch HEAD, re-run Arm A on the integrated tree, squash, fast-forward — so the
branch only ever advances to gate-verified trees.

## Phase 1 — finish in-flight goals

Before claiming anything new, settle every `in_progress` entry — finished work beats
new work.

**Single-`in_progress` invariant (data-loss guard) — lane-aware.** In serial operation
a healthy queue has at most ONE `in_progress` entry. FIRST check for lanes: an
`in_progress` entry whose `lane/<id>` branch exists (`git branch --list 'lane/*'`,
`git worktree list`) is a parallel-mode claim — its work lives in the lane, so the
reset-past-newer-work hazard does not exist for it. Settle each lane-backed entry
through the Parallel-mode lifecycle from its furthest checkpoint: lane has commits →
run its in-lane gate and integrate (one at a time); lane empty → respawn its
implementer in the lane; lane branch listed but worktree missing → recreate the
worktree at the branch tip. For entries with NO lane: MORE than one lane-less
`in_progress` on a linear branch means a `git reset --hard` on the older could destroy
the newer's work — STOP, roll back nothing, surface `multiple in_progress claims —
manual review`. When exactly one lane-less `in_progress` exists, proceed:

`gate_base` is not stored in `index.yaml` — recover it from git: the SHA of the goal's
claim commit, `git log --grep="chore(goals): claim <id>" --format=%H -1`. Decide by
whether work commits exist after that claim commit:

1. **Work commits present after the claim commit** → recover `gate_base`, then read
   the sitting's `STATUS:` from the dead session's report file
   (`~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md`) or its final message.
   A declared `BLOCKED` / `NEEDS_CONTEXT` / `CONTRACT_AMBIGUOUS` / `GOAL_UNREACHABLE`
   keeps its own routing (`$DISPATCH_REFS/escalation-and-repair.md`). **No `STATUS:`
   block at all → resume from increments, never gate-then-reset**: a missing
   `STATUS:` block on a returned implementer is itself the trigger for the
   resume-from-increments rung — read `gate_base..HEAD`, re-brief ONE fresh worker
   with what already landed, let it finish from current HEAD on the same claim and
   `gate_base`, and route its own `STATUS:` normally. A second consecutive
   STATUS-less death re-fires the resume-from-increments rung while the
   transient-death budget has headroom; only a spent budget blocks
   `repeated transient death` — rung 5's guard. The gate —
   and its FAIL-path rollback — never fires first on a sitting whose implementer never
   declared DONE: that rollback destroys landed increments. The report check below
   runs only once a `STATUS: DONE` (or a regenerated stub) exists.
   **Completion-shaped `STATUS:` present (`DONE` / `DONE_WITH_CONCERNS`) → the gate
   path.** Hand the report file to the reviewer as usual; absent is fine — that is
   the crash-recovered reviewer handoff only (the diff and goal file suffice for
   Arm B), never a license to complete without a report. Before running the gate, if
   that report is missing, empty, or older than `gate_base`, regenerate a stub report
   from `gate_base..HEAD` at the same path FIRST so Arm A cannot reset a sitting that
   only lacked the file. Then run the gate (Working a goal, step 3). PASS → squash +
   `chore(goals): complete <id>`. FAIL_FIXABLE → one repair round, re-gate; still
   failing → `git reset --hard <gate_base>` + `chore(goals): block <id> — <reason>`.
   FAIL_CONTRACT → reset + block (class `contract defect`). INCONCLUSIVE → reset +
   block (`no runnable local gate: <evidence>`).
2. **No work commits and no active agent** (stale claim) → `gate_base` is the current
   HEAD. Apply the stale-claim rule from Re-entrancy: re-spawn from current HEAD, or
   `blocked` per its final report / `GOAL_UNREACHABLE` / the transient-death cap.

## Phase 2 — claim the next goal

Ready = `status: not_started` AND every `depends_on` entry is `completed` — a `blocked`
dependency makes dependents not-ready; report the stuck chain. Pick `priority: high`
first, then top-most in the file; claim via the protocol BEFORE spawning. A per-goal
`base:` field overrides `config.base` for that goal — but since dispatch works on the
currently-checked-out branch, a goal whose `base:` differs from the started branch is
surfaced as class `base: mismatch`, never silently worked.

If `config.budget` is exhausted, stop claiming (Hard rules) and let the current goal
finish. Never claim a goal while another is unsettled.

## Phase 3 — spawn the implementer (depth 1, foreground)

One Agent per claimed goal, never backgrounded (on Droid: one `Task`,
`subagent_type: worker`, `await: true`). In serial mode: NO worktree — it works in THIS
checkout on the current branch. In parallel mode the same brief applies with only the
Workspace paragraph substituted (`$DISPATCH_REFS/parallel-mode.md`), and all wave
spawns go out in ONE message. Set the spawn's `model` parameter to the goal's resolved
implementer tier (`inherit` = omit the parameter). Pass NO `name:` (Hard rules) — warm
resume does not need one: the spawn returns the agent's own id and the repair round
resumes it by that id.

The brief is canonical and lives at `$DISPATCH_REFS/implementer-brief.md` — Read it,
fill in `<id>`, `<SLUG>` (= the repo dir name), the resolved skill lists, and the
latest-context bullets, and pass the filled block as the spawn prompt. Never paraphrase
the brief from memory — the brief file is the contract.

After the implementer returns, run the independent review and the gate yourself
(Working a goal, steps 3–4). Any status other than a clean `DONE`, and any gate verdict
other than PASS, routes through `$DISPATCH_REFS/escalation-and-repair.md` — the warm
repair round, the receiving-review rules, the focused re-check, the escalation ladder,
and the contract-defect short-circuits are all specified there. Read it when a status
or verdict demands it and follow it exactly — never improvise a repair or a block from
memory.

## Solo mode — work one named goal in this session

"Work goal 005" — or `/dispatch 005`, `/dispatch 5`, `/dispatch 005-slug` — scopes the
run to a single id: skip Phase 2's ready-scan, claim that goal directly via the
protocol, and run it through Working a goal. Everything else is identical, and the run
stops after that one goal (a batch flag alongside an id is ignored — the id wins).
Guards before claiming: a named goal that is `completed` or already `in_progress` is
reported, not re-claimed; one whose `depends_on` are not all `completed` is surfaced as
class `unmet dependency` instead of claimed; an id matching no entry reports the
near-misses.

## Phase 4 — report (the report IS the message — nothing rides along)

`[dispatch] <done>/<total> done [<bar>] · ready: <count> · blocked: <count> · inbox: <unconverted inbox lines, omit when zero> · current: <id or none> · last: <id PASS (reviewed, <N>m | review-skipped: mechanical, <N>m)|FAIL (<N>m)|none> · needs-you: <blocked goals + human decisions, or nothing>`

**The output envelope:**

- **A per-goal settle turn is the report line and NOTHING else.** No headings, no
  narrative recap, no gate story, no "claiming X next". Everything else you want to say
  about a goal — findings verified or refuted, dismissal reasoning, Report-only items,
  judgment calls — is APPENDED to the goal's report file
  (`~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md`, under an
  `## Orchestrator` heading).
- **The closing turn is: the report line, the summary line, one bullet per needs-you
  item, one bullet per fyi item. Nothing else, and never a second closing message.**
  Hard ceiling ~15 lines; a needs-you bullet's reason half stays under ~120 chars.
- **A plan-tool update is a PRE-CLOSING action — the closer stays last.** Any harness
  plan/artifact status acknowledgement (Claude Code's plan-tool update, Droid's
  `Plan is up-to-date.`) is ALLOWED, never banned; it must simply land BEFORE the
  closing turn is emitted — the closer is the run's last message, always.
- **Interstitial narration between report lines is at most one short sentence** and
  never restates a finding, a diff, or a verdict.

Lead with **progress** (`<done>/<total>`), never `ready/total` — a bare `ready/total`
reads as "nothing done". Every number carries its label. **The counts come from ONE
fresh read of `index.yaml` at settle time — never an incremented remembered count.**
Re-read the index when composing the line and derive every counter — `done`, `ready`,
`blocked`, `total` — from that single read (a remembered `done += 1` drifts the first
time a Phase 1 settle, a retire, or a requeue changes the index):
- `done` = completed · `ready` = not_started with all `depends_on` completed ·
  `blocked` = `blocked` status or not_started with an unmet dependency · `current` =
  the goal being worked this fire (parallel mode: the live lane ids, `+`-joined) ·
  `last` = the most recently gated goal and its verdict (a goal settled WITHOUT a gate
  run — a live BLOCKED / GOAL_UNREACHABLE / CONTRACT_AMBIGUOUS short-circuit — reports
  `<id> FAIL`; needs-you carries the detail). A gated `last` also names its review
  decision — `reviewed` or `review-skipped: mechanical` — so the carve-out leaves an
  audit trail in every fire's report. `last` also carries the goal's claim-to-settle
  wall-clock as `<N>m` (integer minutes; `settled_at` − `claimed_at` from the entry
  the settle just wrote; fall back to the claim/settle commit author dates) — e.g.
  `last: 172 PASS (reviewed, 41m)`. A retirement shows no duration. A duration is a
  FIELD, never a sentence — and read it with skepticism: a sitting spanning a
  usage-limit pause looks slow and isn't.
- Any residual `in_progress` entry this fire could not settle counts into `blocked`
  (as blocked-pending) so that `done + ready + blocked` always equals `total`.

The bar is 20 cells: `filled = round(20 × done ÷ total)` (0.5 rounds up), clamped to
[0, 20]; empty = 20 − filled. Filled cells = █, empty = ░; omit the whole bar when
total = 0. Anchor example: 19/21 → round(18.10) = 18 filled →
`[██████████████████░░]`.

**Every multi-goal run** (the drain default included): the one-line report above is
emitted after EACH settled goal, and one final summary line closes the run:
`[dispatch] worked <n>: <id PASS (<N>m)|FAIL (<N>m)|RETIRED, …> · stopped: <count reached|drained|budget exhausted|environment brake> · shipped: <outcome per the Ship step> · <all complete | outstanding: <n> for you>`
(each worked goal carries its claim-to-settle minutes; RETIRED shows none; the summary
line appends no extra heartbeat).
**The closing state is a word, not an essay:** `all complete` when the queue is
drained, nothing is blocked, and needs-you is empty; otherwise `outstanding: <n> for
you` where `<n>` counts exactly the needs-you bullets that follow (fyi items never
count). When the run stops with a non-empty inbox and the chain rule doesn't fire, the
summary carries `inbox: <N> captured → /process-inbox`. This summary line is the run's
ONE closing line; Phase 0's `factory drained` line replaces it only when the run worked
zero goals.

needs-you lists what is genuinely waiting on the human AFTER the Self-heal pass has
run: goals still `blocked` because their defect needed a second amend or hides an owner
fork (with the dependents stuck behind them), a `base:`-mismatched goal, `budget
exhausted`, an environment the run could not clear. The non-blocking observations — a
red CI run, a `recurring lesson`, every criterion marked **needs independent review**
on a goal this fire PASSed (those goals are `completed`, so the item asks for a look,
not a decision), a goal this run retired — render under **`fyi:`** instead: same line
shape, after the needs-you bullets, never counted in `outstanding:`. A dep-blocked
goal (waiting on another goal) is NOT human-blocked — it appears only as a "dependent
stuck behind" a goal that is. Every item uses the canonical needs-you format — the
`→ <what to run>` half is not optional.

**Stalled factory → one real notification.** The fire that first finds the factory
fully stalled — needs-you non-empty and nothing this iteration could do about it —
sends the needs-you line via the PushNotification tool (ToolSearch loads it if
deferred). One notification per distinct blocker set; identical no-op fires after it
send none, though the report line still goes out every fire.

**Heartbeat (liveness) — every fire** (in a multi-goal run, once per per-goal cycle).
APPEND one line — `<UTC timestamp> · <done>/<total> · current <id or none> · drained
<yes|no>` — to `~/.local/state/pg-dispatch/<SLUG>/heartbeat` (`mkdir -p` first; then
trim to the newest ~50 lines) — and re-write the checkout lock's line in the same
step. Two readers: (1) liveness — a silently-dead orchestrator emits nothing, so the
next `/dispatch` or an external watcher compares the newest line's age to the expected
cadence; (2) the cross-fire brake counts lines after a stale claim's date to measure
fires observed — which is how a usage-limit pause is told apart from a goal failing
across live fires. The drained flag feeds the terminal stop.

## Hygiene

When `completed` entries crowd the index (~20+), move their files to `docs/goals/done/`
and their entries to `docs/goals/archive.yaml` in one `chore(goals): archive` commit —
and move any plan stamped `status: done` to `docs/goals/plans/done/` in the same
commit. The queue commit is always its own step. Agents read the whole index every
iteration — keep it small.

**Encode recurring lessons.** When the same class of gate failure recurs across
different goals, that is a system defect, not a string of per-goal bugs: surface ONE
needs-you line as class `recurring lesson`, its `→` half proposing where to encode it —
a `config.verify` command, a `config.skills` entry, a CLAUDE.md rule, or a contract fix
via define-goal. Propose only; the repo owner decides what lands.
