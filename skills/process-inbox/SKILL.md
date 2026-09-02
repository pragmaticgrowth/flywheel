---
name: process-inbox
description: Use when the user runs "/process-inbox" (optionally --triage-only) or asks to process, triage, clean up, or work through docs/goals/inbox.md — the legacy follow-up capture file older dispatch versions appended at settle time ("what's in the inbox", "deal with the captured follow-ups", "clear the inbox"). Flagless runs END TO END — verify every item against current code, then FIX the real ones directly with tiered subagents behind dispatch's own gate, drop the dead ones, and park what cannot be fixed with a recorded why — one command, an emptied inbox, and NO new goals — it never converts items into goal files. --triage-only stops after triage and reports the fix list.
argument-hint: "[--triage-only]"
---

# Process-inbox — verify, triage, and clear the captured follow-ups directly

## Overview

`docs/goals/inbox.md` is the capture file dispatch versions before v15.0.0 appended
at settle time: one `- [ ]` line per discovered defect or follow-up that was real but
outside its source goal's contract (date, source goal id, type guess, description,
evidence pointer). Since v15.0.0 dispatch fixes those items in-run (its settle sweep)
and never writes this file; what remains in an inbox is legacy debt plus lines a
human added by hand. This skill is the sweep that clears it — **by fixing, never by
minting goals** (owner decision 2026-09-02: a sweep that turned N lines into eight or
ten goals just moved the debt into the queue).

**Flagless = drain ("one command, come back to an emptied inbox").** A flagless
`/process-inbox` runs the WHOLE path in one session: verify → triage → FIX every
confirmed item through dispatch's settle-sweep procedure (tiered fixer, two-arm gate,
one repair round, squash) → ledger. The run is never a confirmation point — an
invented mid-drain permission-ask ("want me to fix these?") is a compliance miss,
dispatch v10's rule applied here. The OWNER bucket is the only thing that waits for a
human, and it waits at the END of the report, never mid-run. `--triage-only` stops
after the ledger commit and reports the FIX list without running it.

**The one law: verify before you route.** Captures age — the measured base rate on a
weeks-old inbox is ~20% dead (code deleted since capture, fixed in passing, or
disproved on a closer read). An item's evidence pointer is where verification STARTS,
never a substitute for reading the code as it stands today. Fixing an unverified item
changes code for a phantom; deleting an unverified item loses a real defect.

**Boundaries.** This skill never writes goal files or index entries — not in its own
context and not through define-goal: the CONVERT bucket is gone. Non-trivial fixes run
through dispatch's settle-sweep procedure (`skills/dispatch/references/settle-sweep.md`
— the fixer brief, the gate, the repair round), never in this context; it never
touches inbox lines outside the set it processed. No question rounds: the OWNER
bucket below is the only thing that waits for a human.

## The process

### 1. Read and cluster

Read `docs/goals/inbox.md`; count open `- [ ]` items (zero → report "inbox empty"
and stop). **Retire stamped keeps first:** any open line carrying a `KEEP <date>:`
stamp from a pre-v15 sweep skips verification and retires to the `## Triaged` ledger
in step 5 (`retired keep: <gist> — <reason>`); it was adjudicated once, and if it
ever becomes live a dispatch settle will sweep it. **OWNER lines carried over from a
previous sweep are RE-ADJUDICATED against the OWNER bar (step 3), never re-listed
as-is:** run the blast-radius check the bar demands; a line that fails the bar
re-triages into a normal bucket this sweep, and only a line that still clears it — a
proven, still-live consequence — is re-presented, with its check attached. A parking
lot is not a bucket. Then cluster the remaining items by the file/subsystem their
evidence points at, folding obvious duplicates (two captures naming the same function
and the same change are ONE item). Aim for one cluster per verification subagent,
~5–15 items each.

### 2. Verify fan-out — every item re-checked against current code

Spawn one read-only verification subagent per cluster (concurrent — all of a wave's
spawns in ONE message, cap ~8 per wave; more clusters → more waves). Claude Code:
`flywheel:recon-analyzer` when the runtime lists it, else `general-purpose` — either
way on the medium tier (`model: sonnet`); never the built-in Explore type. Droid:
`explorer` with `complexity: medium`, else `worker` with the verification brief
inline. Strictly read-only.

Each brief: "For each item below: does the described defect or opportunity exist in
the CURRENT code? The evidence pointer is your starting point, not your answer — read
the code as it stands. Return per item: CONFIRMED (current `path:line` refs + one-line
restatement + the files a fix would touch) | DISPROVED (what the capture missed) |
GONE (the code was deleted or the fix already landed — name the commit if visible) |
UNVERIFIABLE-HERE (only a live/production system can settle it — name the exact query
that would). Evidence for every verdict; no fixes, no writes."

**Spawning and waiting.** Dispatch's Spawning-and-waiting rule (its Hard rules
section) is the canonical statement and governs these spawns too: plain spawns
(`subagent_type`, `model`, brief — never a `name:`, never backgrounded), let the turn
end rather than building a wait, and death needs evidence — the only thing that
licenses giving up on a verifier is TWO checks with real minutes between them showing
zero new transcript records and no completion notification. Then, and only then:
**retry once, never wait a second round.** Respawn that cluster ONCE, plain; if the
respawn also delivers nothing, verify that cluster's items in your own context and
note `verified inline (verifier not delivered)` on them. That fallback is legitimate
HERE because a verification subagent buys context economy and parallelism, not
independence — nothing is grading its own work. It is NOT available for the sweep's
gate review, where independence is the entire product; that waits.

Judgment stays with you, on the session model: subagent verdicts are input, the
triage is yours.

### 3. Triage — every item into exactly ONE bucket

- **FIX** — CONFIRMED, and a code change one fixer sitting can land and the gate can
  verify — dispatch's one-sitting test (Settle triage, disposition 3): inside the
  evidence's files plus their tests, no migration/lockfile/CI/config file, no new
  drivable surface. Live defects, missing wiring, false captions/comments/docs. The tier is decided per the settle-sweep rule — heavy for any behavior
  change or test logic, medium for rote mechanical work, never light. **Mechanism
  check:** an item whose fix names a specific mechanism — an alert channel, a queue,
  a binding, a secret — gets that mechanism verified LIVE (read-only) before any fix
  (a measured recommended fix would have paged nobody: the webhook was unset in both
  environments).
- **PARK** — CONFIRMED but not fixable here: goal-sized (a schema/migration change, a
  conflict-domain file, a new drivable surface, its own contract's worth), needs a
  measurement first, or unreachable at current caps. It leaves the open list for the
  ledger with its why, and the report carries one `fyi: follow-up` line ending
  `→ /define-goal <one-line want>` — the owner decides whether it becomes a goal.
  This skill never decides that.
- **DROP** — DISPROVED or GONE. The line is deleted, its why recorded (step 5).
- **PRODUCTION-CHECK** — UNVERIFIABLE-HERE. If this session can reach the live system
  read-only (a query, a log read), run the named check now and re-triage on the
  result (runnable checks do not print as P-lines); otherwise it goes to the report
  as a P-line (query + why), not the needs-you list, and leaves the open list for
  the ledger as `production-check: <gist> — <query>` (step 5). P-lines are not
  OWNER lines.
- **OWNER** — a decision that is provably the human's: it spends money, deletes or
  exposes data that EXISTS today, or is irreversible/externally visible outside the
  repo's own gated path. **The bar — a proven consequence, not a matching topic.**
  Before anything is routed OWNER, run the read-only check that sizes the blast
  radius — the `SELECT` on the table the deletion would touch, the secret/bucket
  listing the alert depends on, the count of affected rows — and attach the check
  and its result to the item. An empty or absent target is NOT a data-loss decision
  — the item then re-triages as ordinary work (a still-real preventive fix goes to
  FIX, a dissolved claim DROPs); a change confined to code behind the factory's own
  gate is NEVER an owner item (shipping is what the factory is for); "for
  convention's sake", "worth your attention", and "recommend X" are FIX. An item
  whose own recommendation is a code edit the gate can verify is not an owner item.
  (Field measurement: four of five topic-matched OWNER items dissolved under one
  read-only production query.) Present each surviving item with a recommendation;
  never act on it. This is the only bucket that waits for a human — and only items
  that clear the bar may wait.

### 4. Fix, cluster by cluster (flagless runs only)

Run dispatch's settle-sweep procedure once per FIX cluster, sequentially — one
writer in the tree at a time: `sweep_base` = HEAD; ONE fixer on the strongest tier
the cluster needs, plain foreground spawn, the sweep brief verbatim with the
cluster's items (commit prefix `chore(inbox): <gist>`, one item per commit; the
evidence path goes to `~/.local/state/pg-dispatch/<SLUG>/reports/inbox-<date>.md`);
then the sweep gate over `sweep_base..HEAD` — Arm A as ONE tracked, `timeout`-bounded
background script running every `config.verify` command plus the `docs/goals/`
untouched check, Arm B sized by the diff (mechanical carve-out, one reviewer, or the
panel), both joined before a verdict; one repair round; still failing and localized
to one item's commit → revert that commit and re-run Arm A once; otherwise reset to
`sweep_base`, and every item in the cluster becomes PARK with `sweep failed:
<reason>`. PASS → squash the cluster to ONE `chore(inbox): <n> items — <gists>`
commit. A cap of ~5 items per sweep holds; a larger cluster runs as consecutive
sweeps. Fixer-SKIPPED items re-triage: an owner's-word why → OWNER, a too-large why →
PARK. **PRODUCTION-CHECK** items run first: a result can land anywhere, including
FIX or OWNER. Under `--triage-only`, skip this step and report the FIX list.

### 5. Ledger and commit

Update `inbox.md` in one commit (`chore(goals): inbox triage YYYY-MM-DD`):

- DELETE dropped lines and fixed lines.
- PARK lines leave the open list too: each becomes one ledger line —
  `parked: <gist> — <why> → /define-goal <want>`; unrunnable PRODUCTION-CHECK lines
  likewise — `production-check: <gist> — <query>`.
- RETIRE previously-stamped KEEP lines (step 1) the same way —
  `retired keep: <gist> — <its original KEEP reason>`.
- Record the pass as a short `## Triaged YYYY-MM-DD` section: counts per bucket,
  the notable folds, the sweep commits, and one line of why per drop — the same
  ledger shape the field passes left, so the file carries its own history.
- OWNER lines are the ONLY lines that may stay `- [ ]`, untouched until the owner
  decides. After a sweep the open list holds exactly the OWNER lines — zero
  otherwise.

Push if the repo pushes on completion.

### 6. Report

One summary, counts first — `<N> items → <F> fixed (<commits>) · <Z> dropped dead ·
<K> parked · <P> production checks · <O> for you` — then one `fyi: follow-up` line
per parked item — then one P-line per unrunnable production check (query + why) —
then each OWNER item in one plain-language line with your recommendation. **That is
the ENTIRE message:** the counts line, the follow-up lines, the P-lines, one line per
OWNER item — no "What happened" section, no tables, no caveats, no epilogue; the
detail lives in the committed `## Triaged` ledger and the sweep report file. `<K>`,
`<P>`, and `<O>` must each EQUAL the number of lines of their kind printed (a measured
report said "6 for you" and listed 5). "Nothing else needs the owner's eyes" is a hard
envelope, not advice — the measured violations ran to ~3,000 characters.

## Red flags — stop and get back on the path

- Fixing or dropping an item no subagent verified THIS session → verify first.
- Writing a goal file or index entry, or invoking define-goal to convert a line →
  this skill never mints goals; PARK it with the `/define-goal` pointer.
- Fixing a non-trivial item in your own context → the sweep procedure, always.
- A verification subagent asked to fix anything → read-only, always.
- Asking the owner about any bucket except OWNER → triage is yours.
- Deleting an OWNER line, or editing lines outside the processed set.
- Two fixers writing in the tree at once → one cluster at a time.
- Skipping the sweep gate because the fixes "look mechanical" → the mechanical
  carve-out is judged from the diff, and Arm A always runs.
- Skipping the verify fan-out because "the captures look obviously right" → the
  measured dead rate on a stale inbox is ~20%.
- Pausing a flagless drain to ask permission → the drain invocation already
  answered; only OWNER items wait.
- Routing an item to OWNER without the read-only blast-radius check attached → run
  the check first; topic-matching is not the bar.
- Re-presenting a carried-over OWNER line without re-adjudicating it against the
  bar → the bucket is a decision queue, never a parking lot.
- A report with any section beyond the counts line, the follow-up lines, the
  P-lines, and the OWNER lines → the envelope is hard.

## Related skills

- **dispatch** — owns the settle-sweep procedure this skill reuses, and since
  v15.0.0 fixes its own settle findings in-run, so a fresh repo's inbox stays empty.
- **define-goal** — where a PARKED follow-up goes ONLY when the owner asks for it.
- **goals-status** — shows the inbox count while legacy debt remains.
