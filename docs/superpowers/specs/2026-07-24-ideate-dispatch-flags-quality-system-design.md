# Ideation skill, dispatch flags, and the end-to-end quality system

**Date:** 2026-07-24 · **Status:** DESIGN — awaiting owner approval, nothing implemented
**Sources read in full:** all 14 superpowers v6.1.1 skills plus the three subagent prompt
templates (implementer, task-reviewer, code-reviewer); flywheel's define-goal and dispatch
SKILL.md at v6.0.0.

## 1. What the superpowers deep-read actually taught us

Most of superpowers' quality machinery is already in flywheel — often in a stronger,
factory-adapted form. The honest gap analysis:

| Superpowers skill | Flywheel today | Verdict |
|---|---|---|
| brainstorming | **Nothing before define-goal.** define-goal interviews to fill a contract; nobody explores a fuzzy idea into a design first. | **GAP → new `ideate` skill (§2)** |
| writing-plans | define-goal writes goal contracts (our unit of plan). Interfaces notes (v5.5.0), type-shaped criteria, grounding in real commands. | Covered. One adoption: the explicit **No-Placeholders check** in the red-team rubric (§5). |
| executing-plans | dispatch's implementer brief: skeptical contract read, follow the contract exactly, stop-don't-guess (`CONTRACT_AMBIGUOUS`). | Covered. Its "stop and ask" maps to our needs-you lane. |
| subagent-driven-development | dispatch's whole shape: fresh implementer per goal, report files, fresh-check panel, gate review, omnibus repair, turn-count-beats-token-price (v5.5.0). | Mostly covered. **Two adoptions: the BLOCKED escalation ladder and `NEEDS_CONTEXT` (§4).** |
| test-driven-development | Mandated in the implementer brief; bug goals lead with the failing test; gate proves repro-direction. | Covered — ours is deterministic where theirs is prompt discipline. |
| verification-before-completion | Mandated in the brief; the whole gate exists because "the implementer's report is evidence, not the verdict". | Covered. |
| requesting-code-review | `flywheel:gate-reviewer` — adversarial, diff-scoped, calibrated (v5.3.0/v5.5.0). | Covered. |
| receiving-code-review | Orchestrator verifies findings before repair. The **repair agent** itself gets no verify-then-fix discipline. | **Small adoption (§4): repair brief gains verify-then-fix / rebut-with-evidence.** |
| systematic-debugging | Bug-type recon (all hypotheses recorded), failing-test-first, ~3-honest-attempts → GOAL_UNREACHABLE. | Covered; the 3-failures→question-the-architecture rung folds into the escalation ladder. |
| dispatching-parallel-agents | Recon fan-out, fresh-check lens panel — bounded inside one goal. | Covered. |
| finishing-a-development-branch | Local gate → squash → complete; rollback on FAIL. No options menu needed — the factory has one integration path by design. | Covered / not applicable. |
| using-git-worktrees | **Deliberately absent** — v3 scar tissue (CHANGELOG 4.0.0). | Not adopted, stays that way. |
| writing-skills | Repo rule since 2026-07-17: subagent dry-runs + RED baselines for skill edits. Also the SDO lesson: descriptions carry triggers, never workflow (dispatch's description already obeys this). | Covered. |
| using-superpowers | Skill-invocation mandates inside dispatch's brief. | Covered. |

**Deliberately NOT adopted, with reasons on file:**

- Worktrees / per-goal branches / PR checkpoints — v4.0.0 scar tissue; the local gate is
  the only integration gate.
- Per-task human checkpoints (executing-plans' stop-and-ask cadence) — dispatch is
  autonomous; `CONTRACT_AMBIGUOUS` + needs-you is the equivalent rail without breaking
  unattended runs.
- One-question-at-a-time interviewing in **define-goal** — the v5.5.1 decision stands
  (option-based rounds, two-round cap). The conversational mode lives in `ideate`, where
  the user is present by definition (§2).
- A separate progress-ledger file (SDD's `.superpowers/sdd/progress.md`) — `index.yaml`
  is already the durable ledger and the heartbeat is already the liveness record.
- review-package/task-brief helper scripts — dispatch already hands file paths (goal
  file, report file) and its reviewers read the diff themselves; the orchestrator's
  context never holds the diff either way.

## 2. New skill: `ideate` — the pipeline's front door

The superpowers pipeline is brainstorming → writing-plans → executing. Ours becomes:

```
/ideate  →  /define-goal  →  /dispatch  →  /goals-status
(explore)   (contract)       (execute+gate)  (observe)
```

`ideate` is to `define-goal` what brainstorming is to writing-plans: it turns a fuzzy
want into an **approved design**; define-goal then turns that design into measurable
contracts. It fills the one genuinely empty slot in the pipeline — today a fuzzy idea
either gets prematurely contracted or wanders unstructured.

**Name:** `ideate` (verb-first, matches dispatch/define-goal naming; avoids colliding
with `superpowers:brainstorming` on machines that run both).

**Description (trigger-only, per the SDO lesson — no workflow summary):**
> Use when the user has an idea or early want that isn't ready to define — "I have an
> idea", "what if we", "let's think through X", "/ideate" — or when goal definition
> stalls because the want needs design exploration first. Explores intent and design
> through dialogue; never implements and never writes goal files or queue entries
> (that's define-goal).

**Process (adapted from brainstorming, kept proportional):**

1. **Context first.** Light read-only look at the repo/system (files, docs, recent
   commits). For a bigger unknown, 1–2 read-only subagents under the same rules as
   define-goal's recon (inherit session model, report `path:line`, never Explore-type).
   This is orientation, not recon — define-goal's recon still runs later, narrowed by
   what ideate found.
2. **Scope check before detail questions.** If the idea spans multiple independently
   shippable pieces, surface the decomposition FIRST — pieces, relationships, build
   order — before refining any one piece. (Mirrors define-goal's split-first rule; a
   question round spent refining a piece that then splits is a wasted interrupt.)
   The decomposition maps 1:1 onto future goals + `depends_on` chains.
3. **Clarifying dialogue.** One focused AskUserQuestion round at a time (1–2 questions
   per round), each question with concrete options and a recommended default;
   open-ended only when options would mislead. Keep going while answers still change
   the design; stop when they stop mattering. No hard round cap — this is the
   attended, conversational stage; the two-round cap stays in define-goal, where it
   belongs. Focus: purpose, constraints, success criteria. YAGNI ruthlessly — cut
   features from every design.
4. **Propose 2–3 approaches** with trade-offs, recommendation first with reasoning.
5. **Present the design** in sections scaled to complexity — a few sentences for a
   simple idea, section-by-section approval checkpoints only for a genuinely large
   one. Cover what applies: architecture, components, data flow, error handling, how
   it will be verified (this feeds acceptance criteria directly).
6. **Self-review inline** before handoff: placeholder scan (TBD/vague requirements),
   internal consistency, two-readable requirements (ambiguity is a contract defect
   downstream — kill it here), scope (single goal or a chain?). Fix and move on — no
   re-review loop.
7. **Handoff — the HARD GATE.** On user approval, invoke `define-goal` with the
   approved design: the outcome(s), the decomposition with interfaces between pieces,
   located files/constraints, and the verification story. Single piece → normal
   define-goal flow. Multiple pieces → define-goal batch mode with the decomposition as
   the item list. `ideate` NEVER writes goal files, index entries, or code, and never
   skips define-goal's own red-team/confirmation — terminal state is invoking
   define-goal, nothing else. (Brainstorming's HARD-GATE, mapped onto our pipeline.)

**Design artifact:** for a multi-goal chain, write one short design brief to
`docs/goals/briefs/YYYY-MM-DD-<topic>.md` and have each goal's Context link it —
dispatch implementers see only their own goal file, and a chain benefits from one
shared reference (each goal still carries its own Interfaces note; the brief is
background, the goal file remains the contract). For a single-goal outcome, no file —
the design flows into the goal's Context and dies as conversation. This is the one
sanctioned planning artifact beyond goal files, created by ideate before define-goal
runs (define-goal's own no-artifacts rule is untouched).

**Boundary with define-goal:** a clear want ("add rate limiting to /api/orders,
429 over 100 req/min") goes straight to define-goal — ideate would be ceremony. The
define-goal description gains one line pointing fuzzy intake at ideate; the ideate
description points shaped wants back. When invoked mid-define (a question round
reveals the want is really a design problem), define-goal hands off to ideate rather
than burning its two rounds on design questions.

## 3. Dispatch flags — `/dispatch [<goal-id>] [--count N | --unlimited]`

**Grammar:**

| Invocation | Behavior |
|---|---|
| `/dispatch` | Work the next ready goal (today's behavior; ≡ `--count 1`). |
| `/dispatch 87` | Solo mode on goal 087 — the existing "work goal 005" path, now a first-class argument. Accepts `87`, `087`, or `087-slug`. |
| `/dispatch --count 3` | Work up to 3 ready goals, sequentially, in this run. |
| `/dispatch --unlimited` | Keep working ready goals until the queue drains or a brake fires. |

Arg rules: a goal id combined with `--count`/`--unlimited` → the id wins, note the
ignored flag in the report. `--count` needs N ≥ 1; anything else → report usage, work
one goal. Unknown flags → same.

**The invariant, restated honestly.** The research-backed rule was never "one goal per
run" as an end in itself — it was *one goal AT A TIME, on one branch, behind a local
gate*, because v3's parallelism (worktrees, PRs, concurrent implementers) livelocked.
`--count`/`--unlimited` are in-session sequential repetition of the exact same per-goal
cycle `/loop /dispatch` already repeats across fires: each goal fully settles — claim →
implement → gate → squash-or-rollback, branch clean, single-`in_progress` invariant
continuously true — before the next claim. No safety property changes. CLAUDE.md's
invariants section gets reworded from "one goal per run" to "one goal at a time,
sequential; a run works 1..N goals per its flags" at implementation time.

**Batch loop semantics:**

- Phase 0 (read queue) and Phase 1 (settle in-flight) run ONCE at batch start —
  finished work still beats new work.
- Then per goal: Phase 2 claim → Phase 3 implement → gate → settle → Phase 4 report
  line + heartbeat append. One report line and one heartbeat line **per settled goal**
  (each per-goal cycle counts as one "fire" — keeps the cross-fire brake's
  lines-after-claim arithmetic meaningful), plus one final batch summary line
  (`[dispatch batch] worked <n> goals: <ids+verdicts> · stopped: <reason>`).
- A goal that settles `blocked` does NOT stop the batch — the next ready goal is
  claimed, exactly as the next loop fire would. Dep-chains behave naturally: a blocked
  goal's dependents simply aren't ready.
- The end-of-drain CI observation stays end-of-batch/drain, never per-goal. The
  stalled-factory notification stays once-per-distinct-blocker-set.

**Stop conditions (first one wins):**

1. Count reached (`--count N`).
2. Queue drained — no ready goals (for `--unlimited`, the existing drained-queue
   terminal stop; needs-you-empty check unchanged).
3. `config.budget.max_goals_per_session` exhausted — **budget always wins**; effective
   cap = min(flag, budget). The budget is the external brake precisely because the
   session can't edit it; a flag must not outrank it. A user who wants a true
   unlimited drain removes the budget from `config` themselves.
4. **Environment brake (new):** two CONSECUTIVE goals fail with the same
   infrastructure-shaped cause — the same `config.verify` command failing identically
   in a way the goals' diffs can't explain, or two INCONCLUSIVE gate verdicts → stop
   the batch, surface "run `/factory-doctor`" under needs-you. A broken environment
   must not burn the queue one blocked goal at a time.

**Relationship to `/loop` and unattended runs:** `--unlimited` is the *attended*
"drain it now" mode. For unattended drains, `/loop /dispatch` + external scheduling
remain the recommended rail (loop-architect's usage-limit-proofing: an in-session
batch dies silently at a subscription window with no hook fired; the per-goal
heartbeat makes that death detectable, and Phase 1 idempotency makes the next run's
recovery clean — mid-goal death in a batch is exactly a mid-fire death today). The
skill says this explicitly so `--unlimited` doesn't get sold as a scheduler.

## 4. Dispatch adoptions from executing-plans / SDD

**a. The BLOCKED escalation ladder.** SDD's controller never lets a stuck implementer
die silently or retry unchanged: assess the blocker, then (1) provide context, (2)
escalate the model, (3) split the task, (4) escalate to the human. Dispatch today goes
straight from BLOCKED to `blocked` (only transient deaths get respawns). Adopt the
ladder, proportionally — each rung at most ONCE per goal per session, and never a
same-model-no-change respawn:

1. **`NEEDS_CONTEXT` (new sixth implementer status).** The implementer needs
   information the orchestrator holds (latest context, a sibling goal's interfaces, a
   path, a config value) — distinct from BLOCKED so a context ask is never mislabeled
   a failure. Orchestrator answers from what it holds (queue, goal files, latest
   context) and re-spawns once with the answer in the brief. Can't answer → needs-you.
2. **Capability escalation.** A BLOCKED report from a goal stamped `sonnet`/`haiku`
   whose blocker reads capability-shaped (architectural fork within contract bounds,
   "reading file after file without progress") → ONE re-spawn on the stronger model
   (the session model), noted in the report line. Never downgrade; never re-spawn
   `inherit`/`opus` goals on this rung — for them capability wasn't the gap.
3. **Too large / contract wrong** → existing contract-defect route:
   `blocked — contract defect: <reason>`, needs-you amendment via define-goal (which
   splits or re-specifies). Also the landing place for systematic-debugging's
   "3 failed fixes → question the architecture": an implementer that burns its ~3
   honest attempts on fix-shaped churn reports GOAL_UNREACHABLE, and the amendment —
   not a fourth fix — is the answer.
4. Anything else → `blocked` with reason, exactly as today.

**b. Repair-agent discipline (from receiving-code-review).** The orchestrator already
verifies findings before spawning repair; the repair agent itself should inherit the
same skepticism. Three lines added to the repair brief: verify each finding against
the code before changing anything; a finding you can disprove gets a one-line rebuttal
with evidence in the report instead of a "fix" (the orchestrator adjudicates); after
fixes, re-run the covering tests and append results to the report file — the re-check
reviewer reads evidence, it doesn't re-run your tests.

## 5. define-goal: one small tightening

The red-team rubric gains an explicit **No-Placeholders check** (from writing-plans,
where placeholders are named plan failures): "TBD", "appropriate error handling",
"handle edge cases", a criterion naming no command, a threshold with no number —
contract-blocking findings. Today's gameability/termination checks catch most of
these; naming the pattern class closes the rest. One rubric bullet, nothing more.

## 6. The end-to-end quality system (the assembled view)

Every stage has a maker, an independent checker, and a deterministic backstop where
one exists. Judgment is front-loaded left (attended, cheap) so execution can run
autonomous right:

| Stage | Maker | Independent check | Deterministic backstop |
|---|---|---|---|
| **Ideate** | design dialogue with the user | user approval gate (HARD GATE: no goals, no code) | self-review scan (placeholders, ambiguity, scope) |
| **Define** | contract draft, grounded by recon fan-out | `contract-red-team` (gameability, command reality, type shape, gate fit, termination, no-placeholders) + user confirmation | 4,000-char cap, turn cap, headless-`acceptance:` rule |
| **Implement** | one implementer per goal (model per contract-tightness stamp) | fresh-check lens panel (contract / tests-overbuild / stray-regressions) | TDD red-green, verification-before-completion, off-happy-path probe |
| **Gate** | — | `gate-reviewer` (adversarial, diff-scoped, anti-laundering) challenging the implementer's own verdicts | `pg_validate.py` + `config.verify`, repro-direction for bugs; squash on PASS, hard rollback on FAIL |
| **Repair** | one omnibus repair agent (verify-then-fix, rebut-with-evidence) | focused re-check + collateral scan | re-gate; second identical FAIL → rollback + block |
| **Operate** | dispatch fires (1, N, or unlimited per flags) | needs-you lane + one-shot notifications; escalation ladder before any goal blocks | claim protocol, single-`in_progress` invariant, heartbeat + cross-fire brake, budget, environment brake, factory-doctor, loop-architect's external rails |

The through-line adopted from superpowers, stated once: **evidence before claims at
every seam** — the user approves the design, the red-team breaks the contract, the
implementer proves with failing-then-passing tests, the reviewer refutes rather than
confirms, the gate re-runs everything, and no maker ever grades its own work.

## 7. Rollout plan (on approval — one release)

**Version:** flywheel v6.1.0 (one bump bundles everything, per release policy).

1. New `skills/ideate/SKILL.md` (§2). No scripts, no agents — pure guidance.
2. dispatch SKILL.md: flag grammar + batch loop (§3), escalation ladder +
   `NEEDS_CONTEXT` in the brief/status contract, repair-brief lines (§4).
   Description updated (trigger-level only): default = next ready goal; a goal id,
   `--count N`, or `--unlimited` select more.
3. define-goal SKILL.md: no-placeholders rubric bullet (§5); one intake line routing
   fuzzy wants to ideate; ideate handoff accepted as input (design → contracts).
4. CLAUDE.md: pipeline now four stages; invariant reworded to "one goal at a time".
   README + `public/index.html`: six flywheel skills, pipeline diagram, flag docs —
   same change, same commit. Marketplace description if it enumerates skills.
5. CHANGELOG entry, version pill/title/badge bumps, tag `v6.1.0` + GitHub release,
   `wrangler deploy`, plugin-validator run before commit.
6. **Skill testing per repo rule** (writing-skills doctrine, already adopted):
   subagent dry-runs with "cite the section that decides each answer", plus RED
   baselines against `git show HEAD:<file>` for the compliance-critical rules —
   (a) `/dispatch --count 3` semantics (old text must leave it undecided),
   (b) `/dispatch 87` (old text decides it only via "work goal 005" phrasing),
   (c) ideate's hard gate (never writes goals),
   (d) NEEDS_CONTEXT vs BLOCKED routing,
   (e) budget-beats-flag under `--unlimited`.

## 8. Decisions taken in this design (flag if you disagree)

1. **Name `ideate`**, not `brainstorm` — avoids superpowers collision, matches naming.
2. **Design brief file only for multi-goal chains**, at `docs/goals/briefs/` —
   single-goal ideation stays fileless.
3. **`--unlimited` positioned as attended**; unattended drains stay on
   `/loop` + external scheduling (usage-limit reality, not preference).
4. **`NEEDS_CONTEXT` added as a sixth status** rather than folded into BLOCKED —
   the split is what stops context asks being blocked as failures.
5. **Budget outranks flags** — the external brake stays external.
6. **No worktrees, no parallelism, no per-task human checkpoints** — re-affirmed, not
   revisited.
