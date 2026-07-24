---
name: ideate
description: Use when the user has an idea or early want that isn't ready to define — "I have an idea", "what if we", "let's think through X", "/ideate" — or when goal definition stalls because the want needs design exploration first. Explores intent and design through dialogue; never implements and never writes goal files or queue entries (that's define-goal).
argument-hint: "[the idea to explore]"
---

# Ideate — explore an idea into an approved design

## Overview

Turn a fuzzy want into a design the user has approved, then hand that design to
`define-goal` to become measurable goal contracts. This is the pipeline's front door:

```
/ideate  →  /define-goal  →  /dispatch  →  /goals-status
(explore)   (contract)       (execute+gate)  (observe)
```

Ideation is dialogue, not paperwork: understand the current system, ask what actually
matters, propose real alternatives, and converge on a design the user recognizes as
what they meant. The user may not be an engineer — plain language throughout.

A want that is already shaped ("add rate limiting to /api/orders, 429 over 100
req/min") skips this skill entirely — send it straight to `define-goal`; ideating on
it is ceremony. Conversely, when a define-goal question round reveals the want is
really a design problem (answers keep re-opening what to build rather than pinning it
down), hand off here instead of burning define-goal's two capped rounds on design
questions.

**HARD GATE.** The ONLY terminal states of this skill are (a) invoking `define-goal`
with the approved design, or (b) the user parking or dropping the idea. Never write
goal files, `index.yaml` entries, or code; never scaffold; never implement "just the
obvious part"; never draft goal contracts here to skip define-goal's contract review
and confirmation. This holds regardless of how simple the idea seems — simple ideas
are where unexamined assumptions waste the most work.

## The process

Work through these in order; scale each step to the idea's size.

### 1. Context first

Orient in the current system before asking anything — files, docs, recent commits,
where similar features already live. For a bigger unknown, spawn 1–2 read-only
subagents (`general-purpose`, no model override — they inherit the session model;
never the built-in Explore type if it would force a cheaper model) reporting
`path:line` summaries, never file dumps. This is orientation, not recon: enough to
ask good questions and propose grounded approaches. define-goal's recon still runs
later, narrowed by what you found — the handoff tells it what you already located so
it verifies rather than re-derives.

### 2. Scope check — before any detail question

If the idea spans multiple independently shippable pieces, surface the decomposition
FIRST: the pieces, how they relate, what order to build them. A question round spent
refining a piece that then splits is a wasted interrupt (the same reason define-goal
asks its split question first). The decomposition maps 1:1 onto future goals and
their `depends_on` chain — say so in plain language ("this is really three
deliverables; the second needs the first").

### 3. Clarifying dialogue

One AskUserQuestion round at a time, 1–2 questions per round; each question carries
concrete options with a recommended default (open-ended only when options would
mislead). Keep the dialogue going while answers still change the design; stop the
moment the next question wouldn't. There is no round cap here — this is the attended,
conversational stage; the two-round cap belongs to define-goal's interview, not this
dialogue. Spend every question on purpose, constraints, or success criteria — never
on detail the repo can answer.

YAGNI ruthlessly: propose cutting features from every design. A cut piece can always
be ideated later as its own goal.

### 4. Propose 2–3 approaches

Present genuinely different approaches with trade-offs, recommendation first with the
reasoning. One approach means you stopped thinking early; four means you are
delegating the design back to the user.

### 5. Present the design

Sections scaled to their complexity — a few sentences for a simple idea; for a
genuinely large design, checkpoint section by section ("does this look right so
far?"). Cover what applies: the outcome in the user's terms, architecture and
components, data flow, error handling, and — always — how it will be verified (name
real commands and drivable surfaces where you can; this feeds define-goal's
acceptance criteria directly). When a comparison is genuinely clearer shown than
told and the html-artifacts skill is available, use it; never require it.

### 6. Self-review, inline

Before handoff, re-read the design with fresh eyes:

- **Placeholders:** any "TBD", "handle edge cases", "appropriate X"? Fix them.
- **Consistency:** do sections contradict each other?
- **Ambiguity:** could a requirement be read two materially different ways?
  Two-readable requirements come back as `CONTRACT_AMBIGUOUS` stops at dispatch
  time — kill them here, the cheapest place.
- **Scope:** one goal or a chain? (Feeds the handoff below.)

Fix inline and move on — no re-review loop.

### 7. Handoff to define-goal

On the user's approval, invoke `define-goal` with the approved design: the
outcome(s), the decomposition with the interfaces between pieces, the files and
constraints you located, and the verification story. Single piece → normal
define-goal flow. Multiple pieces → define-goal batch mode with the decomposition as
the item list. define-goal still runs its own (narrowed) recon, contract review,
model stamping, and confirmation — the design is input, never a bypass.

## Design brief file — multi-goal chains only

For a chain (2+ goals), write ONE short design brief to
`docs/goals/briefs/YYYY-MM-DD-<topic>.md` (create the directory if needed) and have
define-goal link it from each chain goal's Context. Dispatch implementers see only
their own goal file; the brief is the shared background a chain needs. Keep it under
a page: outcome, decomposition, interfaces, key decisions with their why. The goal
files remain the contracts — the brief never carries acceptance criteria or status.
For a single-goal outcome, no file: the design flows into that goal's Context and the
conversation ends. (This brief is the one sanctioned planning artifact beyond goal
files; define-goal's own no-artifacts rule is untouched.)

## Red flags — stop and get back on the path

- Writing a goal file, index entry, or code "while it's fresh" → HARD GATE violation.
- "Too simple to need the dialogue" → the design can be three sentences, but present
  it and get approval.
- Asking a question the repo can answer → read the repo; save the user's attention
  for purpose, constraints, and success.
- Refining details of a piece before the split question is settled.
- Presenting one approach as inevitable.
- A design section that says "TBD" or "we'll figure that out during implementation".

## Related skills

- Shaped want, or design approved → **define-goal** (single or batch mode).
- Recurring/unattended execution of the result → **loop-architect** (reached through
  define-goal, which owns the goal contract).
- Working the resulting queue → **dispatch**.
