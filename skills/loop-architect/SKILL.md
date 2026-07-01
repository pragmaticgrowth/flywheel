---
name: loop-architect
description: Use when the user wants to automate, schedule, or run work autonomously/remotely — setting up a /goal, /loop, routine, channel, or long unattended run, or asking "how do I keep the agent working on X". Designs the loop contract (prompt + verification + stop conditions) instead of just running the task.
---

# Loop Architect

**CLI detection**: this skill works in both Claude Code and Droid (Factory CLI). Detect
your runtime: if Droid-specific tools (CronCreate, CreateAutomation) are available or
`$DROID_PLUGIN_ROOT` is set, you are in Droid. Otherwise Claude Code. The primitive table
in Step 2 maps each situation to both CLIs.

Design loops and goals the way Boris Cherny does: "Turn workflows into skills, then loop them."
Output of this skill = a concrete, copy-pasteable setup (goal contract, loop prompt, or routine
prompt) with verification and hard stops — not a vague plan.

## Intake rule

Start with a short brief: repeated task, target repo/system/environment, gate command(s),
state file/ledger, budget/cadence, tools available, and the stop/escalation condition. Ask
one concise proactive question round (max 4 questions) when any of those missing pieces
changes the primitive, safety, or verifiability. If enough context exists, proceed with
explicit assumptions. If the user is also asking to create work for the factory, pair this
skill with define-goal: design the repeat mechanism, then return to a real goal artifact
(`docs/goals/` entry or run-now command). Do not leave the user with loop advice only.

## Step 1 — Qualify (the four-condition test)

A loop pays off only when ALL four hold. Check honestly; if one fails, recommend a plain
one-shot prompt instead and say which condition failed.

1. **Repeats** — the task recurs at least ~weekly (or runs many iterations within one goal)
2. **Automated gate** — a test / typecheck / build / linter / benchmark can REJECT bad output
   without a human in the room
3. **Budget** — the user's plan can absorb retries and re-reads (loops explore and waste)
4. **Tools** — the agent can run what it changes and see what breaks (logs, dev server,
   browser extension, simulator, MCPs)

**Closed first, open later.** Default to the most bounded primitive and scope that still
solves the task — a *closed* loop (defined steps, a gate after each, tight blast radius);
widen to a broader open-ended goal only after the gate has demonstrably rejected bad output
in practice. Every loop that fails dies one of four deaths — runaway cost, silent death
(stands still, pretends alive), aimless drift, or shipping faster than you can review — and
all four are cheaper to prevent in a bounded loop than to detect in an open one.

## Step 2 — Pick the primitive

| Situation | Claude Code | Droid |
|---|---|---|
| Work until a verifiable end state is true | `/goal` (Haiku evaluator checks after every turn) | `droid exec --auto high "<condition>"` (agent self-verifies) or interactive paste |
| Poll/babysit on a cadence while a session is open | `/loop <interval> <skill-or-prompt>` | `CronCreate` with `same_session: true`, `recurring: true` |
| Recurring default maintenance for this repo | bare `/loop` + a `.claude/loop.md` | `CronCreate` same_session with the loop body as the job prompt (no loop.md equivalent) |
| A backlog of shippable changes worked unattended | docs/goals queue — fill with `define-goal`, then repeat `/dispatch` (one ready goal per run on the checked-out branch; `/loop /dispatch` drains over repeated fires) | docs/goals queue — fill with `define-goal`, then repeat `/dispatch` (one ready goal per run on the checked-out branch; use `CronCreate` same_session to drain over repeated fires) |
| Must run with the laptop closed | Routine (`/schedule`; cloud; schedule / API / GitHub triggers) | `CreateAutomation` (cloud; runs on a Droid Computer) or `CronCreate` with `new_session` |
| Needs local files, machine on, no session open | Desktop scheduled task | `CronCreate` with `new_session` (starts a fresh local session) |
| React to external events (CI, chat) instead of polling | Channels (`--channels`) or Routine API trigger | Slack integration + `CronCreate` new_session; or `CreateAutomation` with event triggers |
| Massively parallel / adversarial / unknown-size work | Dynamic workflow (pair with `/goal` for hard completion) | Mission mode (`droid exec --mission`; pair with `droid exec --auto high` for hard completion) |
| Deterministic check on every turn, all sessions | Stop hook | Hook in `.factory/hooks/hooks.json` |

Combos are normal: workflow + `/goal` for hard completion; skill + `/loop`/`CronCreate` for
cadence; routine/automation + channel for laptop-closed with phone telemetry.

Workflow thresholds (per platform docs): >5 independent agents or a multi-stage
find→verify→synthesize loop → workflow (Claude Code) or mission mode (Droid); 2–4 parallel
lookups → plain subagents, cheaper and simpler; anything that must survive the session
(cross-iteration implementers, multi-day queues) → the `docs/goals/index.yaml` ledger plus
repeated one-goal dispatch runs, never workflow state — workflows are session-bound and don't
resume across sessions. Dispatch implementers may use workflows only for bounded read-only
fan-out or review inside that one goal, never as parallel code-writing lanes. The Workflow
tool needs Claude Code ≥2.1.154 and can be disabled; Droid's mission mode
(`droid exec --mission`) is the equivalent but also optional. Design a plain-subagent
fallback for either CLI.

## Step 3 — Write the contract

### For /goal — six elements, one cap (condition max 4,000 chars)

CRITICAL CONSTRAINT: the evaluator (Claude Code's `/goal` Haiku evaluator, or Droid's
agent self-verification) only reads the transcript. It cannot run commands or read
files. Every clause must be demonstrable by output the agent prints (test results, exit
codes, diffs, counts). Never write taste conditions ("clean", "better", "high quality").

```
/goal <end state> verified by <command + expected output the agent will print>
while preserving <what must not regress/change>.
Work only within <files/branches/tools boundaries>.
Between iterations, record what changed, what the check showed, and the next best action.
If blocked or no valid paths remain, stop and report attempted paths, evidence, the
blocker, and what would unlock progress.
If the same check fails the same way twice in a row, or after ~3 honest attempts the end
state can neither be reached nor shown measurable (a flaky, non-deterministic, or
contradictory check), declare GOAL_UNREACHABLE: <which clause, why unmeasurable, last
measurement> and stop — never retry the identical failing approach. Stop after <N> turns.
```

In Droid (no `/goal` command), the equivalent is:
`droid exec --auto high "<same condition>"` for headless, or paste the condition as a
prompt in an interactive session. The agent self-verifies by running every acceptance
command and showing output — bake the verification commands into the prompt explicitly
since there is no separate evaluator model to check them automatically.

- Reachability pre-check: before drafting the condition, confirm the end state is one the
  agent can drive to TRUE and MEASURE — a binary or a threshold it can print — not an
  asymptote ("every page < 50ms") or an unmeasurable absolute. An unreachable target spins
  forever; fix the target before writing the goal. Pair it with the GOAL_UNREACHABLE escape
  hatch above so the loop terminates even when a check turns out flaky in practice.
- Include an explicit outcome taxonomy for queue-like work ("every item ends as
  fixed | acknowledged-stale | abandoned | blocked-external; 0 items left unclassified") —
  a missing "blocked" bucket makes the goal bounce forever on reality.
- Prefer two small goals with a checkpoint over one mega-goal.
- If the user's ask is vague, run pre-goal calibration: ask what "done" means until it is
  specific and measurable, THEN draft the condition for approval. Keep the question round
  short; derive code-level detail from repo recon instead of asking the user to debug for you.

### For /loop — skill-first

1. Confirm the task ran manually at least once reliably. If not, do that first.
2. Put the procedure in a skill (scope, exact checks, allowed actions, FORBIDDEN actions,
   state-file location, one-line status format per iteration). The loop body is then just
   `/loop 10m /skill-name` (Claude Code) or `CronCreate` same_session every 10m running
   `/skill-name` (Droid).
3. Fixed interval for predictable cadence; omit the interval to let the agent self-pace
   (1m–1h based on observed activity); bare `/loop` uses `.claude/loop.md` if present
   (Claude Code only — Droid has no loop.md equivalent; embed the loop body directly in the
   `CronCreate` job prompt).
4. Remember mechanics: fires between turns only, 7-day expiry, jitter up to 30m on
   recurring tasks, Esc cancels a pending iteration, restored on `--resume` (Claude Code).
   Droid's `CronCreate` same_session has analogous semantics (fires between turns in the
   same session); `CronCreate` new_session starts a fresh session each fire.

### For routines (cloud) — fully autonomous, no permission prompts exist

The prompt must be self-contained: what to read, what to do, how to verify, where to write
results, what success means, what to escalate. Pushes only to `claude/`-prefixed branches
unless unrestricted pushes were explicitly enabled. Scope repos, connectors, and network
access to the minimum the routine needs.

## Step 4 — Wire verification and state (non-negotiable)

- **Gate**: name the exact command(s) that can fail the work, and require their output in
  the transcript / PR / summary.
- **Maker/checker split**: for anything substantial, a separate verifier (subagent,
  workflow verifier, /goal's evaluator, or the agent's own self-verification in Droid)
  judges the work — never the agent that wrote it.
- **State file**: a markdown/board/ledger outside the conversation records done/next/blocked
  so the next run resumes instead of restarting. Name the file in the prompt. For factory
  work, the canonical ledger is the `docs/goals/index.yaml` queue (created by `define-goal`,
  worked by repeated one-goal `/dispatch` runs) — prefer it over inventing a new state file.
- **Self-verification tooling** (Boris's #1, "2-3x the quality"): browser extension for web
  UI, simulator MCP for mobile, runnable server + tests for backend. Name the tool in the
  prompt and describe it.
- **Liveness**: each iteration writes a heartbeat (cycle number + timestamp + one-line
  status) to the state file/ledger and announces the cycle number, so the ABSENCE of an
  update is detectable — a loop that silently dies (e.g. after a context-window blowout)
  otherwise looks alive. For unattended/cloud runs, recommend an external silence-detector
  ("no heartbeat in N intervals → alert").
- **Health metric**: the number that matters is cost (tokens/$) per ACCEPTED change — a
  gate-passed completed goal or a passing artifact — not raw tokens or loops run. A sustained
  acceptance rate below ~50% means the loop is making slop: tighten the gate or stop it. For
  factory work the completion ledger (`index.yaml` completed count) is the acceptance
  denominator. (The v4 dispatch model has no PRs — nothing is "merged"; a goal is accepted when
  it passes the local gate and its squashed commit lands on the branch.)

## Step 5 — Hard stops and safety rails

In-prompt caps are the SOFT layer — the agent can edit its own context, so a drifting loop
can weaken or delete its own brakes. Where the runtime allows it, the load-bearing brake (the
hard token/dollar/iteration ceiling AND the pass/fail gate) must be enforced by something the
agent CANNOT edit: a Stop hook, an external cron/budget process ("burnstop"), the CI gate,
/goal's separate evaluator, or dispatch's `config.budget`. "Install the brakes before the
horsepower" — and never let the loop grade itself against a criterion it can rewrite.

Always include, in the prompt itself (the soft layer, restated for the agent):
- Max iterations / turn cap ("stop after 25 turns", "max 3 retries on the same finding")
- No-progress detection ("if the same error appears twice without progress, stop and report")
- Convergence stop for review/verification loops: stop when the gate verdict clears even if
  cosmetic nits remain — treat reviewer comments as findings to verify, not orders to obey,
  and cap review rounds. Chasing a perfectly clean review spawns fresh nits forever.
- Token budget for workflows ("+200k budget") — workflows balloon 5–10× without one
- The repo's hard rules verbatim (e.g. forbidden merges, protected branches, prod flags) —
  hooks are a backstop, not the encoding
- Human gate before merge / deploy / dependency changes
- Quarantine: agents reading untrusted content (tickets, scraped pages) get no
  high-privilege tools; separate actor agents never see the raw text

## Step 6 — Remote layer (offer when relevant)

- Steer from phone: `claude --rc <name>` or `/remote-control` (Claude Code); server mode
  `claude remote-control --spawn worktree` for multiple phone-spawned sessions. In Droid,
  use Droid Computers (persistent cloud or BYOM Linux machines) for laptop-closed operation,
  or the Factory web app to resume sessions from any browser.
- Telemetry: `/config` → "Push when Claude decides" (Claude Code); or "notify me when X
  finishes" in the prompt; channels (Telegram/Discord/iMessage) for two-way chat into a live
  session. In Droid, use `/settings` for notification config; the Factory app provides push
  notifications and session monitoring.
- Laptop closed: routines + Claude Code on the web (Claude Code); `CreateAutomation` running
  on a Droid Computer (Droid); teleport (`&` / `--teleport`) to move sessions between local
  and cloud (Claude Code). In Droid, use Droid Computers or session forking
  (`droid exec --fork <session-id>`) to resume work across machines.

## Output format

Deliver: (1) chosen primitive + one-line why, (2) the exact contract/prompt block ready to
paste, (3) the gate + state file, (4) the hard stops included, (5) any skill/loop.md file to
create — create it if the user agrees or has asked for setup. Keep it to one screen.
