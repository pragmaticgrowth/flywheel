# After the implementer returns — repair, escalation, contract routing

Read this file when an implementer returns any status other than a clean `DONE`, or
when the gate verdict is anything other than PASS.

One status routes elsewhere: `DONE_WITH_CONCERNS` is not an escalation — its concerns
are settle-triage input (SKILL.md, Settle triage), and only a concern that invalidates
one of THIS goal's own acceptance criteria enters the repair path below as a gate
finding.

## FAIL_FIXABLE — the repair round (warm first)

A `FAIL_FIXABLE` verdict gets ONE repair round, fed the COMPLETE verified findings list
in one go (including any verified Critical/Important findings from the independent
review) — never one repair per finding.

**Warm resume is round one.** When the harness can continue the goal's own implementer
agent with its context intact (Claude Code: message the implementer you spawned,
addressed by the agent id its spawn returned — never a `name:`, which the
Spawning-and-waiting rule bans; its window already holds the goal, the code, and the
tests, so a resume costs a fraction of a cold spawn), resume it with the findings list
plus the receiving-review rules below. When the harness cannot resume (Droid, an agent
that died or errored, or the resume itself fails), spawn ONE fresh repair agent
instead — same brief as the implementer, same resolved implementer tier, findings
appended. **Replay detection:** a warm resume that returns with ZERO new commits and a
report indistinguishable from the previous one is the harness replaying the old turn,
not work — treat that resume as failed, disable warm resume for the REMAINDER of this
run, and spawn fresh. Either way it is one repair round: re-gate after it (commands in
the background, focused re-check in the foreground, join both); a second identical
FAIL → roll back + block, exactly as the no-progress rule requires. Never add a second
repair round to a warm resume — if the warm round couldn't fix it, the finding goes to
a human with the evidence, not to another spawn.

**The repair brief appends four receiving-review rules:** verify each finding against
the code before changing anything; a finding you can disprove gets a one-line rebuttal
with evidence in the report instead of a "fix" — the orchestrator adjudicates it; after
fixes, sweep your OWN repair diff once for new instances of the exact defect classes
you just fixed; and re-run the tests covering the amended code, appending both results
to the report file — the focused re-check reads evidence, it does not re-run your
tests.

**Adjudicating a rebuttal:** verify it against the code and the cited evidence
yourself — confirmed false → drop the finding from the re-check scope (note it in the
report); upheld → it goes back unfixed, and the re-gate treats it as an open failure.

**The focused re-check** (when verified review findings drove the repair): one fresh
read-only agent — the gate-reviewer plugin agent else the generic type, session model —
scoped to exactly those findings PLUS a one-pass collateral scan of the repair diff
itself (a fix can break a neighbor), not a new full review; its budget is TIGHTER than
the full review's, ~8 tool calls, and the brief says so: the full review already
happened, so nothing outside the named findings and the repair diff is in scope.

## Contract-defect short-circuits (no gate, no ladder)

A `CONTRACT_AMBIGUOUS` return is a contract defect caught early, not a work failure: if
any work commits landed before the stop, `git reset --hard <gate_base>`; set the goal
`blocked — contract defect: <criterion> ambiguous` — never respawn it to "try a
reading", the respawn guesses at the same fork.

`GOAL_UNREACHABLE` likewise skips the ladder: roll back any work commits and block with
reason `contract defect: <criterion> unreachable` — never a respawn.

**Then Self-heal owns the block (SKILL.md, Self-heal section).** Every contract-defect
block above routes through define-goal's amend machinery IN-RUN under the drain waiver
(red-team unchanged, one amend-and-re-claim per goal per run), and a block whose
evidence disproves the goal's premise RETIRES the goal instead
(`chore(goals): retire <id>`). It reaches needs-you as class `contract defect` only
when self-heal already failed on it this run, or the amend hits a true owner fork.

A live `NEEDS_CONTEXT` or `BLOCKED` return skips the gate — there is nothing to certify
yet — but does NOT go straight to `blocked`: run the escalation ladder first.

## Escalation ladder — before any goal blocks

Each rung fires at most ONCE per goal per session, and never as a same-model-unchanged
respawn — if the implementer is stuck, something must change (more context, a stronger
model, or a better contract). One carve-out: an evidenced transient STATUS-less death
re-fires the resume rung while the transient-death budget has headroom — each re-brief
carries a larger `Landed so far` set, which is the change. A ladder re-spawn continues
from the current branch state (same claim, same `gate_base`; roll nothing back — the
gate certifies the whole `gate_base..HEAD` diff regardless of which spawn produced it):

1. **`NEEDS_CONTEXT`** → answer it from what you hold — the queue, sibling goal files
   and their Interfaces notes, the latest-context bullets, repo config — and re-spawn
   once with the answer added to the brief. Nothing you hold answers it → roll back any
   work commits and block with the ask as the reason (class `contract defect`).
2. **`BLOCKED`, capability-shaped, on a cheap-stamped goal.** The goal's resolved
   implementer tier is `medium` or `light` AND the blocker reads capability-shaped (an
   architectural fork within contract bounds, "reading file after file without
   progress") → ONE re-spawn on the session model: omit the tier mapping entirely —
   dropping the pin IS the escalation (never a lighter tier, and never `heavy` instead)
   — noted in the report line. Goals already resolved to `inherit`/`heavy` skip this
   rung — capability was not the gap there.
3. **Too large / contract wrong.** A blocker that reads "the goal is too large" or "the
   contract is wrong" → the contract-defect route: roll back, block with
   `contract defect: <reason>`, then the Self-heal pass amends (or splits via
   define-goal) in-run. Never respawn — a respawn hits the same wall.
4. **No `STATUS:` block — resume from increments.** A missing `STATUS:` block on a
   returned implementer is itself a trigger for this rung — EVEN when work commits
   exist on the branch: the sitting is dead with unknown work-state. Never
   gate-then-reset it: the gate would FAIL half-done work and its rollback destroys
   landed increments. Instead: read `gate_base..HEAD` —
   `git log gate_base..HEAD` plus the diff — then re-brief ONE fresh worker with what
   already landed: the canonical implementer brief plus a `Landed so far` section
   carrying the increment log and what the diff already changed, finishing the goal
   from current HEAD on the same claim and `gate_base`, rolling nothing back.
   The changed brief is what makes this not a same-model-unchanged respawn; spawn on
   the goal's same resolved tier. The resumed worker's own `STATUS:` return routes
   normally. No work commits at all is the stale-claim path (SKILL.md Phase 1 bullet
   2), not this rung. Once per goal per session — one carve-out: a SECOND consecutive
   STATUS-less death re-fires this rung while the ~3-transient-respawn budget has
   headroom, the re-brief changed by the larger `Landed so far` set (never a
   same-model-unchanged respawn), and the rule is death-mode generic — the
   child-session timeout clause (SKILL.md Re-entrancy rule 2) is one named instance.
5. **Anything else** → roll back any work commits and block with the implementer's
   stated reason. **Guard:** a STATUS-less transient death never routes here while the
   transient-death budget has headroom — rung 4 re-fires. Once that budget is spent the
   goal blocks here as `repeated transient death` and the rollback fires at this rung.
