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
`flywheel` v12.0.0.
(The `html-artifacts`, `autoresearch`, `human-writing` plugins were **removed**
from the marketplace in v8.0.0, owner decision
2026-07-25 — the marketplace is the goal-factory only now; git history keeps
them recoverable.) No MCP
servers, no commands, no build step, and ONE hook bundle — root `hooks/`, the
opt-in factory event log added in v13.0.0 (owner ask 2026-09-01), inert until
`~/.local/state/pg-factory/` exists. TWO scoped exceptions to the
skills-only rule — that hook bundle, and SIX plugin agent definitions under root
`agents/`: the
factory's read-only REVIEW roles `gate-reviewer`, `fresh-check`,
`contract-red-team` (v5.4.0, owner-delegated decision 2026-07-16 after
transcript forensics on real dispatch runs showed hand-composed review briefs
drifting across fires) plus the read-only RECON/orientation roles
`recon-locator`, `recon-analyzer`, `recon-patterns` (v11.1.0, owner-delegated
decision 2026-08-12 — adapted from HumanLayer's riptide codebase agents for the
same anti-drift reason: recon briefs were hand-composed per session; spawned by
define-goal recon, ideate orientation, and implementer exploration on Claude
Code with the medium tier — `model: sonnet` — passed at spawn; on Droid recon
stays on `explorer` + `complexity: medium`, custom-droid + complexity being
unverified). Each carries the role
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
for review roles.
`flywheel` has nine skills under root
`skills/` (four ship deterministic Python helpers in `scripts/`), forming a
plain-language → autonomous-execution pipeline around a file-based goal queue
(`docs/goals/` in target repos): `/ideate → /define-goal → /dispatch →
/goals-status`, with `loop-architect` and `factory-doctor` as the rails,
`process-inbox` closing the loop from dispatch's captured follow-ups back into
define-goal, `factory-report` as the cross-repo performance view over the whole
estate (v13.0.0), and `show-me` as the one pipeline-adjacent explainer (v11.8.0,
owner ask 2026-08-18 — adapted from HumanLayer's show-me). There
is no `plugins/` directory — the repo root IS the flywheel plugin.

- **ideate** (v11.0.0 — rewritten around the PLAN, the factory's design tier,
  after the 2026-08-12 riptide/RPI deep-read + estate forensics; originally
  adapted from superpowers' brainstorming, 2026-07-24) — the pipeline's front
  door: explores a fuzzy idea and writes an approved plan at
  `docs/goals/plans/YYYY-MM-DD-<topic>.md` (template:
  `skills/ideate/references/plan-template.md`; replaces the v6-era design
  brief — existing `docs/goals/briefs/` links stay valid). Context orientation
  first (1–2 read-only subagents max — the plugin recon agents when listed,
  else `general-purpose`, either way the medium tier `model: sonnet` on Claude
  Code; `explorer` + `complexity: medium` on Droid),
  then a VERTICAL-SLICE scope check (each piece independently verifiable
  end-to-end; "if a piece cannot be verified without a LATER piece existing,
  it is not a slice"; pieces map 1:1 onto goals + `depends_on`). Exploration
  dialogue (v11.4.0, owner decision 2026-08-13 — ideate is the ONE skill where
  asking is the tool; the factory-wide "don't ask me questions" diet stands in
  every OTHER skill, and the prior at-most-ONE-round cap is retired here):
  PROGRESSIVE brainstorm-style rounds — plain owner-language questions only,
  each an AskUserQuestion with 2–4 options, recommended option first,
  multiSelect where non-exclusive; one short round (1–2 questions) at a time
  with no fixed cap (stop when answers stop changing the design); an answer
  that opens territory the current context doesn't cover triggers fresh recon
  (step 1's agents) BEFORE the next round or any design writing. TECHNICAL
  forks stay out of the dialogue: they become the plan's Open-questions
  section (options + recommendation each; ONLY the owner resolves; "go with
  your recommendations" resolves all at once with provenance recorded;
  resolved questions keep their why forever), and the plan presentation stays
  the single approval touch. The plan is code-shaped at
  signature altitude (exact signatures with bodies elided, file-tree diff,
  call flows only where non-obvious — never function bodies) with
  takeaway-stating headers. Dispatch checks phases off as their goals
  complete, so the plan doubles as the progress view. HARD GATE: its only
  terminal states are invoking define-goal with the approved plan or the user
  parking the idea — it never writes goal files, index entries, or code.
  Single-goal outcomes stay fileless; already-shaped wants skip it entirely;
  re-invoking on a planned idea iterates the same plan file. v12.4.0 — THE PLAN
  IS MEASURED AS A WHOLE, AND ITS STANDARD IS RATCHETED. At 3+ slices step 2
  mints one extra phase, the OUTCOME CHECK: a verification-only final goal that
  builds nothing, depends on every other phase, and runs every bullet of
  `## What will be true when done` — so `status: done` comes to mean the outcome
  check PASSED, not merely that the pieces got built, with no new dispatch
  machinery (phases already map 1:1 onto goals). Outcome bullets stop being inert
  prose: each names an exact command (or keeps the `**needs independent review**`
  marker), each must FAIL at the plan's base commit (a check that already passes
  is measuring a piece), each must be a COMMITTED test the repo's suite discovers
  (an ad-hoc command run once at settle leaves the stamp resting on evidence that
  went stale the moment the next phase landed), and each must DRIVE a real surface
  rather than read source — which is what makes the owner-resolved decision to let
  implementers see the plan safe, since the only way to pass such a check is to
  build the behavior. And ideate is now a RATCHET SITE alongside define-goal: on
  iteration, outcome-bullet edits are classified against
  `git show HEAD:docs/goals/plans/<file>.md` and a weakening stops for the owner
  (removing or renaming the section counts). This closes the back door the
  goal-file ratchet alone leaves open — soften the plan, contract the goal
  honestly from the softened text, and every individual comparison sees nothing.
  Three residual routes are named rather than implied: a plan edited outside
  ideate after its outcome goal is contracted (red-team item 15(b) is the
  backstop), a fresh plan file duplicating a topic, and a weakened TEST BODY under
  a byte-identical command — no text ratchet can see that last one.
  v12.3.0 (goal 013,
  with goals-status): an UNSHAPED LIST is this skill's front door too — "I have
  N issues/items, where do I start?" is one idea at plan altitude, not a
  define-goal batch dump: orient once over the whole list, cut it into vertical
  slices (items may merge or split in the cut), and write ONE plan whose phases
  map 1:1 onto the goals define-goal will contract; batch mode is for items
  already shaped enough to contract individually. v11.3.0 (owner
  decision 2026-08-13): when the session's tools include the Artifact tool
  (built into Claude Code ≥2.1.183, needs a claude.ai login, can be disabled,
  absent on Droid/headless), step 5 ALSO publishes the plan as a designed
  artifact page — the owner's reading surface for the approval touch — with
  the URL recorded in plan frontmatter `artifact:` so iterations update the
  SAME page; ONE publish per approval touch, approval stays in-conversation,
  the markdown plan file stays canonical, and dispatch/define-goal never
  republish the page (deliberately NOT a live twin — the drift/ceremony
  analysis is in the 2026-08-13 session; riptide's own precedent is one-shot,
  size-gated HTML, never a living twin). Chat presentation is the norm and
  the fallback wherever the tool is absent. Grounding: the
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
  oversized contract). v12.3.0 adds a count trigger the atomicity note never
  downgrades: a `touches:` list hitting ≥3 of the three product bands —
  migration/schema (`**/migrations/**`, `**/supabase/**`), API/server
  (`**/apps/api/**`, `**/server/**`), web/UI (`**/apps/web/**`,
  `**/frontend/**`) — is contract-blocking Size even with an atomicity note
  (`docs/goals/**` never counts; product docs are a fourth band but the trigger
  stays ≥3 of the three product bands; the fix is a `depends_on` chain of thinner
  vertical slices; the note still downgrades only the qualitative two-band
  span; field-grounded 2026-08-28 in a 16-glob four-band goal that passed
  every check and then needed touches-closure amends). v13.0.0 adds the second
  no-advisory count — COUNT THE UNITS, NOT THE CRITERIA: one criterion (or the Outcome)
  naming 3+ PARALLEL new surfaces of the same kind (screens, routes, endpoints, jobs,
  commands, tables — none depending on another) is N goals in one criterion's clothes,
  contract-blocking, the enumeration itself being the split seam; two is a pair and
  stays legal. Field-grounded 2026-08-31: two console-wave goals passed every existing
  Size check — one subsystem, two bands, five and six criteria — while one criterion
  each read "Documents, Mailroom, and DocuSeal screens" and "monitoring, NAICS, R2
  objects, Trustpilot, legacy payments"; both ran healthy with no hang and no thrash and
  still took 132 and 119 minutes against a 29-minute median that day.
  `agents/contract-red-team.md` updated in lockstep. v11.0.0 (the plan release, forensics-backed
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
  (spend, data loss, irreversible/externally-visible). v11.6.0 (the 2026-08-16
  drain forensics — every one of 10 blocked goals across two repos was a
  contract-authoring defect, not a work failure): a mechanical CONTRACT
  REALITY CHECK runs before the red-team on every queued draft — `touches:`
  closure (every path the contract's own text requires, incl. plan files and
  mandated regens, must be covered), `touches:` existence (every glob matches
  a real path or a declared new file), `acceptance:` runnability (a named
  test path must be reachable by the runner AS WRITTEN — config include,
  `--config`, package filter), Constraints scoping (no unsatisfiable pasted
  boilerplate), and before/after criteria naming their BEFORE; the red-team's
  Command-reality/Gate-fit items carry the same teeth plus a new
  Constraints-reality item (`agents/contract-red-team.md` updated in
  lockstep), and inbox intake refuses caption/comment-wording items outright
  (fix-directly-or-drop; a measured caption-class goal bought no coverage).
  v12.0.0 (the 2026-08-19 forensics — ~37 needs-you items in 3 days, ~3 genuinely
  the owner's): the reality check grows to EIGHT — Drainability (no criterion may
  need a human's word mid-goal; the old recon rule that MANDATED "stop and confirm"
  gates on irreversible criteria-path actions is inverted to a split rule — the
  reversible half queues, the irreversible act goes to the owner with the evidence;
  two real goals blocked by construction on that shape), Premise (the justifying
  claim verified against a primary artifact, dated, refutation-tested for bugs — a
  misread aggregate became a goal that burned a heavy run disproving itself), and
  acceptance fail-at-base/pass-at-head (live-network reports are evidence, never
  acceptance; not-yet-true capabilities are `depends_on` priors). Amend mode gains
  the DRAIN WAIVER (dispatch's Self-heal invokes it in-run: red-team unchanged, no
  question rounds, confirmation waived, owner forks still stop — the blanket
  "never auto-amend" is retired) and RETIRE (premise disproven / already true →
  `chore(goals): retire <id>`, entry to archive with reason, file to done/ — there
  is nothing to amend). Inbox intake also refuses aggregate-only premises (KEEP
  `premise unconfirmed`) and verifies named mechanisms live. Red-team items 11–12
  (Drainability, Premise) added in lockstep.
  v12.4.0 — THE RATCHET (from Factory's 2026-08-27 study: an agent stops early
  because it authors its own definition of done, and a standard that can soften
  stops measuring): an amend may only make a contract stricter or more correct,
  never easier. Amend step 4 classifies every edit against
  `git show HEAD:docs/goals/<id>.md` on a named taxonomy — weakening (criterion
  deleted and not replaced, threshold loosened, a runnable command traded for a
  vouched-for assertion, a drivable-surface check traded for a code-reading one,
  a before/after criterion that lost its BEFORE, a removed `needs independent
  review` flag, `touches:` narrowed past what the criteria still require) STOPS
  FOR THE OWNER, drain waiver or not; tightening/repair proceeds unattended as
  before, and the amendment note carries a `ratchet:` field naming which it was.
  RETIRE is under it too as the largest possible weakening — under the waiver its
  disproving evidence must be a command output or quoted primary artifact, never
  the agent's own reasoning. Reality check item 10 (amend-only) and red-team item
  15 enforce it, and the header count — stale at "eight" while listing nine since
  v12.1.0 — is corrected to "ten". The waiver deliberately cannot reach any of it:
  self-heal is the one path where nobody is watching, so it is the one path where
  a softening standard would go unnoticed. The plan-backed fast path also
  contracts a 3+-phase plan's FINAL phase as its outcome check (`type: chore` via
  a new type-shape exception admitting a verification-only goal with no
  no-behavior-change proof; `depends_on` every other phase), and warns that a
  `-k` selector exits 5 on no match, so any test name an outcome bullet selects
  must be pinned by a criterion in the goal that CREATES it.
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
  batch mode (both harnesses since v12.5.0; default K=2, cap 4) builds provably-disjoint
  goals concurrently in disposable LOCAL worktree lanes
  (`~/.local/state/pg-dispatch/<SLUG>/lanes/<id>`, local branch `lane/<id>`,
  deleted at settle) under admission control (disjoint `touches:` globs — a
  goal without `touches:` is never co-scheduled; no dep path; conflict
  domains like lockfile/migrations/CI/config always exclusive; same base)
  while INTEGRATING strictly one at a time: rebase lane onto branch HEAD,
  re-run Arm A on the integrated lane tree, squash, fast-forward the branch
  (v11.4.1, from two real field failures 2026-08-13: collapse IN the lane +
  `git merge --ff-only` only — `git merge --squash` is banned, it re-merges
  what the rebase settled and put conflict markers into a committed
  index.yaml; `docs/goals/**` in a lane range is always restored to the
  branch copy, a conflict-markered tree is never committed, and lanes copy
  needed gitignored local files like `.dev.vars` at creation) —
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
  one-at-a-time per run, and `config.parallel.auto: false` (v11.2.0) is the
  persistent opt-out for pre-v11 queues that configured `parallel:` when it
  only tuned the explicit flag. CONCERNS DIET: DONE_WITH_CONCERNS is legal ONLY for a concern
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
  v11.6.0 (the 2026-08-16 drain forensics: high completion but pile-up —
  ~1.5–2.5 inbox lines per completed goal, mostly keep-grade nits; drains
  killed by a shared-limit/model-pin infra death; three false agent-dead calls
  in one run; two same-checkout session collisions): SETTLE-TRIAGE CAPTURE BAR —
  a fourth disposition, Report-only, takes latent/unreachable-today findings,
  fail-safe residuals, contract-mandated tradeoffs, and caption/wording nits
  (they live in the report file); only live defects, genuinely new work, and
  owner decisions earn an inbox line. PIN-FAILURE FALLBACK — a spawn error
  naming the model/provider (`unknown provider for model …`) retries ONCE with
  the pin omitted (session model), never burning transient respawns on an
  error that reproduces by construction, never a lighter pin. DEATH NEEDS
  EVIDENCE — an agent that has not returned is never declared dead on one
  silent probe: two checks, real minutes apart, zero new commits between.
  CHECKOUT LOCK — Phase 0 checks/writes `~/.local/state/pg-dispatch/<SLUG>/lock`
  (~2h staleness; fresh lock → stop, needs-you `checkout busy`; refreshed with
  the heartbeat, deleted at terminal stops — the lock guards the TREE, the
  claim protocol still guards the queue). And the implementer brief mandates
  COMMITTING WORKING INCREMENTS after each green TDD cycle (squash makes them
  free; the uncommitted-tree death left 8 files of orphaned half-work).
  v12.0.0 — the self-healing-drain release (2026-08-19 forensics over 3 days,
  both field repos, both harnesses: ~37 needs-you items of which ~3 genuinely
  needed the owner; report lines followed perfectly but wrapped in 2,000–4,100
  chars of prose; five "say the word" closers cost ~18h idle; one 4-lane Droid
  emulation burned 293 poll calls and the account balance): SELF-HEAL — every
  run routes contract-defect blocks (new AND the existing blocked backlog)
  through define-goal's amend machinery in-run under a drain waiver (red-team
  unchanged, one amend-and-re-claim per goal per run, owner forks still stop),
  and RETIRES disproven-premise goals (`retire`, the fifth claim verb — terminal,
  archive-bound). TWO CHANNELS — `needs-you:` is decisions only; observations
  (CI red, recurring lesson, needs-independent-review, retirements) move to
  `fyi:`, and reasons cap at ~120 chars (the full text stays in index/report
  files). OUTPUT ENVELOPE — the settle turn IS the report line, the closing turn
  is line + summary + bullets and nothing else ("the fire's report" always means
  the report FILE); a plan-tool update (any harness plan/artifact status
  acknowledgement, incl. Droid's "Plan is up-to-date.") is a PRE-CLOSING action —
  allowed, but it lands BEFORE the closer so the closing turn stays the run's
  last message; the line's done/ready/blocked/total counters derive from ONE
  `index.yaml` read at settle time, never an incremented remembered count; the
  summary ends `all complete` or `outstanding: <n> for you`. DECLARATIVE STALLS
  are the permission-ask miss in statement form (incl.
  the closing turn — no offers). SHIP STEP — a terminal stop runs the repo's own
  pre-authorized publish path (every declared path the diff touched when docs
  declare more than one, reported per-service; one shipped and one not is
  `ship FAILED: partial (<service> unshipped)` under needs-you class
  `environment failure`); unshipped is not done (a run reported 21/21 done
  over 30 unpushed commits in a push-is-deploy repo). Dispatch never
  invents a deploy. Dirty trees are
  quarantine-committed and worked past (after a live-writer check), not refused.
  A user-invoked flagless drain that ends drained with inbox lines CHAINS into
  /process-inbox once (loop-guarded). Infra class widened: billing/auth/overload
  errors get the pin-omitted retry then a CLEAN settle (lock released) instead
  of a mid-wave hang; Droid `--parallel` was refused out loud (poll-loop
  emulation banned — RETIRED in v12.5.0, see below); Droid spawns pass `await: true`; a warm resume that
  replays with zero new commits disables warm resume for the run.
  v12.3.0 — the death-recovery release (2026-08-27 field analysis, both
  harnesses; twelve goals drained 2026-08-28): RESUME FROM INCREMENTS — a
  missing `STATUS:` block on a returned implementer is ITSELF the trigger for a
  new escalation rung (read `gate_base..HEAD`, re-brief ONE fresh worker with a
  `Landed so far` section, finish from current HEAD on the same claim and
  `gate_base`), never gate-then-reset, whose `git reset --hard` destroys exactly
  the increments the rung exists to recover; `Child session timed out due to
  inactivity` joins the transient infra class (ONE same-tier respawn, pin off
  only when the error ALSO names model/provider), and the rule is DEATH-MODE
  GENERIC — a second consecutive STATUS-less death re-fires the resume rung
  while the ~3-transient-respawn budget has headroom (the larger landed set is
  what makes each re-brief a changed brief), `repeated transient death` and the
  rollback firing only once that budget is spent. REPORT-FILE GATE — Arm A's
  `pg_validate.py` now enforces what the brief always claimed: a missing, empty,
  or pre-`gate_base` implementer report is FAIL_FIXABLE with no mechanical-edit
  exemption (Phase 1's "absent is fine" is the crash-recovery reviewer handoff
  only, and crash recovery regenerates a stub first so a sitting that merely
  lacked the file is not reset). CAPTURE BAR INVERTED — Report-only is the
  DEFAULT disposition (unsure lands there) and an inbox line is legal only
  carrying its `(earn: …)` token naming which of the three shapes it meets; a
  line without one is a capture that did not happen. PLURAL SHIP — every
  declared publish path the diff touched, reported per-service. CLOSER STAYS
  LAST — a plan-tool acknowledgement is a PRE-CLOSING action, and the report
  line's counters derive from ONE fresh `index.yaml` read at settle time, never
  a remembered increment. DROID LENSES — `droid exec` fresh-check commands carry
  `--enabled-tools "Read,Grep,Glob,LS,Execute"` (tool-less lenses were returning
  UNVERIFIABLE) and `not run (no fresh-context mechanism available)` is honest
  only after `command -v droid` fails (a lens erroring with `droid` present is
  `not delivered`). ONE WAIT — the Arm A join waits once then reads, repeated
  `sleep`+`ps` polling banned by name on Droid; and parallel mode drains pending
  `idle_notification` teammate pings before the closing turn (Claude-Code-only,
  never by spawning anything).
  v12.5.0 — PARALLEL LANE MODE ON DROID. The v12.0.0 blanket refusal
  (`parallel unavailable on this harness — running serial`) is retired: it banned the
  FEATURE because of the MECHANISM one run used to fake it. Field evidence settles the
  capability question the v7.0.0 no-unverified-Droid-claim doctrine left open — a
  2026-08-31 audit of `~/.factory/task-invocations.json` (Droid 0.208.2, 1,017 recorded
  Task invocations across nine repos) found routine 7–8-way CONCURRENT FOREGROUND
  (`runInBackground: false`) Task bursts, write-capable `worker` spawns among them
  running 9–14 minutes apiece (2026-08-26 aj-leads 7 workers, 2026-08-27 mfa 8,
  2026-08-28 flywheel 8). So a Droid wave spawns exactly like a Claude Code wave: K
  awaited `Task` calls (`worker`, `await: true`, `complexity:` from the tier) issued in
  ONE message, returning together — awaited never meant one-at-a-time. Everything else in
  the lane model is harness-neutral and unchanged (admission control, the in-lane gate,
  the serialized integration lock, fast-forward-only branch movement, every failure
  ruling), and flagless auto-parallel now applies on both harnesses. What STAYS banned
  everywhere is the shape the 2026-08-17 run actually used — `runInBackground: true`
  plus a `TaskOutput` poll loop (293 poll calls, 34 % of its turns, account balance
  exhausted mid-drain); foreground concurrency is its opposite: K spawns, ONE wait, zero
  polls. Two Droid-only lane rules come from the same audit: a Droid Task subagent
  INHERITS the session cwd (every recorded invocation's `cwd` equals its parent's; Task
  takes no cwd parameter), so lane briefs name the lane as an ABSOLUTE path, require
  `cd <lane>`/`git -C <lane>` on every shell call, and mandate a
  `git -C <lane> rev-parse --abbrev-ref HEAD` confirmation before the first commit; and a
  Droid subagent has no Task tool, so an in-lane fresh-check lens adds `--cwd <lane>` to
  its `droid exec` command or it reviews the wrong tree. A `git worktree add` or lane
  spawn failing on a trust/permission error (lanes live under
  `~/.local/state/pg-dispatch/`, which must sit inside a Droid trusted folder) is
  a ONE-strike needs-you `environment failure`: discard that lane, keep the goal claimed
  and work it serially, let running lanes finish, open no further lanes this run.
  Long in-lane commands are detached (`setsid <cmd> > <log> 2>&1 &`) and waited on ONCE:
  Droid's foreground shell was observed killing a long command with its process group at
  roughly a minute. Worktree lanes themselves were already field-proven on Droid — the
  banned 2026-08-17 run DID build 4 goals in real lanes off `staging`; its only defect
  was backgrounding the Tasks and polling them.
  v12.4.0 — A WHOLE-OUTCOME GAP OUTRANKS THE CAPTURE BAR. v12.3.0 made Report-only
  the default with "unsure lands here", which is right for nits and backwards for
  the one failure the plan tier exists to catch, so settle triage gains ONE narrow
  carve-out: an item that would FALSIFY a bullet of the goal's linked plan
  `## What will be true when done` is never Report-only, however unsure the
  implementer is. It carries the `live-defect` earning token by construction —
  without that the capture item's own "cannot honestly name one shape →
  Report-only" would re-route the very items the carve-out exempts — and the
  operative test is narrow: it qualifies when, if true, it would make an outcome
  bullet's COMMAND fail or a `needs independent review` bullet false; topical
  relation is not enough. Everything else stays Report-only exactly as v12.3.0 has
  it. Phase 0's plan-sync section also states what the stamp MEANS: on a 3+-phase
  plan the last phase is the outcome check, so `status: done` means it PASSED (a
  1-2-phase plan keeps the older, weaker meaning).
  v12.6.0 — THE WAIT (2026-08-31 forensics on two field `/process-inbox` runs). On
  Claude Code a spawned helper's report reaches the orchestrator only at a TURN
  BOUNDARY: the `Agent` call returns "launched", the report arrives later as a
  completion notification. Every wait the runs built out of `Monitor` sleep loops,
  blocking `TaskOutput` on those loops, and repeated `ListAgents` held the turn OPEN and
  therefore starved the delivery it was waiting for — a verifier that answered in 71 s
  was killed as stalled at 8 min, a red-team that delivered full findings at 4 min 24 s
  was killed at 5 min 58 s, and BOTH were re-run in the orchestrator's own context,
  destroying exactly the independence the spawn exists to buy (45 `ListAgents` calls and
  six sleep loops burned across the two runs). So: spawn PLAIN — `subagent_type`,
  `model`, brief, nothing else — do the independent work in hand, and otherwise let the
  turn END. `name:` is banned on every factory spawn: a named agent becomes a persistent
  session teammate reporting by MAILBOX rather than by notification (that verifier's
  verdict was accepted into the mailbox at 71 s and never surfaced; named implementers
  from earlier runs were still listed idle 5 h on) — and from inside a subagent a plain
  spawn returns its report INLINE as the tool result, which is why the same run's named
  lens panel returned nothing and had to be respawned plain. DEATH NEEDS THE TRANSCRIPT:
  a helper writes its own transcript to disk while it runs
  (`~/.claude/projects/<cwd-slug>/<session-id>/subagents/agent-*.jsonl`;
  `~/.factory/sessions/<cwd-slug>/<childSessionId>.jsonl` on Droid, child ids in
  `~/.factory/task-invocations.json`), so fresh records or a file ending mid-tool-call
  mean ALIVE and the v11.6.0 two-samples rule now names that file as its evidence. The
  ban on repeated task-status polling, previously written as a Droid rule, is now
  explicitly both-harness. Droid's awaited `Task` contract is unchanged — K spawns, ONE
  wait, results together.
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
  brace-glob chain aborted under zsh with `no matches found`. v12.3.0 (the
  front door, with ideate — goal 013): the view ends with exactly one
  `next: <command>` line the helper derives first-match from queue state — any
  open goal → `/dispatch`, else unchecked `- [ ]` lines in `docs/goals/inbox.md`
  → `/process-inbox`, else `/ideate`; an all-completed queue pointing at
  `/ideate` is the front door working, not an error. Strictly
  read-only — never claims, changes, or implements a goal (that's
  `dispatch`) and never writes `index.yaml`.
- **process-inbox** (v11.5.0, owner ask 2026-08-13 — "one command so the best
  thing is done without writing manual prompts") — the attended triage sweep
  for dispatch's `docs/goals/inbox.md` capture file, codifying the measured
  field pattern (romy 2026-08-13: 101 items → 31 goals, 20 dead lines deleted,
  3 settled by production queries). VERIFY-FIRST law: every item re-checked
  against current code by read-only subagents before any routing
  (`flywheel:recon-analyzer` else `general-purpose`, medium tier
  `model: sonnet`, on Claude Code; `explorer` + `complexity: medium` on Droid;
  clustered by file/subsystem, ~8 concurrent; measured ~20% dead rate on a
  stale inbox — evidence pointers are where verification starts, never its
  substitute), then SIX-BUCKET triage on the session model: CONVERT (folding
  rules — one-function captures fold into one goal, >2 independent findings
  per goal costs more repair rounds than it saves, caption/wording items
  never convert as of v11.6.0; handed to define-goal's inbox intake
  pre-verified, recon narrowed to
  verify-and-complete, red-team + approval unchanged), FIX-NOW (mechanical
  no-behavior-change only, at dispatch's review-skip bar judged from the diff;
  ONE `chore(inbox): direct fixes` commit gated by `config.verify` — any
  failure reverts the whole batch and demotes to CONVERT), DROP
  (disproved/gone — deleted with a one-line why in the inbox's own
  `## Triaged` ledger section), PRODUCTION-CHECK (run read-only now or hand
  the exact query to needs-you), KEEP (reason appended to the line), OWNER
  (spend/data-loss/irreversible/externally-visible — presented with a
  recommendation, never acted on; the ONLY bucket that waits for a human — no
  other question rounds). Hard boundaries: never writes goal files or index
  entries (define-goal's), never implements non-trivial work (dispatch's),
  never touches unprocessed lines. Dispatch's drained-queue pointer names it
  (`inbox: N captured → /process-inbox`). v11.6.0: KEEP is ONE-CYCLE PAROLE —
  a line stamped `KEEP <date>:` by a previous sweep skips verification and
  retires to the `## Triaged` ledger (`retired keep: <gist> — <reason>`)
  instead of being re-verified forever (a real sweep re-verified 28
  already-adjudicated lines and changed almost none); and caption/
  comment-wording items NEVER CONVERT — FIX-NOW or DROP only (the folding
  rules' caption-split clause is gone; define-goal's intake refuses the class
  too). Dispatch's v11.6.0 capture bar keeps fresh inboxes lean; pre-bar
  inboxes still carry the old mix. v11.7.0 (owner decision 2026-08-17 — "one
  command, come back to a cleared inbox"): FLAGLESS = DRAIN — a flagless run
  goes end to end in one session: verify → triage → FIX-NOW batch → convert
  through define-goal's inbox intake with the APPROVAL TABLE WAIVED (the drain
  invocation is the standing approval; red-team unchanged and never waived —
  an unfixable contract-blocking finding demotes the item to KEEP with the
  finding as reason; a true owner fork returns it to the OWNER bucket
  unconverted; assumptions go in the goal's Context, `provenance:
  inbox-drain`) → then a normal flagless `/dispatch` drain (nothing
  special-cased; older ready goals get worked too; captures appended DURING
  the drain are next sweep's input). Mid-drain permission-asks are compliance
  misses (dispatch v10's rule applied here); the report appends dispatch's
  final line before the OWNER items. `--triage-only` restores the pre-v11.7
  stop-at-handoff behavior with the approval table intact. The chaining does
  not blur boundaries — conversion and implementation still run inside
  define-goal's and dispatch's own machinery, reviews and gates unchanged.
  v12.0.0 (the 2026-08-19 forensics — the same 5 OWNER items re-presented
  across 4 sessions until one owner instruction dissolved them, 4 of 5 via a
  single read-only production query): the OWNER BAR — OWNER requires a PROVEN
  consequence, not a matching topic: run the read-only blast-radius check
  (the SELECT, the secret/bucket listing) BEFORE routing, attach it; an empty
  target is not a data-loss decision, a code edit behind the factory's gate is
  never OWNER, "for convention's sake" is CONVERT/FIX-NOW. Carried-over OWNER
  lines are RE-ADJUDICATED against the bar each sweep (parking-lot ban), a
  CONVERT item's named mechanism is verified live (a measured recommendation
  would have paged nobody), and the report is a hard envelope — counts line +
  dispatch's line + one line per OWNER item, `<O>` equal to the lines printed,
  nothing else. v12.3.0 (goal 006): the envelope also carries one P-LINE per
  unrunnable PRODUCTION-CHECK (the exact query + why), `<P>` equal to the
  P-lines printed, mirroring `<O>` — step 3 had been sending those queries to a
  report that step 7's envelope then forbade printing, so a compliant report
  could count `<P>` and show none of them; P-lines are not OWNER lines.
- **show-me** (v11.8.0, owner ask 2026-08-18 — adapted from HumanLayer's
  show-me skill) — visual explainer for the current topic: answers
  "how does X work / what talks to what / what would change" with the
  smallest view that lands the point — pseudocode, call tree, component
  tree, shallow file tree, Mermaid, or a shape-matched `diff` — prose kept
  brief. RED-baselined 2026-08-18: the unaided answer to the same question
  was ~195 words of pure prose. All output is plain markdown, identical on
  both harnesses; the ONE harness-gated option is a focused HTML page via
  the Artifact tool (same availability gate as ideate's plan artifact;
  absent → markdown in chat is the fallback, never a written HTML file —
  the upstream `.humanlayer/tasks/` artifact convention was replaced with
  this). Strictly read-only — explains, never edits code or the queue; data
  charts are out of scope (dataviz territory).
- **factory-report** (v13.0.0, owner ask 2026-09-01 — "a logging system we can
  monitor performance easily") — the read-only performance view across EVERY repo on
  the machine with a `docs/goals` queue, not one repo at a time (that is
  `goals-status`). Ships `scripts/factory_report.py` reading three sources with a fixed
  trust order: goal timing ALWAYS from the repo's own `chore(goals):` commit dates
  (retroactive, works on repos that never had logging on, and cannot be fabricated by
  an agent — the v12.7.0 audit found 43 % of stamps wrong); agent lifecycles and
  tool-call counts from the event log the plugin's hooks write to ONE machine-wide
  `~/.local/state/pg-factory/events.ndjson`; status and queue depth from
  `index.yaml`/`archive.yaml`, whose stamped durations are cross-checked against git and
  never trusted over it. Its point is the THREE FAILURE MODES, which look identical from
  outside — "the goal took two hours" — and have different fixes: RUNAWAY (tool calls far
  above normal, no gaps: a healthy worker's p90 is ~105, the threshold 300 — measured
  over 494 workers only two ever passed it and BOTH failed; mfa/105 made 1,427 calls in
  114 min with no gap over a minute, then died), HUNG (a 15-minute+ silence; inside a
  working agent the largest normal gap is ~1 min, and two field agents sat 5 and 8 hours
  silent), and OVERSIZED (healthy, evenly paced, finishes — the contract was just too
  big; the fix is upstream in define-goal, never in dispatch). All three are
  REPORTING-ONLY by owner decision 2026-09-01 ("watch first"): the thresholds come from
  one repo mix, so nothing in flywheel stops an agent on them until real data backs
  them. Publishes to the same stable artifact each run where the Artifact tool exists
  (same availability gate as ideate's plan), chat output the norm and the fallback.
  Strictly read-only — never claims, amends, or implements, and never rewrites a
  contract on the strength of a slow number.
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
  (v9.0.0, Claude Code only until v12.5.0 opened it to Droid; since v11.0.0 a flagless drain auto-enters lane
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
- Statuses: `not_started | in_progress | completed | blocked | retired` — blocked
  (with reason) is required to avoid re-dispatch livelock. `completed`
  only when the gate has PASSED and the goal's commit is on the branch.
  `retired` (v12.0.0) is the terminal disposition for a goal whose premise the
  evidence disproved or whose outcome is already true — minted only by dispatch's
  Self-heal pass or define-goal's amend flow (`chore(goals): retire <id>`: entry to
  `archive.yaml` with reason, file to `done/`, one commit); never requeued, never
  re-reported, satisfied as a dependency.
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
  (`chore(goals): claim|complete|block|archive|retire <id>` from dispatch, plus
  define-goal's `amend <id>` requeue of a blocked goal). One entry per commit,
  status-only-in-index; no push, no push-arbitration — the single session
  owns the branch. NNN minting is local too (a collision renumbers the NEW
  goal only; never renumber existing goals). v12.2.0 (owner ask 2026-08-27,
  grounded in a 4-day/91-goal timing analysis that needed git archaeology to
  compute): the claim flip stamps `claimed_at:` and every terminal flip
  (`complete|block|retire`) stamps `settled_at:` (UTC ISO-8601, seconds) on the
  same entry edit — duration metadata, dispatch-only writes, NEVER control flow
  (the stale-claim brake still counts heartbeat fires), optional on legacy
  entries, carried verbatim into archive.yaml; dispatch's report line shows
  each settled goal's claim-to-settle minutes and goals-status shows elapsed
  age on in_progress/blocked entries. Timestamps are not status, so
  status-only-in-index holds unchanged.
  v12.7.0 (2026-08-31 audit of the 58 stamped goals across four field repos against
  their own claim/settle commits: 43 % off by >2 min, 14 % by >15, one settling BEFORE its
  claim, one a full day in the future, the metric reading 67.4 h against git's 36.4 h): the
  stamp is the verbatim stdout of `date -u +%Y-%m-%dT%H:%M:%SZ` run in the same action as
  the flip — a recalled, inferred, or whole-minute value is fabricated data (whole-minute
  stamps were the tell; the repos that matched git ran the command) — and an unstamped
  terminal flip is an incomplete flip, the pre-existing-entry exemption never a blanket
  one.
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
  On Claude Code spawn the plugin recon agents when listed
  (`flywheel:recon-locator|recon-analyzer|recon-patterns`, each on the
  medium tier — `model: sonnet` — at spawn, v11.1.0), else `general-purpose`
  on the same medium tier (`model: sonnet`);
  never the built-in Explore type (its model cannot be pinned); on Droid use
  `explorer` with `complexity: medium` (never the plugin agents there —
  custom-droid + complexity unverified). Strictly read-only either way. The
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
agents/<name>.md                  # six flywheel plugin agents — read-only review roles: gate-reviewer, fresh-check, contract-red-team (v5.4.0) + recon roles: recon-locator, recon-analyzer, recon-patterns (v11.1.0, adapted from riptide)
hooks/hooks.json + hooks/pg-log.sh # the ONE hook bundle (v13.0.0) — opt-in factory event log, inert until ~/.local/state/pg-factory/ exists; six events both harnesses document, one script serves both
skills/<name>/SKILL.md            # nine flywheel skills (ideate, define-goal, dispatch, process-inbox, goals-status, factory-report, loop-architect, factory-doctor, show-me)
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
  six root `agents/` definitions (three read-only review roles, owner-delegated
  decision 2026-07-16; three read-only recon/orientation roles adapted from
  riptide, owner-delegated decision 2026-08-12). Keep it minimal: plugin agents
  must stay read-only-by-tools on BOTH harnesses (no Edit/Write/Create/
  ApplyPatch/Agent/Task; the allowlist names both shell tools `Bash` +
  `Execute` since each harness silently drops unknown names), pin no
  `model:`, carry
  narrow non-auto-triggering descriptions, and every skill that spawns one keeps
  a generic-type inline-brief fallback (`general-purpose` on Claude Code,
  `worker` on Droid) so nothing breaks where plugin
  agents are unavailable. A new hook or agent needs the same explicit ask.
  A SECOND standing exception since v13.0.0 (owner ask 2026-09-01): root
  `hooks/` — `hooks.json` + `pg-log.sh`, the factory event log. It is OPT-IN BY
  CONSTRUCTION: the script exits at line one unless `~/.local/state/pg-factory/`
  exists, so installing the plugin writes nothing and records nothing until the
  owner runs one `mkdir`. That opt-in is not a nicety — the marketplace is public,
  and a plugin that starts logging on install is a bad surprise. It registers the six events BOTH
  harnesses document (SessionStart, SessionEnd, UserPromptSubmit, PostToolUse,
  SubagentStop, Stop) plus three Claude-only ones (SubagentStart, PostToolUseFailure,
  StopFailure) — v13.0.x withheld those fearing Droid would reject an unknown event key,
  and a live probe disproved it: Droid silently IGNORES events it does not know.
  `SubagentStart` is the load-bearing one: without it a subagent's clock starts at its
  first tool call, measuring a real 7-second subagent as 3 (a 57 % undercount) and making
  a zero-tool subagent — a lens returning a verdict — invisible; `StopFailure` carries a
  `rate_limit` reason, the usage-limit death the factory could never see. TWO details are load-bearing and were verified
  LIVE on a fresh session of each harness 2026-09-01, not read off the docs. First, the
  plugin-root reference must be DOUBLE-quoted: Claude Code hands the command to a shell
  and relies on it to expand `$CLAUDE_PLUGIN_ROOT`, so single quotes make it a literal
  and every hook dies with `cannot open ${CLAUDE_PLUGIN_ROOT}/...`, while Droid
  substitutes textually and works either way — and `async: true` SWALLOWS that error, so
  the symptom on Claude Code is a permanently empty log and no complaint. Second,
  PostToolUse carries NO matcher: Claude Code reads the matcher as a regex and matches
  every tool when it is omitted (a `matcher: "*"` entry logged nothing at all), and
  Droid matches all tools with it omitted too — carrying both entries made Droid fire
  TWICE for one tool call. `async: true` is honoured by Claude Code and ignored by
  Droid, which runs the hook synchronously at ~9 ms. Metadata only — never a
  prompt body, tool input, tool output, file content, or environment value; the one
  string it reads out of a command is a `chore(goals):` flip, keeping the verb and
  goal id. ~9 ms and ~100 bytes per tool call, rotating at 64 MB.
  (The repo carried a THIRD exception — `hooks/hooks.json` for the
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
  install, quick start, the nine skills in one line each, the queue/gate/config
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
