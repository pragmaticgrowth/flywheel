---
name: process-inbox
description: Use when the user runs "/process-inbox" or asks to process, triage, clean up, or work through docs/goals/inbox.md — the follow-up capture file dispatch appends at settle time ("what's in the inbox", "convert the inbox", "deal with the captured follow-ups"). Triage only, through the factory's own rails — goal conversion stays in define-goal, non-trivial implementation stays in dispatch.
argument-hint: ""
---

# Process-inbox — verify, triage, and clear the captured follow-ups

## Overview

`docs/goals/inbox.md` is dispatch's settle-triage capture file: one `- [ ]` line
per discovered defect or follow-up that was real but outside its source goal's
contract (date, source goal id, type guess, description, evidence pointer).
Dispatch only ever APPENDS. This skill is the attended sweep that clears it, with
the discipline the first large field pass proved out (romy, 2026-08-13: 101 items
→ 31 goals, 20 dead lines deleted, 3 settled by querying production — after EVERY
item was re-verified against current code).

**The one law: verify before you route.** Captures age. The measured base rate on
a weeks-old inbox is ~20% dead — code deleted since capture, fixed in passing, or
disproved on a closer read. An item's evidence pointer is where verification
STARTS, never a substitute for reading the code as it stands today. Converting an
unverified item queues phantom work; deleting an unverified item loses a real
defect.

**Boundaries.** This skill never writes goal files or index entries (define-goal
does, behind its contract review), never implements non-trivial work (dispatch
does, behind the gate), and never touches inbox lines outside the set it
processed. No question rounds: the OWNER bucket below is the only thing that
waits for a human.

## The process

### 1. Read and cluster

Read `docs/goals/inbox.md`; count open `- [ ]` items (zero → report "inbox
empty" and stop). Cluster items by the file/subsystem their evidence points at,
folding obvious duplicates (two captures naming the same function and the same
change are ONE item). Aim for one cluster per verification subagent, ~5–15 items
each.

### 2. Verify fan-out — every item re-checked against current code

Spawn one read-only verification subagent per cluster (foreground, concurrent,
cap ~8 per wave; more clusters → more waves). Claude Code:
`flywheel:recon-analyzer` when the runtime lists it, else `general-purpose` —
either way on the medium tier (`model: sonnet`); never the built-in Explore
type. Droid: `explorer` with `complexity: medium`, else `worker` with the
verification brief inline. Strictly read-only.

Each brief: "For each item below: does the described defect or opportunity exist
in the CURRENT code? The evidence pointer is your starting point, not your
answer — read the code as it stands. Return per item: CONFIRMED (current
`path:line` refs + one-line restatement) | DISPROVED (what the capture missed) |
GONE (the code was deleted or the fix already landed — name the commit if
visible) | UNVERIFIABLE-HERE (only a live/production system can settle it — name
the exact query that would). Evidence for every verdict; no fixes, no writes."

Judgment stays with you, on the session model: subagent verdicts are input, the
triage is yours.

### 3. Triage — every item into exactly ONE bucket

- **CONVERT** — confirmed and worth a factory cycle. Folding rules (measured):
  captures that are one change to one function fold into ONE goal; a broad
  caption-/comment-class splits by FILE, and a file still carrying more than
  two independent findings splits again — the repair-cost rule wins ties (a
  goal closing more than two independent findings costs more repair rounds
  than it saves).
- **FIX-NOW** — confirmed, and genuinely mechanical with no behavior change: a
  wrong comment or caption, a stale doc sentence, a dead constant, a
  typo-class rename. The bar is dispatch's review-skip bar, judged from the
  would-be diff itself; the measured why is that a full factory cycle per
  comment typo costs more than the typo. Any doubt, any test logic, anything a
  reviewer could argue with → CONVERT instead.
- **DROP** — DISPROVED or GONE. The line is deleted, its why recorded (step 5).
- **PRODUCTION-CHECK** — UNVERIFIABLE-HERE. If this session can reach the live
  system read-only (a query, a log read), run the named check now and re-triage
  on the result; otherwise it goes to the report's needs-you list with the
  exact query spelled out.
- **KEEP** — real but deliberately not actionable yet: needs a measurement
  first, blocked on a pending decision, unreachable at current caps. Stays
  captured, reason appended to its line.
- **OWNER** — spend, data deletion, anything irreversible or externally
  visible. Present it with a recommendation; never act on it. This is the only
  bucket that waits for a human.

### 4. Act, in this order

1. **FIX-NOW batch:** apply all mechanical fixes as ONE commit
   (`chore(inbox): direct fixes — <N> items`), then run the repo's
   `config.verify` commands (else its detected build+test). On failure: when
   the output plainly names ONE fixed file as the culprit, drop just that fix
   (demote its item to CONVERT) and re-run ONCE; any other or any second
   failure → revert the whole batch, demote every FIX-NOW item to CONVERT,
   and say so. Green → those lines are processed.
2. **CONVERT handoff:** invoke `define-goal` (inbox intake) with the CONVERT
   list inline — each inbox line verbatim plus its verdict and current
   `path:line` evidence; at ~5+ items that list IS define-goal's batch-mode
   item list. Items arrive pre-verified:
   define-goal's recon narrows to verify-and-complete (the plan-backed
   pattern), its contract red-team and approval table run unchanged, and it
   deletes each converted line in the same commit as the index entry — exactly
   its own intake rules. This skill writes no goal file and no index entry,
   ever.
3. **PRODUCTION-CHECK:** run what is runnable read-only; re-triage each result
   through step 3's buckets — a result can land anywhere, including FIX-NOW
   or OWNER.

### 5. Ledger and commit

Update `inbox.md` in one commit (`chore(goals): inbox triage YYYY-MM-DD`):

- DELETE dropped lines and fixed lines; converted lines go with define-goal's
  own commits.
- Record the pass as a short `## Triaged YYYY-MM-DD` section: counts per
  bucket, the notable folds, and one line of why per drop — the same ledger
  shape the field passes left, so the file carries its own history.
- KEEP lines stay `- [ ]` with the reason appended; OWNER lines stay untouched
  until the owner decides.

Push if the repo pushes on completion.

### 6. Report

One summary, counts first — `<N> items → <X> goals queued (<ids>) · <Y> fixed
directly (<commit>) · <Z> dropped dead · <K> kept · <P> production checks ·
<O> for you` — then each OWNER item in one plain-language line with your
recommendation. Nothing else needs the owner's eyes.

## Red flags — stop and get back on the path

- Converting or dropping an item no subagent verified THIS session → verify
  first.
- Writing a goal file or index entry here → that's define-goal's, always.
- A FIX-NOW item that changes behavior, touches test logic, or needs an
  explanation → CONVERT.
- A verification subagent asked to fix anything → read-only, always.
- Asking the owner about any bucket except OWNER → triage is yours.
- Deleting a KEEP or OWNER line, or editing lines outside the processed set.
- Skipping the verify fan-out because "the captures look obviously right" → the
  measured dead rate on a stale inbox is ~20%.

## Related skills

- **define-goal** — owns conversion (contracts, red-team, approval, line
  deletion); this skill is its verified front door.
- **dispatch** — appends captures at settle time; works the converted goals.
- **goals-status** — the queue view after conversion.
