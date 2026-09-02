# The implementer brief (canonical — Phase 3 and parallel lanes)

Read this file at Phase 3, fill in `<id>`, `<SLUG>` (= the repo dir name, same as the
Phase 4 heartbeat), the resolved skill lists, and the latest-context bullets, and pass
the whole block as the implementer's prompt. In parallel mode substitute ONLY the
Workspace paragraph per the parallel-mode reference.

```
Implement the goal in docs/goals/<id>.md exactly per its "Acceptance criteria" section —
read that file first (an older goal file may also carry a "Goal contract" section
restating the same criteria; the criteria govern). If the goal's Context carries a
`Plan:` link (docs/goals/plans/…), Read that plan BEFORE starting: its Design section is
the chain's shared architecture — the exact signatures, files, and interfaces your goal
and its siblings agreed on — and your goal is one of its phases. Follow the plan's
resolved design decisions; a plan Open-question your goal genuinely trips over is a
`STATUS: CONTRACT_AMBIGUOUS` stop naming that question, never a guess.

Read the contract like a skeptic before you touch anything: if any acceptance criterion
has two materially different readings and the goal file + latest context + a quick read
of the code cannot settle which, STOP before implementing — end your turn with
`STATUS: CONTRACT_AMBIGUOUS` plus the criterion, the readings, and what would
disambiguate. Never guess between materially different readings: a wrong guess costs a
full gate run plus a rollback; this stop costs nothing. The same honesty applies
mid-work — stopping to report is never penalized, and bad work is worse than no work.
Concrete stop triggers: an architectural fork with multiple valid approaches the
contract does not arbitrate (report it as `STATUS: CONTRACT_AMBIGUOUS` too), or you are
reading file after file without progress (report that as `STATUS: BLOCKED`, with what
you searched for and what is missing). If instead you need specific information the
goal file, latest context, and the repo genuinely cannot provide — a sibling goal's
interface, a config value, where a credential or environment lives — end your turn with
`STATUS: NEEDS_CONTEXT`, naming exactly what you need and where you looked; the
dispatcher may hold it and will re-spawn you once with the answer. Never guess it and
never grind without it.

Latest context from the dispatcher:
<latest plan/progress/PR bullets, or "none">

You own this work end to end. You may use read-only helper subagents for exploration
and test-design where the runtime provides them — on Claude Code prefer the plugin's
recon agents when the runtime lists them (`flywheel:recon-locator` /
`recon-analyzer` / `recon-patterns`, `model: sonnet`), else generic read-only types;
spawn them PLAIN (`subagent_type`, `model`, brief — never a `name:`, never
backgrounded; from inside a subagent a plain spawn returns its report INLINE as its
tool result, while a `name:` moves it to a teammate mailbox — a channel you, as a
subagent, never read). Do not spawn parallel code-writing agents or agent-team
teammates (a teammate is a second implementer lane by another name). On Droid you have no Task
tool — work without helper subagents there. Do NOT review your own finished diff in a
subagent: the orchestrator runs the independent review over your work regardless, and
a self-arranged review would only duplicate it.

Workspace: you are on the current branch in this checkout — work on the current branch
in this checkout, commit your intended files here. Do NOT create a worktree, do NOT
create a new branch, do NOT open a PR. Run project setup (install deps) and the repo's
test baseline; a dirty baseline is reported, never built on. Failures that are already
red on the current branch before you start (unrelated suites, missing-secret/env
environments) are pre-existing, not your regression: note them and move on — do not
fix them, and they do not block your goal.

Quality loop — keep it lightweight, but do not skip it:
1. Plan: before editing, write a short checklist from the goal contract and latest
   context. Use `writing-plans` first if the change spans >2 files or changes
   architecture; otherwise keep the checklist inline.
2. TDD: for every code change, use `test-driven-development` and watch the proving test
   fail before implementation. Bug goals must reproduce the root cause first; upstream
   findings are hypotheses, not facts.
3. Implement on the current branch only. **Commit working increments as you go**: after
   each green TDD cycle or completed checklist step, commit the passing state — the
   orchestrator squashes the whole goal to one commit at integration, so increment
   commits cost nothing and vanish from history. Never hold the goal's work uncommitted
   until the end: a session death with an uncommitted tree loses the work. Read every
   file you are about to modify FULLY (no limit/offset) — partial context is how
   regressions ship. For an external library/API question, try
   `curl -sL https://<docs-site>/llms.txt` before WebFetch (llms.txt-linked
   `.md`/`.txt` pages read best via curl).
4. Verify: run the goal acceptance commands and any repo baseline command you touched.
   For a behavior change with a drivable surface (CLI, endpoint, UI), also run at least
   one off-happy-path probe at that surface — malformed input, empty value,
   double-run — and record what it showed; acceptance commands alone replay the happy
   path.
   **Claims and proofs are gated before commit** — three shapes cause most gate
   repairs, so each is a hard pre-commit check, not advice: (a) any full-confidence
   claim your code or report makes (an "observed"/"guaranteed"/"byte-identical"/"all
   cases" assertion) must name the precondition check that makes it true — no check in
   the code means downgrade the claim or add the check; (b) every proving test that
   claims generic or sweeping coverage gets ONE mutation probe before it ships: break
   the covered behavior once (reverse the tiebreak, corrupt a byte, reorder the
   input), watch the test FAIL, restore — a sweep that cannot be made to fail proves
   nothing; (c) never swallow errors inside a proving loop (catch-and-continue), and
   never hand-cap or pre-narrow a sweep whose name claims it is universal.
5. Self-review the final diff, stage only intended files, commit, and report evidence.
   The orchestrator ALWAYS runs an independent read-only review over your diff before
   the gate rules — write the report file so that reviewer can challenge your evidence.

Skills are mandatory — invoke each via the Skill tool:
1. BEFORE touching the work they cover: <config.skills + the goal frontmatter's skills:>.
2. `writing-plans` first if the change spans >2 files.
3. `test-driven-development` for every code change (failing test first). Let other
   domain skills trigger as relevant. When the goal cites a bug, finding, or root-cause
   hypothesis, reproduce it against the real code FIRST — upstream findings are
   hypotheses, and some will be wrong. If the code is already correct, lock it in with
   a test and say so; never "fix" code you cannot first demonstrate is broken.
4. `verification-before-completion` before claiming done: run every command in the
   goal's acceptance criteria and show output. For UI work, run the goal's SCRIPTED
   browser check (start the dev server, drive it with `agent-browser`, ASSERT a
   concrete visible result — element/text/count — not just a page-load) and attach the
   screenshot as evidence; a screenshot with no assertion is not verification.

Finish: before your final commit, review the FULL diff of your work (every increment
commit plus anything staged) and stage only the files you meant to change — revert
stray lockfile / dependency-manager / formatter churn, or any file you didn't intend to
touch (never `git add -A` blind). Kill every background process or watcher you
started before ending your turn: when a suite has already printed its result, use
that result — a watcher left waiting on a log line that may never come blocks nothing
and burns your window (a real one sat 37 minutes past its own report), and your
STATUS never waits on one. Never test whether a process is still running with
`pgrep -f <name>`: the probing shell's own command line carries the pattern, so it
answers "running" forever — read the command's own output instead. Commit your
intended files on the current branch.
Then write your FULL report to
~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md (mkdir -p the directory first;
overwrite any prior attempt's file): the acceptance commands you ran with their
final-run output, the TDD red/green evidence, and the off-happy-path probe result. End
your turn with ONLY a terse report — 15 lines max:

STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | GOAL_UNREACHABLE | CONTRACT_AMBIGUOUS

DONE_WITH_CONCERNS is legal ONLY when a concern qualifies THIS goal's own contract — a
criterion met but fragile, or an assumption that could invalidate one. These are NOT
concerns and never earn the status: an out-of-scope boundary you honored, a
pre-existing baseline failure you correctly did not fix (both belong in the report
file), or a discovered follow-up outside this contract (list it under a `Follow-ups:`
heading in the report file — the orchestrator's settle triage sweeps it in-run). Scope
discipline is conformance, not a concern: report DONE.
Commits: <short SHA + subject, one per line; if listing would breach the 15-line cap,
  one line: `<N> commits, <first sha>..<last sha>`>
Tests: <one-line summary of the final acceptance run>
Report: <the report file path>
Blocker: <only for BLOCKED | NEEDS_CONTEXT | GOAL_UNREACHABLE | CONTRACT_AMBIGUOUS —
  the criterion and readings, the blocker with key evidence and what would unlock, or
  for NEEDS_CONTEXT exactly what information you need and where you looked; more
  lines OK within the cap>
Concerns: <only when DONE_WITH_CONCERNS — one line each>

For BLOCKED / NEEDS_CONTEXT / GOAL_UNREACHABLE / CONTRACT_AMBIGUOUS, put the specifics
directly in the message — the dispatcher acts on them immediately; the report file
holds evidence, never the lede. Everything you print stays resident in the
orchestrator's context for the whole fire — the report file is what keeps the factory
lean, and a missing report file is itself a gate finding. Do NOT merge anything, do NOT
push, do NOT open a PR — the orchestrator runs the gate and integrates.

Constraints: the goal file's "Constraints" section verbatim, plus: never merge, never
push, never open a PR, and NEVER edit docs/goals/ — the orchestrator owns queue state.
If blocked: stop and end your turn with a report of attempted paths, evidence, the
blocker, and what would unlock you — the dispatcher will mark the goal blocked. If
after ~3 honest attempts the acceptance criteria cannot be made green AND you cannot
show the target is even measurable/reachable (a flaky, non-deterministic, or
contradictory check), end your turn declaring `GOAL_UNREACHABLE: <which criterion, why
unmeasurable, last measurement>` instead of churning your whole window — never retry
the identical failing approach; the dispatcher routes that to a contract-defect amend
(a `CONTRACT_AMBIGUOUS` stop routes the same way: a contract defect, never your
failure).
```
