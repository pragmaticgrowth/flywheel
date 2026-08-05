# v10.0.0 — the smooth-drain release (design)

Date: 2026-08-06. Owner decision: after a superpowers-migration evaluation (two
Sonnet deep-reads + one Opus adversarial eval + two Sonnet transcript-forensics
passes over 19 real dispatch sessions, 2026-07-23 → 2026-08-06), the owner chose
to keep the flywheel architecture and fix the measured pain instead of migrating
to superpowers plan execution.

## Evidence (what the forensics measured)

- Session-span breakdown (158 cycles): ~61% usage-limit idle, ~29% implementer
  runtime, ~4% all review machinery. Repairs = 40.1% of ACTIVE wall-clock.
- Superpowers has no plan index/status (its ledger is git-ignored and deleted on
  finish), bans parallel implementers, has no cross-plan admission control, and
  its finishing skill stops for a human menu — a migration would rebuild
  index.yaml on day one and reproduce the v3 scar. Verdict: simplify, don't
  migrate.
- Stop-forensics (19 sessions): 7 runs ended "stopping after this one goal" with
  ready goals queued (the flagless one-goal default); 6 runs invented
  permission-asks the skill never requires ("Want me to run the repair?", "Say
  the word and I'll squash").
- Incomplete-forensics: the dominant leak is COMPLETION leaks, not early stops —
  a 30-goal run ended with 55 needs-you follow-ups incl. 3 production-impacting
  defects and 6 explicit "needs a new goal" items; six days later ZERO existed in
  any queue. A DONE_WITH_CONCERNS kernel bug ("recommend a follow-up goal") was
  likewise never queued. Prose evaporates; only committed artifacts survive.

## The seven changes

1. **Drain by default.** `/dispatch` ≡ `--unlimited`: work ready goals until the
   queue drains or a brake fires. `--count N` (incl. `--count 1`) is the opt-in
   limiter; `--unlimited` stays as an explicit alias. Budget/brakes unchanged and
   still outrank everything. Rationale: the #1 stop pattern was the old
   one-goal default + manual re-invoke; window-timed drains are already the
   sanctioned throughput pattern.
2. **Never-ask hard rule.** The per-goal cycle (claim → spawn → gate → repair →
   squash → complete/block → push) is autonomous end-to-end; asking permission
   for any step the skill specifies is a compliance miss. The attended-only
   three-condition question rule stays the ONLY legal interactive ask.
3. **Concern triage — no prose-only leftovers.** At settle, every implementer
   concern, verified-but-out-of-scope reviewer finding, and "needs a new goal"
   discovery is (a) repaired now if it breaches the goal's own contract,
   (b) dismissed with one line of reasoning in the report, or (c) CAPTURED to
   `docs/goals/inbox.md` (tracked, committed `chore(goals): inbox <id>`). A
   DONE_WITH_CONCERNS may not settle `completed` with unclassified concerns. The
   final report names inbox additions with the one command that converts them
   (`/define-goal` reads the inbox).
4. **define-goal inbox intake + touches: requirement.** define-goal, when
   invoked with a non-empty inbox, offers converting inbox items (batch mode at
   5+). Recon-backed feature/bug goals MUST carry `touches:` frontmatter
   (red-team check upgraded from drafting-miss to contract-blocking) so
   `--parallel` admission actually co-schedules.
5. **Single-lens fresh check by default.** The implementer panel defaults to ONE
   medium-tier lens (contract-conformance); the full 2–3-lens panel only for
   diffs spanning >3 files or touching test logic. Gate Arm B (independent
   reviewer) unchanged — the second view stays.
6. **Warm repair round.** Repair round 1 resumes the same implementer agent when
   the harness supports continuing a named agent (Claude Code); a fresh omnibus
   repair agent is round 2 (and the only round on Droid). Turn count beats token
   price — the implementer's context already holds the code.
7. **Skill diet.** dispatch/SKILL.md sheds its conditional paths to
   `references/` (parallel mode, the implementer brief, escalation ladder +
   repair briefs, Windows note), loaded only when the path is hit. Same rules,
   verbatim where moved; the resident file targets ~600 lines.

## Non-changes (deliberate)

- The local gate, two-arm overlap, claim protocol, two-anchor rollback,
  status-only-in-index, one-goal-integrates-at-a-time: untouched.
- No headless scheduler, no fast mode (owner 2026-07-28 constraints stand).
- goals-status script untouched this release (inbox surfacing rides dispatch's
  report; a status view of the inbox can come later if wanted).
