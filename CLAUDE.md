# flywheel

## Project Overview

Skills-first plugin marketplace from Pragmatic Growth, dual-target since
v7.0.0: **Claude Code and Factory Droid are both first-class harnesses**
(Droid installs the Claude-layout plugins via its compatibility translation;
v5.0.0 had removed the old dual-CLI support, v7.0.0 restored it on a new
architecture — one harness-neutral **execution-tier vocabulary
`heavy|medium|light`** plus one small harness-mapping block per skill,
instead of the v4.x dual-branch prose).
The repo publishes ONE plugin from the `pragmatic-growth` marketplace:
`flywheel` v11.0.0.
(The `html-artifacts`, `autoresearch`, `human-writing` plugins were **removed**
from the marketplace in v8.0.0, owner decision
2026-07-25 — the marketplace is the goal-factory only now; git history keeps
them recoverable.) No MCP
servers, no commands, no hooks, no build step. ONE scoped exception to the
skills-only rule, as of v5.4.0: THREE plugin agent definitions
(root `agents/` — the factory's read-only review roles `gate-reviewer`,
`fresh-check`, `contract-red-team`; added by owner-delegated decision
2026-07-16 after transcript forensics on real dispatch runs showed
hand-composed review briefs drifting across fires. Each carries the role
brief + output contract as its system prompt and a tool allowlist with no
write-capable tools (the list names both harnesses' shell tools, `Bash` + `Execute` — each harness silently
ignores the other's; live-verified on Droid 2026-07-25 — and ONLY tool IDs one of the two
harnesses defines, since Droid validates `tools:` against a fixed table and an unknown ID
is a validation error), pins no `model:`, and has a deliberately narrow
description so the agent never auto-delegates to it outside flywheel skills;
the skills always keep a generic-type-with-inline-brief fallback
(`general-purpose` on Claude Code, `worker` on Droid; spawn plugin agents as
`flywheel:<name>` on Claude Code, bare `<name>` on Droid), and
the built-in Explore type (Claude Code) and `explorer` (Droid) are banned
for review roles).
`flywheel` has six skills under root
`skills/` (three ship deterministic Python helpers in `scripts/`), forming a
plain-language → autonomous-execution pipeline around a file-based goal queue
(`docs/goals/` in target repos): `/ideate → /define-goal → /dispatch →
/goals-status`, with `loop-architect` and `factory-doctor` as the rails. There
is no `plugins/` directory — the repo root IS the flywheel plugin.

- **ideate** (v11.0.0 — rewritten around the PLAN, the factory's design tier,
  after the 2026-08-12 riptide/RPI deep-read + estate forensics; originally
  adapted from superpowers' brainstorming, 2026-07-24) — the pipeline's front
  door: explores a fuzzy idea and writes an approved plan at
  `docs/goals/plans/YYYY-MM-DD-<topic>.md` (template:
  `skills/ideate/references/plan-template.md`; replaces the v6-era design
  brief — existing `docs/goals/briefs/` links stay valid). Context orientation
  first (1–2 read-only subagents max, medium tier — `general-purpose` +
  `model: sonnet` on Claude Code, `explorer` + `complexity: medium` on Droid),
  then a VERTICAL-SLICE scope check (each piece independently verifiable
  end-to-end; "if a piece cannot be verified without a LATER piece existing,
  it is not a slice"; pieces map 1:1 onto goals + `depends_on`). Question
  diet: design forks become the plan's Open-questions section (options +
  recommendation each; ONLY the owner resolves; "go with your recommendations"
  resolves all at once with provenance recorded; resolved questions keep their
  why forever) — at most ONE AskUserQuestion round during exploration, and the
  plan presentation is the single approval touch. The plan is code-shaped at
  signature altitude (exact signatures with bodies elided, file-tree diff,
  call flows only where non-obvious — never function bodies) with
  takeaway-stating headers. Dispatch checks phases off as their goals
  complete, so the plan doubles as the progress view. HARD GATE: its only
  terminal states are invoking define-goal with the approved plan or the user
  parking the idea — it never writes goal files, index entries, or code.
  Single-goal outcomes stay fileless; already-shaped wants skip it entirely;
  re-invoking on a planned idea iterates the same plan file. Grounding: the
  2026-08-12 forensics (335 measured cycles) showed blocked-goal
  amend-thrash — design forks surfacing at dispatch time — cost 10–85 hours
  per goal, the estate's dominant wall-clock tail; the plan resolves forks
  where they cost minutes.
- **define-goal** — plain-language wants → measurable goal contracts.
  Two destinations: a copy-pasteable `/goal` line to run now, or a queued
  goal file (`docs/goals/NNN-slug.md` + `index.yaml` entry). Includes
  repo grounding (CLAUDE.md rules copied verbatim, real
  verification commands) and a batch mode for documents of items.
  Stamps each queued goal's frontmatter `model:` (inherit|heavy|medium|light;
  legacy opus/sonnet/haiku stamps read as heavy/medium/light aliases forever,
  never written anew)
  LAST, after the acceptance criteria are final, from a contract-tightness
  rubric (v4.15.0; rebalanced v6.2.0, owner decision 2026-07-24; tier
  vocabulary since v7.0.0): the goal
  `type:` picks the lane and wins ties — heavy is the DEFAULT for every
  feature/bug goal (tightness is never a downgrade reason; an explicit user
  ask for cheap execution is the only route down), medium is rote
  chore-shaped work only (lint/doc/config sweeps, ports with an exact
  source of truth); unsure → the stronger. Every queued goal gets an adversarial contract review first
  (v5.1.0): one fresh read-only subagent red-teams the drafted contract —
  gameability, command reality, type shape, gate fit, termination — one
  round, before the model stamp and the user confirmation (run-now `/goal`
  lines skip it; the `/goal` evaluator is their second view). As of v5.4.0
  that reviewer spawns as the plugin agent `flywheel:contract-red-team`
  when available (`general-purpose` + inline rubric fallback). v5.5.0 (from
  the superpowers eval-evidence deep-read): dependent goals in a `depends_on`
  chain carry an Interfaces note in Context (exact names the dependency
  produces — the implementer sees only its own goal file; red-team checks it,
  advisory), the tier rubric adds turn-count-beats-token-price to the light
  (formerly haiku — alias) caution, and ambiguity is named a contract defect in its own right
  (dispatch implementers STOP `CONTRACT_AMBIGUOUS` on a two-readable
  criterion instead of guessing). v5.5.1: the question round is split-first
  (split question before detail questions), option-based with a recommended
  default, and adaptively two-round — ONE extra targeted round (1–2
  questions) when a round-1 answer or review finding opens a genuine fork,
  two rounds total the hard cap
  (progressive one-at-a-time dialogue deliberately NOT adopted). Produces goals
  only, never implements. Originally adapted from
  OpenAI's curated `define-goal` skill (its `create_goal`/`get_goal`
  tools don't exist here; `/goal` is user-run, transcript-
  evaluated, 4,000-char condition cap). The `/goal` facts were verified
  against the shipped CLI internals (v5.3.0): the evaluator reads a
  recency-truncated transcript (→ contracts re-print final acceptance outputs
  in the closing turn; long runs announce "turn N of cap M"), its `impossible`
  verdict honors GOAL_UNREACHABLE only with evidence attached, it defers while
  background work runs, and it fails open on its own errors (never the only
  unattended rail). The UI scripted-check rule also generalizes to other
  drivable surfaces (CLI/API → drive-the-real-surface criterion). Since
  v7.0.0 the `/goal` facts are labeled Claude Code facts; on Droid the
  run-now destination is a self-contained contract prompt block invoked via
  `droid exec -f goal-prompt.md` (no evaluator — the contract itself carries
  the verification; live-verified 2026-07-25). v6.1.0: the
  red-team rubric adds a no-placeholders check ("TBD" / "appropriate error
  handling" / command-less criteria are vague-by-construction →
  contract-blocking); fuzzy still-being-explored wants route to ideate first
  (already-shaped wants never bounce; ideate unavailable → design
  conversation inline, the two-round cap governs only the contract
  interview), and an ideate handoff is treated as the brief — question rounds
  cover only remaining gaps, recon narrows to verify-and-complete, chain
  goals link the design brief from Context. v8.3.0 adds the ONE-SITTING rule
  + a matching red-team Size check: a goal is one implementer sitting — one
  subsystem, one drivable surface, ~≤5 acceptance criteria — else it's an
  unsplit `depends_on` chain and splitting is contract-blocking (unless
  Context states why it's atomic, then advisory); grounded in 2026-07-28
  cycle forensics (158 cycles, median ~57 min; every 13–18h outlier was an
  oversized contract). v11.0.0 (the plan release, forensics-backed
  2026-08-12): plan-backed wants get a FAST PATH — zero question rounds (the
  plan is the interview; the one exception is a red-team finding or plan gap
  opening a genuine fork), recon narrowed to verify-and-complete, phases as
  the batch item list, `Plan: docs/goals/plans/<file> — Phase <N>` in each
  chain goal's Context replacing per-goal Interfaces prose; non-plan wants get
  the QUESTION DIET (skip the round when every candidate question has a
  confident recommended default — state assumptions in the one draft
  confirmation instead); the GOAL-FILE DIET cuts `## If blocked` and
  `## Goal contract` from queued files (both live once in dispatch's
  implementer brief; the `/goal` line is run-now-only; old-format files stay
  valid; target ≤60 lines — corpus-measured 75–85 % ceremony before); the
  red-team adds a SLICE check (criteria unverifiable without a LATER goal in
  the same chain = horizontal cut → contract-blocking; stated forced-layer
  reason downgrades to advisory) and `agents/contract-red-team.md` caught up
  to the Placeholders/Size checks; amend mode takes the clearly-recommended
  reading without a question round unless the fork is a true owner decision
  (spend, data loss, irreversible/externally-visible).
**Harness note (v8.2.0; depth corrected v8.3.0):** on Claude Code a subagent can spawn
further subagents (Agent nests — official docs put the default nesting depth at 3 layers
below the main conversation, not the 5 previously claimed here; dispatch's
main → implementer → lens chain uses 2 and fits either way), so a dispatch implementer
runs its fresh-check panel directly.
On Droid a subagent has NO Task tool — Factory's docs state "a subagent cannot spawn its
own subagents" — so the implementer uses the sanctioned `droid exec -f <prompt-file>` path
for genuinely fresh review contexts (≤2 lenses; it costs a CLI cold start each). Self-review
in the implementer's own context is NEVER the fallback: an honest
`Fresh-check: not run (no fresh-context mechanism available)` escalates the orchestrator's
own review to the full panel, and is explicitly not a compliance miss.

- **dispatch** — factory orchestrator for the docs/goals queue: serial
  one-goal-AT-A-TIME on the currently checked-out branch, and since v10.0.0 a
  flagless run DRAINS the queue by default (keeps claiming ready goals until
  empty; `--count N` limits the run, `--unlimited` is a compat alias; since
  v11.0.0 a flagless drain auto-enters lane mode when `config.parallel`
  exists — see the v11 tail of this bullet — and `--serial` forces
  one-at-a-time) — no PRs,
  no remote or `goal/<id>` branches; since v9.0.0 a `--parallel [K]`
  batch mode (Claude Code only, default K=2, cap 4) builds provably-disjoint
  goals concurrently in disposable LOCAL worktree lanes
  (`~/.local/state/pg-dispatch/<SLUG>/lanes/<id>`, local branch `lane/<id>`,
  deleted at settle) under admission control (disjoint `touches:` globs — a
  goal without `touches:` is never co-scheduled; no dep path; conflict
  domains like lockfile/migrations/CI/config always exclusive; same base)
  while INTEGRATING strictly one at a time: rebase lane onto branch HEAD,
  re-run Arm A on the integrated lane tree, squash, fast-forward the branch —
  the branch only ever advances to gate-verified trees; a rebase conflict
  means a mispredicted touch-set → discard the lane, re-run serially,
  needs-you `parallel-conflict` (two in one run degrade the run to serial);
  post-rebase Arm A failure → one integration-repair, else `integration
  interference`. In serial mode per goal it
  records the pre-claim clean
  HEAD as `anchor`, commits the claim, records the post-claim HEAD as
  `gate_base`, spawns ONE foreground implementer that commits its work
  directly on the branch — on the goal's resolved implementer tier
  (goal frontmatter `model:` > `config.model` > inherit, v4.15.0; tiers since
  v7.0.0, mapped at spawn time — heavy/medium/light become
  opus/sonnet/haiku model pins on Claude Code, Task `complexity` on Droid; the
  orchestrator and recon/review agents always stay on the session
  model) — using a lightweight subagent-driven quality loop
  (plan/checklist, TDD, fresh verifier/reviewer subagent for non-trivial work;
  v5.4.0: the fresh-check panel spawns FOREGROUND as `flywheel:fresh-check`
  lenses — never background-then-poll, never Explore — after real runs showed
  sleep-loop waits discarding completed lens verdicts),
  then runs the LOCAL gate authoritatively: an independent review (v5.1.0 —
  for any non-trivial diff the orchestrator ALWAYS spawns one fresh read-only
  adversarial reviewer — v5.4.0: `flywheel:gate-reviewer` when available,
  `general-purpose` + inline brief fallback — over `gate_base..HEAD` + the goal file; the
  implementer's `Fresh-check:` lens verdicts are corroborating evidence,
  never the verdict; a missing block or a not-required claim the diff belies
  escalates to the full 2–3-lens panel; verified Critical/Important findings
  feed the repair path; v8.3.0 OVERLAPS the gate's two arms — the
  deterministic commands run as ONE background Bash started BEFORE the
  foreground reviewer spawn, joined before any verdict (both arms unchanged
  in content; a background command's output file can't be discarded the way
  a background review spawn's turn could — that scar stays); v8.3.0 also
  tightens the mechanical carve-out: a reviewer skip is legal only on a
  one-file genuinely-mechanical diff judged from the diff itself, and the
  decision is stated in the fire's report (`last: <id> PASS (reviewed |
  review-skipped: mechanical)`) — a real batch had settled goal 113 with no
  reviewer and no trace; v5.3.0 calibrates the reviewer — surface half-believed
  findings marked uncertain rather than silently dropping them, Critical
  findings quote the triggering line, pre-existing baseline failures and
  exempted test paths are named non-findings — and the implementer's verify
  step adds one off-happy-path probe at any drivable surface; v5.5.0 tightens
  gate economics + honesty from the superpowers eval-evidence deep-read:
  reviewers are diff-scoped — read the diff once, step outside only for a
  NAMED concrete risk, one focused check per named risk, else it's an
  uncertain finding, never a repo sweep — with two anti-laundering rules (a
  stated rationale never downgrades severity; a contract-mandated defect is
  still a finding → FAIL_CONTRACT, never the repair path); the implementer
  writes full evidence to `~/.local/state/pg-dispatch/<SLUG>/reports/
  <id>-report.md` and returns a ≤15-line `STATUS:` report (DONE |
  DONE_WITH_CONCERNS | BLOCKED | GOAL_UNREACHABLE | CONTRACT_AMBIGUOUS) so
  orchestrator context stays lean; an early `CONTRACT_AMBIGUOUS` stop routes
  two-readable criteria to a needs-you contract amendment before work is
  burned; repair is omnibus (one agent, complete findings list) and the
  focused re-check adds a collateral scan of the repair diff), then the
  deterministic `pg_validate.py`
  over the `gate_base..HEAD` diff plus the repo's `config.verify` build+test
  commands. PASS → squash the goal's commits to one `feat(goal NNN)` commit
  and mark it `completed`; FAIL → `git reset --hard gate_base` and mark it
  `blocked` (with reason). CI, if the repo has it, is a NON-BLOCKING post-push
  observation surfaced under needs-you — never a merge gate. Built to repeat as
  `/loop 15m /dispatch`; each fire handles at most one new goal and is idempotent. Each fire emits one report
  line leading with progress — `<done>/<total> done` plus a 20-cell fill
  bar, then labeled `ready`/`blocked` counts that sum to `total`
  (lead with done, never `ready/total`, which reads as "nothing done");
  `needs-you` holds human-blocked goals plus any non-blocking CI failures.
  Each fire APPENDS a heartbeat line (`~/.local/state/pg-dispatch/<SLUG>/heartbeat`,
  newest ~50 kept); the cross-fire brake counts heartbeat lines after a stale
  claim's date (≥3 fires with zero work commits → `blocked: repeated transient
  death`) instead of wall-clock age, so an account usage-limit pause (no fires
  → no lines) resumes a claim rather than mislabeling it dead. v6.1.0
  (superpowers full-plugin deep-read): invocation grammar —
  `/dispatch` worked the next ready goal (SUPERSEDED in v10.0.0: flagless now
  drains); `/dispatch <id>`
  formalizes solo mode with claim guards (completed/in_progress reported,
  unmet deps → needs-you, id beats a batch flag); `--count N` /
  `--unlimited` run an in-session sequential batch of the same settled
  per-goal cycles (Phase 0/1 once; per-goal report line + heartbeat, each
  cycle = one fire; a blocked goal doesn't stop a batch; the budget ALWAYS
  outranks flags — effective cap = min(flag, budget); an environment brake
  stops the batch on two consecutive infrastructure-shaped failures, skipping
  the second futile repair spawn; v8.3.0: the count meters CLAIMS — a Phase 1
  settle neither consumes nor licenses one, closing a real `--count 1`
  two-goal leak — and window-timed attended drains, `--unlimited` right
  after a limit reset, are the primary throughput pattern). The implementer status
  contract adds NEEDS_CONTEXT, and a BLOCKED escalation ladder runs before
  any goal blocks (each rung once, never a same-model-unchanged respawn:
  answer-context re-spawn → one stronger-tier re-spawn for
  capability-shaped blockers on medium/light-stamped goals → too-large /
  wrong-contract → contract-defect route → else block; ladder re-spawns
  continue from the current branch state). The repair brief gains
  receiving-review discipline: verify-then-fix, rebut-with-evidence (the
  orchestrator adjudicates — confirmed-false findings drop from the re-check,
  upheld ones return as open failures), covering tests re-run and appended.
  v10.0.0 (the smooth-drain release, forensics-backed 2026-08-06 — 19 real
  sessions audited): flagless = drain; the per-goal cycle is NEVER a
  confirmation point (invented permission-asks like "want me to run the
  repair?" are compliance misses); SETTLE TRIAGE closes the completion leak —
  every concern/out-of-scope finding/"needs a new goal" item is repaired,
  dismissed with reasoning, or captured as a committed line in
  `docs/goals/inbox.md` (dispatch appends, define-goal converts and removes;
  capture-only, no statuses — status-only-in-index holds); the implementer's
  fresh-check defaults to ONE medium-tier contract-conformance lens (full 2–3
  panel only for >3-file / test-logic / architecture diffs); repair round 1
  warm-resumes the goal's own implementer where the harness supports it (fresh
  spawn else — and on Droid); and the skill went on a diet — parallel mode, the
  implementer brief, and escalation/repair now live in
  `skills/dispatch/references/*.md`, Read on demand (SKILL.md ~850→ resident
  core only). define-goal v10: `touches:` is REQUIRED on recon-backed
  feature/bug goals (red-team contract-blocking; greenfield opt-out via a
  Context note) and a new Inbox-intake section converts dispatch's captured
  follow-ups into real goals (batch mode at ~5+, converted lines deleted in
  the same commit as the index entry). v11.0.0 (the plan release): a flagless
  drain AUTO-PARALLELIZES — when `config.parallel` exists (standing opt-in),
  the harness is Claude Code, and ≥2 ready goals are co-schedulable, the drain
  runs `--parallel` waves (K = `config.parallel.max_lanes`, else 2; admission
  control and the integration lock unchanged); new `--serial` flag forces
  one-at-a-time. CONCERNS DIET: DONE_WITH_CONCERNS is legal ONLY for a concern
  qualifying the goal's own contract — honored scope boundaries and
  pre-existing failures go to the report file, discovered follow-ups to a
  `Follow-ups:` report heading that settle triage captures (measured pre-v11:
  ~30 % of reports carried the status, mostly scope discipline reading as
  unfinished work). PLAN AWARENESS: the implementer brief anchors on the
  goal's Acceptance criteria (old files' Goal-contract section = same
  content), Reads the goal's linked plan before starting, and treats a plan
  Open-question the goal trips over as a CONTRACT_AMBIGUOUS stop; on a
  plan-backed PASS the settle commit checks the phase off in the plan
  (display mirror only — index.yaml stays the sole status authority; Phase 0's
  doctor pass re-syncs drift plan-follows-index, `chore(goals): plan-sync`).
- **goals-status** (v5.2.0; simplified in v6.0.0) — read-only view of the
  docs/goals queue. Prints
  every OPEN goal — `in_progress`, `blocked`, `not_started` — with its title and
  a one-line brief (the goal file's `## Outcome (plain language)` paragraph),
  grouped in that order and id-sorted within a group; `completed` goals are
  hidden (only counted, including `archive.yaml`). Blocked goals show their
  index `reason`; a `not_started` goal waiting on an unfinished dependency shows
  what it waits on. ONE view — the `--compact`/`--json` modes and the
  `--self-test` flag were cut in v6.0.0 (zero callers; pytest already runs the
  suite). Ships `scripts/goals_status.py`, PyYAML-only: factory-doctor already
  treats a missing PyYAML and a malformed index as BLOCKERs, so v6.0.0 dropped
  the ~80-line hand-rolled fallback rather than ship a second, weaker YAML
  reader. Failure is split deliberately — an unreadable **index** exits 2 with a
  `/factory-doctor` pointer and prints nothing (a partial queue read is worse
  than none), while one unparseable **goal file** degrades to `(untitled)` and
  never takes the view down. SKILL.md resolves the helper in ONE bash block
  (`$CLAUDE_PLUGIN_ROOT`, else a `find` over `~/.claude/plugins`); the old
  brace-glob chain aborted under zsh with `no matches found`. Strictly
  read-only — never claims, changes, or implements a goal (that's
  `dispatch`) and never writes `index.yaml`.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs;
  names `docs/goals/index.yaml` the canonical factory ledger. Includes
  usage-limit proofing (Step 5; rewritten v8.3.0 per the owner's 2026-07-28
  no-fast-mode / no-headless decision): subscription 5-hour/weekly limits
  kill in-session loops with no hook fired, and the rail is now WINDOW-TIMED
  ATTENDED DRAINS — `/dispatch --unlimited` (or `--count N`) started right
  after each limit reset, timed via statusline `rate_limits.*.resets_at`
  (a `StopFailure` (rate_limit) hook stays an optional mid-turn death
  signal); the prior cron/launchd → `claude -p "/dispatch"` rail is retired,
  and `/loop` remains an in-window cadence tool that dies at the limit.
- **factory-doctor** — one-pass preflight/doctor for a repo + machine:
  checks software, gh auth + scopes, the git working tree, CI, queue
  state, and loop health (stale claims, underspecified goals, and
  `limit-resilience` — WARN when a repo's loop demonstrably fires but has no
  usage-limit rail: no `StopFailure` hook, no pre-existing scheduler; its fix
  text recommends the v8.3.0 window-timed attended drain, never headless);
  aggressively auto-fixes everything local (scaffolds the queue,
  strips deprecated v3 config keys — `merge`/`wip`/`execution`/`autonomy` —
  from a stale `index.yaml` so v3-era projects stop silently running dead
  config under the v4 model) and
  reports remote/CI issues with exact fixes. Ships `scripts/doctor_checks.py`
  (read-only probe, `BLOCKER|WARN|FIXED|INFO`, exit 0/1/2). The v4 sequential
  model commits directly on the local branch, so there is no merge allow-rule
  to provision — the gate is local. The probe checks settings in `.claude/`.
## Queue design invariants (research-backed; one-goal-at-a-time dispatch model, 2026-06-28; batch flags 2026-07-24)

- **One-goal-INTEGRATES-at-a-time dispatch model** (v4.1.x; restated for
  v6.1.0's batch flags; restated precisely in v9.0.0 — the invariant was
  never "one per run", and v9.0.0 shows it was never about build concurrency
  either: it is "at most one goal integrates at a time, the branch only ever
  advances to gate-verified trees, every verdict rendered on the tree the
  branch is about to become"): serial mode (default) works ready goals
  strictly sequentially,
  committing work DIRECTLY on the branch that's checked out — no PRs, no
  remote branches, no worktrees. A flagless
  run DRAINS the queue since v10.0.0 (v6.1.0–v9.x it worked one goal);
  `--count N` caps the run at N of the same fully-settled cycles (each goal claims → gates
  → settles before the next claim; budget outranks flags); `--parallel [K]`
  (v9.0.0, Claude Code only; since v11.0.0 a flagless drain auto-enters lane
  mode when `config.parallel` exists and ≥2 ready goals are co-schedulable,
  `--serial` opting out) adds lane-model build concurrency behind the
  SAME serialized, locally-gated integration (see the dispatch bullet above —
  admission control, in-lane gate, integration lock, fast-forward-only
  branch movement; the v3 scar covered PR/CI/remote integration machinery,
  none of which returns). Each
  goal is bracketed by two anchors: `anchor` (the pre-claim clean HEAD) and
  `gate_base` (HEAD right after the claim commit). The implementer commits on
  the branch; then the orchestrator runs the LOCAL gate over the
  `gate_base..HEAD` diff — an independent second-view review (one fresh
  read-only adversarial reviewer for any non-trivial diff, v5.1.0) plus
  `pg_validate.py` plus the repo's `config.verify`
  commands — and that local gate is the ONLY merge gate. PASS → squash the
  goal's commits into one `feat(goal NNN)` commit + `completed`; FAIL →
  `git reset --hard gate_base` + `blocked`. CI, where the repo has it, is a
  NON-BLOCKING post-push observation surfaced under needs-you, never a gate.
  `/loop /dispatch` advances the queue by repeating the same one-goal cycle
  across fires; a batch flag repeats it within one run.
- Status lives ONLY in `index.yaml`, never in goal-file frontmatter —
  dual-write drifts. Goal files are immutable contracts, `define-goal --amend <id>` the
  sole exception: immutable to implementers and while a goal is claimable, editable only
  by an amend on a `blocked` goal, which repairs the defective criteria in place, records
  a one-line amendment note, and requeues via `chore(goals): amend <id>`.
- Statuses: `not_started | in_progress | completed | blocked` — blocked
  (with reason) is required to avoid re-dispatch livelock. `completed`
  only when the gate has PASSED and the goal's commit is on the branch.
- `index.yaml` `config:` block: `base` (the branch goals are worked on;
  per-goal `base:` override allowed), `model` (inherit|heavy|medium|light —
  the repo-wide DEFAULT execution tier for code agents dispatch spawns;
  legacy opus/sonnet/haiku values read as heavy/medium/light aliases; each
  goal's frontmatter `model:` — stamped by define-goal from its
  contract-tightness rubric (heavy default for features/bugs since
  v6.2.0) — overrides it per goal, and the orchestrator and review agents
  always stay on the session model; the depth-vs-limit trade), repo-wide
  `skills`, `verify` (the ordered local
  build+test commands the gate runs after each implementer), and `budget`
  (optional; `max_goals_per_session` + optional `max_iterations` — a simple
  cap on cumulative spend across repeated dispatch fires; absent = no loop cap).
  Defaults: repo default branch, inherit, no extra skills,
  repo-detected verify commands, no budget.
- Goal frontmatter `type: bug|feature|chore` shapes the contract: bugs
  always lead with a failing-test-reproduces-root-cause criterion (all
  recon hypotheses recorded); features must fill Out of scope; chores
  prove "no behavior change" (suite green before and after) plus one
  mechanical check.
- Claim protocol is LOCAL: every status write is flip ONE entry → commit
  (`chore(goals): claim|complete|block|archive <id>` from dispatch, plus
  define-goal's `amend <id>` requeue of a blocked goal). One entry per commit,
  status-only-in-index; no push, no push-arbitration — the single session
  owns the branch. NNN minting is local too (a collision renumbers the NEW
  goal only; never renumber existing goals).
- Skills mandates come in three layers: method skills (writing-plans,
  TDD, verification-before-completion, and a lightweight subagent-driven
  verifier/reviewer loop for non-trivial work) hardcoded in dispatch's brief;
  repo skills in `config.skills`; goal-specific skills in goal
  frontmatter `skills:` (populated by define-goal from actually
  available skills).
- Recon (define-goal) runs BY DEFAULT before any goal touching an existing
  system: investigate-first via parallel read-only subagents is not
  optional — "the description sounds clear" is the failure mode it replaces;
  skip only for genuinely greenfield or one-liner wants. Reaches the system
  wherever it lives (local checkout, separate repo, a host you connect to, a
  service/DB), told to each subagent, never hardcoded. Recon search subagents
  run on the medium tier (v6.2.0, owner routing decision 2026-07-24 — gather
  is strong-tool-use work; the prior always-inherit rule guarded against
  shallow recon, and that guard now lives in the gather/judge split instead).
  On Claude Code use the `general-purpose` type with `model: sonnet` and
  never the built-in Explore type (its model cannot be pinned); on Droid use
  `explorer` with `complexity: medium`. Strictly read-only either way. The
  synthesis/judgment agent — and the contract writing itself — ALWAYS stays
  on the current session model; a per-run explicit user ask is the only
  override for the gather tier. `config.model`
  governs only code-writing agents, never recon. (Recon stays plain parallel
  subagents, NOT a Workflow: 2–4 agents is below the workflow scale threshold
  and a workflow can be disabled on a user's machine — define-goal batch mode
  is the only place that conditionally uses Workflow.)
- Workflow tool only where the docs' thresholds say it wins: define-goal
  batch mode at ~5+ items (drafts in script variables, approval table
  gates file writes). Dispatch implementers may use workflow mode only
  for bounded read-only fan-out or review inside a single goal; they are NEVER
  workflows for parallel code-writing or cross-run state. The branch commits +
  the two-anchor rollback are the recovery path. The tool needs CLI ≥2.1.154 and
  can be disabled, so skills never assume it.

History note: this repo was previously `mcp-do`, a stdio MCP server
wrapping external coding CLIs (removed in v1.0.0 at ac2bd7c). The
**wish** skill (wants → GitHub issues) was retired in v2.0.0 on
2026-06-12 — the docs/goals file queue replaced GitHub issues as the
work queue (issue bodies cap at 65,536 chars; labels needed per-repo
bootstrap). The v3.x model — one isolated `goal/<id>` worktree PR per
goal, parallel `wip` implementers, an optional herdr spawn substrate,
and `merge: auto` integration gated by a deterministic + optional-LLM
validator before a `pg_safe_merge` wrapper — was replaced in v4.0.0
(2026-06-27) by the sequential, local-gated, direct-to-branch model
above. Two real autonomous `/loop /dispatch` runs motivated the change:
on a website repo and on a tax-filing app, the per-goal PR/CI/worktree
churn produced pile-ups of unmergeable PRs and orchestrator livelock —
the loop burned tokens shepherding PRs that never merged. The v4 model
deletes that machinery (worktrees, PRs, the merge wrapper, herdr, the
multi-stage merge gate) in favor of working the branch in place behind
a local gate. The **telegram-message** skill (v4.11.0 → v4.14.0) — a bot
DMing the owner on errors/limits/waiting/completion — was sunset in v6.0.0
on 2026-07-17 along with `hooks/hooks.json`, the repo's only hook bundle,
and dispatch's `active` fire marker (written every fire; the notifier was
its only reader — the heartbeat, which factory-doctor and the cross-fire
brake actually use, is a separate file and stays). Git history has every
prior model if ever needed. Dual-CLI history: v4.x carried Droid (Factory
CLI) support as dual-branch prose + a `config.droid_models` mapping; v5.0.0
(2026-07-11) removed it entirely (Claude-Code-only); v7.0.0 (2026-07-25)
restored Factory Droid as a first-class harness on the tier architecture —
one harness-neutral heavy/medium/light vocabulary plus one mapping block per
skill, all Droid claims live-verified (spec:
docs/superpowers/specs/2026-07-25-droid-dual-target-tiers-design.md).
Three sibling plugins were removed in v8.0.0 (owner decision 2026-07-25):
**html-artifacts** v1.0.2 removed, **autoresearch** v1.2.0 removed, and
**human-writing** v1.0.2 removed — `pragmatic-growth` now
ships the goal factory alone. Their trees are deleted, not deprecated in
place; `git show v7.0.0:plugins/<name>` recovers any of them intact.

## Structure

```
.claude-plugin/plugin.json        # root flywheel plugin manifest — the ONLY plugin
.claude-plugin/marketplace.json   # marketplace — name: pragmatic-growth, lists flywheel alone
agents/<name>.md                  # three flywheel plugin agents — read-only factory review roles: gate-reviewer, fresh-check, contract-red-team (v5.4.0)
skills/<name>/SKILL.md            # six flywheel skills (ideate, define-goal, dispatch, goals-status, loop-architect, factory-doctor)
skills/<name>/scripts/*.py        # dispatch/pg_validate.py (local gate), factory-doctor/doctor_checks.py, goals-status/goals_status.py (read-only queue view)
CHANGELOG.md                      # canonical, git-tracked version history
README.md                         # short public overview (what it is, install, quick start)
```

There is no website. The public landing/docs site
(`public/`, `wrangler.jsonc`, flywheel.pragmaticgrowth.com on Cloudflare) was
DELETED on 2026-08-12 by owner decision — GitHub is the only surface now.
`git show v11.0.0:public/index.html` recovers it if ever needed. Never
re-add a site, a deploy config, or a docs-sync mandate without an explicit ask.

## Rules

- **Skills-first (formerly skills-only).** Don't add MCP servers, commands,
  agents, or hooks here without an explicit ask. ONE exception to date: the
  three root `agents/` definitions (the factory's read-only review roles,
  owner-delegated decision 2026-07-16). Keep it minimal: plugin agents
  must stay read-only-by-tools on BOTH harnesses (no Edit/Write/Create/
  ApplyPatch/Agent/Task; the allowlist names both shell tools `Bash` +
  `Execute` since each harness silently drops unknown names), pin no
  `model:`, carry
  narrow non-auto-triggering descriptions, and every skill that spawns one keeps
  a generic-type inline-brief fallback (`general-purpose` on Claude Code,
  `worker` on Droid) so nothing breaks where plugin
  agents are unavailable. A new hook or agent needs the same explicit ask.
  (The repo carried a second exception — `hooks/hooks.json` for the
  `telegram-message` notifier, owner decision 2026-07-07 — from v4.11.0 until
  the v6.0.0 sunset removed the skill and the hook bundle; flywheel ships no
  hooks again.)
- **Portability.** Skills must not contain user-specific absolute paths
  (`/Users/...`) for either harness. They run in arbitrary repos; script
  resolution goes `$CLAUDE_PLUGIN_ROOT` (Droid aliases it) → `~/.claude/plugins`
  glob → `~/.factory/plugins/cache` glob.
- **This repo is the single source of truth.** The plugins are installed
  user-scoped from the `pragmatic-growth` marketplace; the former
  user-level copies in `~/.claude/skills/` were deleted on 2026-06-10.
  Root flywheel skill edits land here, bump the root `plugin.json` version,
  push, then
  refresh with `/plugin marketplace update pragmatic-growth` (Claude Code)
  and `droid plugin marketplace update` + `droid plugin update` (Droid).
  There is one plugin and one version — the root `plugin.json`.
- **Push every time — on every completion, the FULL tree (owner decision
  2026-07-14).** Pushing to GitHub (`origin main`) after committing is
  pre-authorized — always push without asking. Whenever you complete a unit of
  work (a fix, a plugin, a doc change), commit AND push before treating it as
  done; keep everything in the remote. End every turn with a fully-pushed tree:
  no modified or untracked files left dangling (commit them, or say why one
  can't be), no unpushed commits, no unpushed tags — `git status` clean and
  `main` in sync with `origin/main`. The only files that stay local are the
  gitignored maintainer config (`CLAUDE.local.md`, `.claude/settings.json`) and
  tool caches — never force-add those. The installed plugin refreshes from
  GitHub, so an unpushed commit is an unshipped skill.
- **Internal docs are tracked and pushed.** Planning/design artifacts under
  `docs/` (specs, plans, research) are a normal tracked directory as of
  2026-07-01 — commit and push them with the rest. The remote is **public and
  permanent**, so the one hard guard (enforced by the `pre-push` hook) is **no
  secrets/credentials**, and stay mindful of real client/project names in any
  committed file, message, or history. (`CLAUDE.local.md` and
  `.claude/settings.json` remain gitignored local maintainer config.)
- **Validation.** After changing plugin structure or manifests, run the
  `plugin-dev:plugin-validator` agent before committing.
- **Skill edits are tested.** New or changed skill mechanics get a
  subagent dry-run (scenario + "cite the section that decides each
  answer") before shipping; close every flagged ambiguity. For
  compliance-critical rules, add a RED baseline — run the same scenario
  against the pre-change text (`git show HEAD:<file>`) and confirm the old
  text decided it differently or left it undecided, so the rule is proven to
  change behavior, not just read well (adopted from superpowers'
  RED-baseline doctrine, 2026-07-17).

## Docs & releases (deliberately minimal — owner decision 2026-08-12)

There is no website and no full-doc-sync ritual. A change updates the docs it
actually invalidates, nothing more.

- **README stays SHORT.** It is a public overview only — what flywheel is,
  install, quick start, the six skills in one line each, the queue/gate/config
  shape. Update it ONLY when one of those user-facing facts changes (a skill's
  purpose, invocation, install command, or the config model). Internal
  mechanics, rationale, and history go in `CLAUDE.md`/`AGENTS.md`, never in the
  README. Do not grow it back into a manual — brevity is the spec.
- **Version bumps: `plugin.json` + `CHANGELOG.md` + tag + release. That's all.**
  `CHANGELOG.md` is the canonical, git-tracked history (never delete history):
  add a `## [X.Y.Z] — <date>` block with a commit link. Then an annotated tag on
  the bump commit (`git tag -a vX.Y.Z <sha> -m "…"`, `git push --tags`) and a
  GitHub Release generated from that changelog section, not the tag message:
  `gh release create vX.Y.Z --title "vX.Y.Z — <headline>" --notes-file <section> --verify-tag --latest`
  (`--latest` only on the newest version; backfills use `--latest=false`).
  Releases are how the version history is browsed now that the site is gone.
  Bump the README badge only when you're already editing the README.
- **Bump only for real skill changes.** A docs-only or changelog-only edit does
  NOT need a `plugin.json` version bump — installed plugins don't depend on it.
