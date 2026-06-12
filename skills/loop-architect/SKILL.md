---
name: loop-architect
description: Use when the user wants to automate, schedule, or run work autonomously/remotely — setting up a /goal, /loop, routine, channel, or long unattended run, or asking "how do I keep Claude working on X". Designs the loop contract (prompt + verification + stop conditions) instead of just running the task.
---

# Loop Architect

Design loops and goals the way Boris Cherny does: "Turn workflows into skills, then loop them."
Output of this skill = a concrete, copy-pasteable setup (goal contract, loop prompt, or routine
prompt) with verification and hard stops — not a vague plan.

## Step 1 — Qualify (the four-condition test)

A loop pays off only when ALL four hold. Check honestly; if one fails, recommend a plain
one-shot prompt instead and say which condition failed.

1. **Repeats** — the task recurs at least ~weekly (or runs many iterations within one goal)
2. **Automated gate** — a test / typecheck / build / linter / benchmark can REJECT bad output
   without a human in the room
3. **Budget** — the user's plan can absorb retries and re-reads (loops explore and waste)
4. **Tools** — the agent can run what it changes and see what breaks (logs, dev server,
   browser extension, simulator, MCPs)

## Step 2 — Pick the primitive

| Situation | Primitive |
|---|---|
| Work until a verifiable end state is true | `/goal` (Haiku evaluator checks after every turn) |
| Poll/babysit on a cadence while a session is open | `/loop <interval> <skill-or-prompt>` |
| Recurring default maintenance for this repo | bare `/loop` + a `.claude/loop.md` |
| Must run with the laptop closed | Routine (`/schedule`; cloud; schedule / API / GitHub triggers) |
| Needs local files, machine on, no session open | Desktop scheduled task |
| React to external events (CI, chat) instead of polling | Channels (`--channels`) or Routine API trigger |
| Massively parallel / adversarial / unknown-size work | Dynamic workflow (pair with `/goal` for hard completion) |
| Deterministic check on every turn, all sessions | Stop hook |

Combos are normal: workflow + `/goal` for hard completion; skill + `/loop` for cadence;
routine + channel for laptop-closed with phone telemetry.

Workflow thresholds (per Claude Code docs): >5 independent agents or a multi-stage
find→verify→synthesize loop → workflow; 2–4 parallel lookups → plain subagents, cheaper
and simpler; anything that must survive the session (cross-iteration implementers,
multi-day queues) → background agents + a state file, never a workflow — runs are
session-bound and don't resume across sessions. The Workflow tool needs Claude Code
≥2.1.154 and can be disabled; design a plain-subagent fallback.

## Step 3 — Write the contract

### For /goal — six elements, one cap (condition max 4,000 chars)

CRITICAL CONSTRAINT: the evaluator only reads the transcript. It cannot run commands or read
files. Every clause must be demonstrable by output Claude prints (test results, exit codes,
diffs, counts). Never write taste conditions ("clean", "better", "high quality").

```
/goal <end state> verified by <command + expected output Claude will print>
while preserving <what must not regress/change>.
Work only within <files/branches/tools boundaries>.
Between iterations, record what changed, what the check showed, and the next best action.
If blocked or no valid paths remain, stop and report attempted paths, evidence, the
blocker, and what would unlock progress. Stop after <N> turns.
```

- Include an explicit outcome taxonomy for queue-like work ("every item ends as
  fixed | acknowledged-stale | abandoned | blocked-external; 0 items left unclassified") —
  a missing "blocked" bucket makes the goal bounce forever on reality.
- Prefer two small goals with a checkpoint over one mega-goal.
- If the user's ask is vague, run pre-goal calibration: ask what "done" means until it is
  specific and measurable, THEN draft the condition for approval.

### For /loop — skill-first

1. Confirm the task ran manually at least once reliably. If not, do that first.
2. Put the procedure in a skill (scope, exact checks, allowed actions, FORBIDDEN actions,
   state-file location, one-line status format per iteration). The loop body is then just
   `/loop 10m /skill-name`.
3. Fixed interval for predictable cadence; omit the interval to let Claude self-pace
   (1m–1h based on observed activity); bare `/loop` uses `.claude/loop.md` if present.
4. Remember mechanics: fires between turns only, 7-day expiry, jitter up to 30m on
   recurring tasks, Esc cancels a pending iteration, restored on `--resume`.

### For routines (cloud) — fully autonomous, no permission prompts exist

The prompt must be self-contained: what to read, what to do, how to verify, where to write
results, what success means, what to escalate. Pushes only to `claude/`-prefixed branches
unless unrestricted pushes were explicitly enabled. Scope repos, connectors, and network
access to the minimum the routine needs.

## Step 4 — Wire verification and state (non-negotiable)

- **Gate**: name the exact command(s) that can fail the work, and require their output in
  the transcript / PR / summary.
- **Maker/checker split**: for anything substantial, a separate verifier (subagent,
  workflow verifier, or /goal's evaluator) judges the work — never the agent that wrote it.
- **State file**: a markdown/board/ledger outside the conversation records done/next/blocked
  so the next run resumes instead of restarting. Name the file in the prompt. For factory
  work, the canonical ledger is the `docs/goals/index.yaml` queue (created by `define-goal`,
  worked by `/loop 15m /dispatch`) — prefer it over inventing a new state file.
- **Self-verification tooling** (Boris's #1, "2-3x the quality"): browser extension for web
  UI, simulator MCP for mobile, runnable server + tests for backend. Name the tool in the
  prompt and describe it.

## Step 5 — Hard stops and safety rails

Always include, in the prompt itself:
- Max iterations / turn cap ("stop after 25 turns", "max 3 retries on the same finding")
- No-progress detection ("if the same error appears twice without progress, stop and report")
- Token budget for workflows ("+200k budget") — workflows balloon 5–10× without one
- The repo's hard rules verbatim (e.g. forbidden merges, protected branches, prod flags) —
  hooks are a backstop, not the encoding
- Human gate before merge / deploy / dependency changes
- Quarantine: agents reading untrusted content (tickets, scraped pages) get no
  high-privilege tools; separate actor agents never see the raw text

## Step 6 — Remote layer (offer when relevant)

- Steer from phone: `claude --rc <name>` or `/remote-control`; server mode
  `claude remote-control --spawn worktree` for multiple phone-spawned sessions
- Telemetry: `/config` → "Push when Claude decides"; or "notify me when X finishes" in
  the prompt; channels (Telegram/Discord/iMessage) for two-way chat into a live session
- Laptop closed: routines, Claude Code on the web, teleport (`&` / `--teleport`) to move
  sessions between local and cloud

## Output format

Deliver: (1) chosen primitive + one-line why, (2) the exact contract/prompt block ready to
paste, (3) the gate + state file, (4) the hard stops included, (5) any skill/loop.md file to
create — create it if the user agrees or has asked for setup. Keep it to one screen.
