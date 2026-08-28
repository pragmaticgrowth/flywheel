---
topic: standard-of-completion
created: 2026-08-28
amended: 2026-08-29
status: done
repo: flywheel
branch: main
artifact: https://claude.ai/code/artifact/2c4b2516-7362-46f3-bb8a-528a53f10873
---

# The factory measures the whole, and its standard can only get stricter

## What we're doing

Two changes, from Factory's 2026-08-27 finding that a coding agent stops early
because it invents its own definition of "done" while working. Flywheel already
authors the standard before the work — that is what a goal contract is. What it
does not do is (1) measure the WHOLE of a multi-goal plan, only each piece, and
(2) stop the standard from quietly loosening once work is underway. This plan
closes both.

**Amended 2026-08-29** (re-read of the source article against this draft, before
any phase was minted). The two changes stand unaltered. Three holes in HOW they
were specified are closed, each one a way the standard could still soften while
every artifact stayed honestly derived:

1. The ratchet guarded goal files only — but the outcome bullets live in the
   PLAN, and plans have no immutability rule anywhere in the repo. Ideate
   iterates the same plan file by design. Soften the plan, contract the outcome
   goal from the softened text, and nothing ever compares. Plans are now under
   the ratchet too.
2. Nothing said the outcome check must be a COMMITTED, suite-discovered test.
   The article's instrument is not a final exam — it is "current evidence that
   those procedures pass against the artifact being shipped," rerun as the
   artifact changes. An ad-hoc command run once at settle goes stale the moment
   a later phase lands.
3. v12.3.0 (shipped 2026-08-28, after this plan was written) made Report-only
   the DEFAULT settle-triage disposition with "unsure lands here." That is
   correct for nits and points the wrong way for whole-outcome gaps, which is
   the exact failure this plan exists to catch.

Also refreshed for what v12.3.0 moved: the version target (v12.3.0 → v12.4.0),
the regression floor (262 → 360 tests), and the claim that `docs/goals/plans/`
is empty.

## Current state

Today a plan's phases get ticked off one by one, and when the last one checks the
plan is stamped done. Nothing ever asks whether the thing the plan set out to
deliver actually works. Separately, when a goal blocks on a bad contract, the
factory now rewrites that contract by itself, mid-run, with nobody watching — and
nothing checks whether the rewrite made the bar easier to clear.

Key discoveries:
- The plan template already declares outcomes but they are inert prose —
  `skills/ideate/references/plan-template.md:62-71` (`## What will be true when
  done`, plus an optional post-ship signal). Nothing runs them.
- Plan completion is a display stamp with no behavior:
  `skills/dispatch/SKILL.md:780-788` — "A DISPLAY mirror only"; `status: done` is
  stamped "when the last open phase checks". Recon confirmed no plan-level gate,
  check, or report exists anywhere in dispatch.
- Phases map 1:1 onto goals through a `Plan: … — Phase <N>` Context line
  (`skills/dispatch/SKILL.md:608-614`), so a plan-level check can be an ordinary
  goal — no new dispatch machinery is needed.
- Amend rewrites only the criteria the block reason names defective, byte-for-byte
  elsewhere (`skills/define-goal/SKILL.md:978-985`), but nothing compares the
  result against what it replaced. Grep for weaken/loosen/original/previous over
  define-goal returned nothing.
- The drain waiver waives question rounds and owner confirmation but explicitly
  never the red-team (`skills/define-goal/SKILL.md:1013-1021`) — so the red-team
  is the one enforcement point self-heal cannot route around.
- None of `agents/contract-red-team.md`'s 14 items compares a draft against a
  previous version of the same contract.
- House pattern for verifying skill-text changes: a root `test_*_policy.py`
  placement-guard suite using an `unwrapped()` helper, a docstring stating the
  forensic grounding, and an explicit note that meaning is proven by subagent
  dry-runs, not by text presence (`test_self_heal_policy.py:1-30`,
  `test_contract_scope_policy.py:1-40`).
- `## Contract reality check` says "eight checks" and lists NINE
  (`skills/define-goal/SKILL.md:704-712` vs `713-782`) — item 9 arrived in v12.1.0
  and the header was never updated. CLAUDE.md repeats the wrong count.
- `config.verify` was `python3 -m pytest -q` with pytest not importable here, so the
  gate failed on every goal. Fixed 2026-08-28 to
  `uv run --with pytest --python 3.13 pytest -q` — 262 tests green. Do not "fix" it back.

Added by the 2026-08-29 amendment, each verified against the tree at `4007651`:
- There is NO plan immutability rule anywhere: grepping `skills/` and `CLAUDE.md`
  for plan-immutability language returns nothing, and ideate explicitly iterates the
  same plan file on re-invocation. Goal files are immutable contracts; plans are
  not, and the outcome bullets live in the plan.
- Phase implementers DO read the plan — `skills/dispatch/references/implementer-brief.md:12`
  instructs them to Read the linked plan before starting. This is deliberate (see
  the resolved open question on visibility) and is what makes the drivable-surface
  requirement on outcome bullets load-bearing rather than cosmetic.
- v12.3.0 shipped 2026-08-28, after this plan was drafted, and moved settle triage
  underneath it: `skills/dispatch/SKILL.md:871,899` now make Report-only the DEFAULT
  disposition with "unsure lands here", and captures require an earning token.
- The suite is now 360 tests, not 262, and the released version is 12.3.0 — so this
  chain targets v12.4.0.

## What will be true when done

Each outcome names the exact command that proves it, in `config.verify`'s form. All
but the last FAIL at this plan's amended base commit `4007651` (the suites do not
exist there) and pass only once every phase has landed; the last is the regression
guard and is green at BOTH ends — it proves nothing broke, not that something
arrived.

- A weakening amend stops for the owner even under the drain waiver, and a
  tightening amend still proceeds unattended —
  `uv run --with pytest --python 3.13 pytest -q test_ratchet_policy.py`
- A weakening edit to a PLAN's outcome bullets stops for the owner the same way a
  weakened goal criterion does — `uv run --with pytest --python 3.13 pytest -q
  test_ratchet_policy.py -k plan`
- A 3+-phase plan carries an executable outcome check as its own final phase, with
  every check named as a command that fails at base —
  `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py`
- An outcome check is a committed test the repo's own suite discovers, so it keeps
  running as later phases land — never a command run once at settle —
  `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py -k
  committed`
- `status: done` on a plan means its outcome check passed, not that its pieces got
  built — `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py -k
  test_plan_status_done_means_outcome_check_passed`
- A settle-triage item that falsifies a plan outcome bullet is never Report-only,
  no matter how unsure the implementer is —
  `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py -k
  report_only`
- Nothing else regressed — `uv run --with pytest --python 3.13 pytest -q`, green at
  base and at head, never fewer than the 360 tests passing before this chain
- The two rules decide real scenarios the way they read — **needs independent
  review**: subagent dry-runs with RED baselines against `git show HEAD:<file>`, per
  CLAUDE.md's skill-edit rule, with both transcripts written into the goal's report
  file as named evidence. Placement-guard tests pin the text, never its meaning; this
  bullet is where meaning is checked.

Post-ship signal: on the next drain that self-heals a blocked goal, the amendment
note names what it tightened; on the next 3+-phase plan, the final phase is an
outcome check nobody hand-wrote.

## What we're NOT doing

- **Not hiding acceptance criteria from implementers.** Factory's "wall" keeps the
  validator's test cases secret because their implementer is recreating a
  black-box binary and would otherwise target the sample. Flywheel's phases are
  real features against a known repo; the ratchet, not secrecy, is what protects
  the standard.
- **Not building weighted behavior inventories or differential-testing harnesses.**
  That shape belongs to reimplementation and migration work, which is not what this
  queue does.
- **Not adopting the campaign shape.** Their system run cost 14x the credits and
  13x the wall time of the single agent, on hand-picked tasks, one run per cell,
  no repeats. Directionally interesting; not a budget model for a subscription.
- **Not touching the per-goal gate.** It already is an independent standard the
  implementer did not author. It stays exactly as it is.
- **Not auto-fixing a failed outcome check.** Owner decision 2026-08-28: a whole
  outcome miss is a design fault, and design faults stop for the owner.
- **Not retrofitting existing plans.** The rule applies to plans written from here
  on. `docs/goals/plans/` now holds exactly one file — this plan — and it already
  conforms: it has 4 phases and its Phase 4 is an outcome check that runs every
  bullet above, showing each failing at base and passing at HEAD.
- **Not adopting expansion-on-saturation.** The article's loop, when the instrument
  stops revealing differences, expands the instrument or starts differential
  testing against the reference. That move requires an ORACLE to expand toward.
  ProgramBench has the reference binary; flywheel has owner intent, which does not
  admit more sampling — there is nothing to diff against. This is also the honest
  ceiling on the whole plan: an outcome check can only ever be as good as what the
  owner said they wanted at ideate time. Which is exactly why the plan-level
  ratchet matters more here than it does there: their instrument cannot drift
  because the reference cannot change, and ours is just a file.

## Design

### An outcome check is just the plan's last phase, so dispatch needs almost no new machinery

Phases already map 1:1 onto goals with a `depends_on` chain. Making the outcome
check the final phase means it inherits the entire existing pipeline for free: it
gets contracted by define-goal, red-teamed, reality-checked, claimed by dispatch,
run through the same local gate, and settled into the same report line. A failure
blocks and surfaces under `needs-you:` with no new code path.

It also fixes the meaning of `status: done` by construction: the stamp already
fires when the last phase checks, and the last phase is now the outcome check.

```
Phase 1 ─┐
Phase 2 ─┼─ depends_on ─→ Phase N+1: outcome check ─→ plan status: done
Phase 3 ─┘                (verification only, builds nothing)
```

### Outcome bullets stop being prose and start being commands

`## What will be true when done` already exists and is already the right section.
It changes from a prose list to a checkable one, reusing the goal-file convention
for the parts a command cannot settle:

```markdown
## What will be true when done

Each outcome names the exact command that proves it. Every one of these fails on
the plan's base commit and passes only once all phases have landed.

- <observable outcome> — `<exact command>`
- <subjective outcome> — **needs independent review**
```

The fail-at-base rule is what keeps this from degenerating into a second copy of
`config.verify`: a check that already passes before any phase lands is measuring a
piece, not the whole. It mirrors the reality check's existing
fail-at-base/pass-at-head item rather than inventing a new idea.

### The ratchet compares an amended contract against its own previous commit

The "before" is `git show HEAD:docs/goals/<id>.md` — deterministic, already in the
repo, no new state file. Comparing against HEAD on every amend makes the contract
monotonically non-weakening, so it is transitively never weaker than the original.

Weakening (stops for the owner, waiver or not):

```
criterion deleted and not replaced
threshold loosened            (fewer, slower, lower coverage)
runnable command  →  an assertion a human or agent must vouch for
drivable-surface check  →  a code-reading check
before/after criterion loses its BEFORE
`needs independent review` flag removed
`touches:` narrowed so a path the criteria still require drops out
```

Tightening or repair (proceeds unattended, as today):

```
criterion added
wrong path or command corrected so it actually runs
two-readable criterion pinned to the STRICTER reading
criterion split per Drainability
not-yet-true capability moved to a depends_on prior
```

### The plan is under the same ratchet, or the goal-file ratchet has a back door

Added 2026-08-29. The ratchet above compares `git show HEAD:docs/goals/<id>.md`.
But the outcome bullets do not live in a goal file — they live in the plan, and
grepping `skills/` and `CLAUDE.md` for a plan immutability rule returns nothing.
Ideate is *designed* to iterate the same plan file on re-invocation.

So without this, the bypass is clean and leaves no trace:

```
1. soften `## What will be true when done` in the plan   (unguarded today)
2. define-goal contracts the outcome goal from the plan  (honest derivation)
3. ratchet compares the goal file against ITS previous   (nothing weakened)
4. outcome check passes; plan stamps `status: done`      (against a lower bar)
```

Every step is individually legitimate, which is what makes it the exact failure
the article names — the standard collapsing around what was already built.

The fix reuses the machinery rather than adding any: a plan's outcome bullets are
ratcheted against `git show HEAD:docs/goals/plans/<file>.md` on the SAME
weakening/tightening taxonomy. Deleting a bullet, dropping its command for prose,
loosening its threshold, or removing a **needs independent review** flag is
weakening and stops for the owner. Adding a bullet, or pinning a vague one to a
command, is tightening and proceeds. The rest of the plan — design, phases,
context — stays freely editable; only the outcome bullets are load-bearing.

One consequence worth stating: this makes ideate, not just define-goal, a place
where the ratchet applies. That is correct. Ideate is where the standard is
authored, so it is where the standard can first be lowered.

### An outcome check is a committed test, not a command someone ran once

Added 2026-08-29. The article's instrument has three parts: an inventory of what
must be established, procedures for establishing each part, and *current evidence
that those procedures pass against the artifact being shipped*. The third part is
a live property, not a one-time result — the checks are "rerun as the artifact
changes."

Flywheel gets that for free, but only in one of the two available shapes:

```
committed test file, discovered by config.verify
  → every later goal's gate re-runs it, forever
  → a phase-6 regression that breaks phase-2's outcome FAILS A GATE

ad-hoc command named only in the outcome goal's acceptance
  → runs once at settle, then never again
  → plan stamped `status: done` against evidence that is already stale
```

So the outcome check MUST land as a committed test the repo's own suite picks up
(here, a root `test_*_policy.py`; in a target repo, whatever `config.verify`
discovers). An outcome bullet whose command is not reachable by `config.verify`
as written is a contract defect, caught by the reality check's existing
acceptance-runnability item — no new check needed, just the requirement stated.

Corollary for the authoring side: outcome bullets are DRIVABLE-SURFACE checks,
never code-reading checks. The weakening taxonomy already treats
drivable-surface → code-reading as a downgrade for amends; this states it as the
bar at original authoring too. It is also what makes the resolved open question
about implementer visibility safe — if the sample is visible and the only way to
pass it is to drive the real surface, then targeting the sample IS building the
behavior.

### A gap in the whole outcome outranks the capture bar

Added 2026-08-29. v12.3.0 shipped the day after this plan was drafted and changed
settle triage underneath it: Report-only became the DEFAULT disposition, with
"unsure → Report-only" and an earning token required before anything reaches the
inbox. That was the right fix for its own problem (1.5–2.5 inbox lines per goal,
mostly nits).

But it points against this article's central finding, which is that agents
systematically UNDER-account for what remains. The two pressures are not actually
in conflict once the instruments are separated:

```
capture bar    filters NITS out of the inbox        (v12.3.0, correct)
outcome check  catches WHOLE-OUTCOME gaps           (this plan)
```

The failure mode is the seam between them: an implementer who is unsure whether a
gap is real now defaults to burying it in a report file. One narrow rule closes
it, and it belongs here rather than as a standalone dispatch edit, because it only
has meaning once outcome bullets are executable:

> An item that would falsify a plan outcome bullet is never Report-only. It is a
> live defect by definition and earns its inbox line regardless of the
> implementer's certainty — "unsure → Report-only" does not apply to the whole.

This does not loosen the capture bar for anything else. Nits, latent findings, and
contract-mandated tradeoffs stay Report-only exactly as v12.3.0 has them.

### Enforcement lands in the red-team because the waiver cannot reach it

The teeth go in the red-team, matching how the existing reality-check items are
each mirrored by a red-team item. Full file list for the chain:

```
modified  test_self_heal_policy.py                 its "eight checks" guard pins the
                                             old count — update in the same change
modified  skills/define-goal/SKILL.md      — amend step 4 gains the ratchet
                                             classification + the note records it;
                                             reality check gains item 10
                                             (amend-only); header "eight"→"ten";
                                             drain waiver: a Ratchet finding is
                                             contract-blocking
modified  agents/contract-red-team.md      — item 15, Ratchet: given the previous
                                             contract, flag any weakened criterion
modified  skills/ideate/references/plan-template.md
                                           — outcome bullets carry commands; the
                                             outcome check is the final phase;
                                             bullets are drivable-surface checks
                                             reachable by config.verify
modified  skills/ideate/SKILL.md           — step 2 scope check mints the outcome
                                             phase at 3+; step 6 self-review checks
                                             fail-at-base; iterating an existing
                                             plan ratchets its outcome bullets
                                             against their previous commit
modified  skills/dispatch/SKILL.md         — plan mirror states what done now means;
                                             settle triage: an outcome-falsifying
                                             item is never Report-only
created   test_ratchet_policy.py           — placement guards for phase 1 (goal
                                             contracts AND plan outcome bullets)
created   test_outcome_check_policy.py     — placement guards for phases 2-3
                                             (incl. committed-test form and the
                                             Report-only carve-out)
modified  CLAUDE.md, CHANGELOG.md, .claude-plugin/plugin.json  — v12.4.0
                                             (v12.3.0 shipped 2026-08-28)
```

The red-team is chosen deliberately: `skills/define-goal/SKILL.md:1013-1021` says
the waiver runs it UNCHANGED. Anything placed there is something self-heal cannot
skip. Putting the ratchet only in amend step 4 would leave it waivable.

### The two changes protect each other

Without the ratchet, self-heal could classify a failing outcome check as
`GOAL_UNREACHABLE`, route it into amend, and weaken the very check that was
measuring the whole — turning change 1 into ceremony. Ship them together.

The 2026-08-29 amendment adds the second half of that argument. A ratchet on goal
files alone leaves the plan as an unguarded upstream source: soften the bullets
there and the derived contract is weaker without any amend ever happening. So the
two routes to a lowered bar are:

```
route A  amend the goal contract     → closed by Phase 1 (goal-file ratchet)
route B  soften the plan's bullets   → closed by Phase 3 (plan ratchet)
```

Closing only one is closing neither, which is why Phase 3 is not optional
polish.

### Patterns to follow

- Policy-test shape: `test_self_heal_policy.py:1-30` — module docstring naming the
  forensic grounding, an explicit SCOPE paragraph conceding that text presence is
  not meaning, `read()`/`unwrapped()` helpers, one assertion per rule with a
  takeaway-named test function.
- Behavior tests that import a script: `test_contract_scope_policy.py:32-40`
  (`importlib.util.spec_from_file_location`) — only needed if a phase touches
  Python, which none of these do.
- Reality-check item shape: `skills/define-goal/SKILL.md:713-782` — each item is a
  named check, one line of what it catches, and what verdict it produces.
- Red-team item shape: `agents/contract-red-team.md:17-106` — numbered, named, one
  paragraph, states whether it is contract-blocking or advisory.

## Open questions

All three resolved 2026-08-28 by the owner: "go with your recommendations".

### RESOLVED 2026-08-28 — What `type:` does a verification-only goal get?
- `type: chore` — closest existing shape (mechanical checks, no new behavior) and it
  stamps the medium tier, which suits running named commands. One sentence is added to
  define-goal's type-shape rule so the red-team's Type shape item does not reject a
  verification goal for lacking a "no behavior change" proof. Rejected: a new
  `type: verify`, which would ripple through define-goal, the red-team,
  `pg_validate.py`, and every rule keyed on the three existing types.
  (owner: "go with your recommendations")

### RESOLVED 2026-08-28 — Do phase implementers see the outcome check?
- Yes — it stays in the plan, which dispatch's implementer brief already tells them to
  read, so each phase's implementer knows what the whole is for. Factory's sealed-wall
  rule exists because their implementer reverse-engineers a binary from a sparse
  sample; here the checks are end-to-end outcomes of features being built deliberately,
  so hiding them costs orientation and buys nothing the ratchet does not already cover.
  (owner: "go with your recommendations")

### RESOLVED 2026-08-28 — Is RETIRE under the ratchet?
- Yes — retire under the drain waiver requires the disproving evidence to be a command
  output or a quoted primary artifact recorded in the retire reason; an agent's own
  reasoning as the sole evidence stops for the owner. Retire is the largest possible
  weakening: the whole contract disappears, terminally and unrequeueably. The reality
  check's Premise item verifies a premise when a goal is WRITTEN, which is not the same
  as verifying it when the goal is DESTROYED.
  (owner: "go with your recommendations")

## Phases

Phases 1 and 2 are independent and may run in either order or concurrently.
Phase 3 depends on both. Phase 5 is the outcome check and depends on everything.

- [x] Phase 1: A weakening amend stops for the owner; a tightening one still runs unattended
  - Files: `skills/define-goal/SKILL.md` (amend step 4 ratchet classification,
    amendment-note format, reality-check item 10 amend-only, header count fix,
    drain-waiver blocking clause, retire-evidence rule per the resolved question);
    `agents/contract-red-team.md` (item 15); `test_ratchet_policy.py` (new)
  - Verify: `uv run --with pytest --python 3.13 pytest -q test_ratchet_policy.py` ·
    plus a subagent dry-run on one weakening and one tightening amend scenario, each
    with a RED baseline against `git show HEAD:skills/define-goal/SKILL.md`
    · **needs independent review** on whether the weakening list is exhaustive

- [x] Phase 2: A 3+-phase plan carries an executable outcome check as its final phase
  - Files: `skills/ideate/references/plan-template.md` (outcome bullets carry
    commands, fail-at-base rule, outcome check as final phase, bullets are
    drivable-surface checks reachable by `config.verify` as written);
    `skills/ideate/SKILL.md` (step 2 scope check at 3+, step 6 self-review);
    `test_outcome_check_policy.py` (new, incl. the `-k committed` guard)
  - Verify: `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py`
    · plus a subagent dry-run producing a plan for a 3-phase idea, RED-baselined
    against `git show HEAD:skills/ideate/references/plan-template.md`

- [x] Phase 3: A plan's outcome bullets are ratcheted the same way a goal's criteria are
  - Depends on: Phase 1 (the taxonomy it reuses), Phase 2 (the bullets it guards)
  - Files: `skills/ideate/SKILL.md` (iterating an existing plan classifies every
    outcome-bullet edit as weakening or tightening against
    `git show HEAD:docs/goals/plans/<file>.md`; weakening stops for the owner);
    `agents/contract-red-team.md` (item 15 covers a plan-derived outcome goal whose
    bullets were weakened since the previous commit); `test_ratchet_policy.py`
    (extend, the `-k plan` guard)
  - Verify: `uv run --with pytest --python 3.13 pytest -q test_ratchet_policy.py -k plan`
    · plus a subagent dry-run on a plan iteration that deletes one outcome bullet
    and one that adds a command to a vague bullet, RED-baselined against
    `git show HEAD:skills/ideate/SKILL.md`
    · **needs independent review**: this is the phase that closes the back door, so
    a reviewer should try to find a route from a softened plan to a passing outcome
    check that the rule does not catch

- [x] Phase 4: define-goal contracts the outcome phase, done means passed, and a whole-outcome gap always surfaces
  - Depends on: Phase 2
  - Files: `skills/define-goal/SKILL.md` (plan-backed fast path handles the outcome
    phase; one type-shape sentence admitting a verification goal as `type: chore`);
    `skills/dispatch/SKILL.md` (plan mirror states what `status: done` now means;
    settle triage gains the carve-out — an item that would falsify a plan outcome
    bullet is never Report-only, regardless of certainty);
    `test_outcome_check_policy.py` (extend, the `-k report_only` guard)
  - Verify: `uv run --with pytest --python 3.13 pytest -q test_outcome_check_policy.py`
    · plus a subagent dry-run converting a plan whose final phase is an outcome
    check, and one triaging an outcome-falsifying finding an implementer flagged as
    unsure — RED-baselined against `git show HEAD:skills/dispatch/SKILL.md`, which
    currently routes it to Report-only by default

- [x] Phase 5: The whole thing works end to end, and ships
  - Depends on: Phases 1-4
  - This is the plan's own outcome check — verification only, builds nothing
  - Files: `CLAUDE.md` (all rules, corrected reality-check count);
    `CHANGELOG.md`; `.claude-plugin/plugin.json` (v12.4.0)
  - Verify: every command in `## What will be true when done` above, run in order,
    each shown failing at this plan's amended base commit `4007651` and passing at
    HEAD · `uv run --with pytest --python 3.13 pytest -q` green and never below 360
    tests · `plugin-dev:plugin-validator` clean · tag + GitHub release per the
    repo's release rule
