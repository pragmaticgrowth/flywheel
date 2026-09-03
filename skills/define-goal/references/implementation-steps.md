# Implementation steps — the executable plan inside every queued goal (canonical)

Read this file when drafting the `## Implementation steps` section of a queued goal
(define-goal, queue destination) and when amending one (`--steps <id>`). Adapted from
superpowers' writing-plans skill: the section is written for an engineer who is
skilled, has ZERO context on this codebase, questionable taste, and no time to think —
which is exactly what a medium-tier implementer on medium reasoning is. Every design
decision was made upstream (ideate's plan, this skill's recon and question rounds);
the steps are what is left when nothing remains to decide.

The acceptance criteria say WHAT must be true; the steps say HOW, file by file, in
the order the work is done. The gate still judges the criteria — the steps are the
implementer's script, never a second contract. Bugs the gate misses are fixed in the
next goal; the steps exist so the sitting is short, not so it is perfect.

## The shape

```markdown
## Implementation steps

Files:
- Create: `apps/product-data/src/federal-tax/views.ts` — <one line: what it is for>
- Modify: `apps/product-data/src/index.ts:142-158` — <one line: what changes>
- Test:   `apps/product-data/src/federal-tax/__tests__/views.test.ts`

Interfaces (only on a `depends_on` chain):
- Consumes: `listCustomerFilings(customerId: string): Promise<FilingRow[]>` from goal 237
- Produces: `GET /customer/:id/federal-tax` returning `FilingView[]` — goal 239 reads it

### Task 1: <takeaway — what works after this task>

- [ ] Step 1 — write the failing test in `<test path>`:
  ```ts
  <the actual test code — complete, runnable, no "..." inside>
  ```
- [ ] Step 2 — run `<exact command, scoped to that file>` — expected: FAIL, `<the
  message or assertion that fails>`
- [ ] Step 3 — implement in `<path>` (new code shown whole; an edit shown as the
  exact before/after or a unified diff, anchored on a line that exists at HEAD):
  ```ts
  <the actual code>
  ```
- [ ] Step 4 — run `<same command>` — expected: PASS
- [ ] Step 5 — `git add <exact files> && git commit -m "<message>"`

### Task 2: <takeaway>
…
```

Each task is one test cycle: failing test → run → implement → run → commit (five
steps, two to five minutes each for the implementer). Fold setup, config, scaffolding,
and docs into the task whose deliverable needs them. Split tasks only where one could
be reverted while its neighbor stands.

## Rules

1. **No placeholders — ever.** These are DEFECTS, and the red-team blocks on them:
   "TBD", "TODO", "implement later", "add appropriate error handling", "handle edge
   cases", "add validation", "write tests for the above" (without the test code),
   "similar to Task N" (repeat the code — the implementer reads tasks in order but
   forgets), a step that says what to do without showing how, a reference to a type,
   function, or module no task and no existing file defines, a `Modify:` line with no
   line range, a command whose expected output is not stated.
2. **Code is real code.** New files and functions appear WHOLE. Edits to existing
   code show the exact lines being replaced (copied from HEAD, from recon's excerpt)
   and the exact replacement — the implementer's job is transcription plus a scoped
   test run. Signatures elided with `{ ... }` belong in ideate's plan, never here.
3. **Every path exists or is declared Created.** `Modify:` paths carry a line range
   that exists at HEAD (recon supplies it; the reality check verifies it). A moved
   line range is the ONE thing the implementer may adjust on its own.
4. **Every command is exact and scoped** — the package's own test runner pointed at
   the one test file, never the repo pipeline (the gate runs that). State the expected
   result for each run: FAIL with what, then PASS.
5. **A step that needs a decision is a fork, not a step.** If you cannot write a step
   without choosing between two designs, stop drafting: on a plan-backed goal that is
   a plan gap (add the question to the plan's Open questions, or fix the plan if it is
   an error); otherwise it is the one legitimate reason for a question round. Never
   paper over it with "choose the appropriate approach".
6. **Follow the house pattern, and show it.** Where recon-patterns found the existing
   implementation to imitate, the step's code follows it and the task header cites
   it (`path:line`). The implementer never has to go looking.
7. **Length is not a defect.** The contract sections above the steps stay on the
   goal-file diet (≤60 lines); the steps run as long as executability needs — a
   complete five-task goal is often 150–250 lines. Duplicated boilerplate and
   restated system rules are still defects; a full function body is not.

## Self-review before the red-team (inline, no subagent)

- **Coverage:** point at the task that makes each acceptance criterion true; a
  criterion with no task is a gap — add the task.
- **Placeholder scan:** search the section for every pattern in rule 1.
- **Type consistency:** names, signatures, and return types used in a later task
  match what an earlier task (or HEAD) defines — `clearLayers()` in Task 2 and
  `clearFullLayers()` in Task 4 is a bug.
- **Runnable as written:** every command's runner reaches the named test file from
  the repo root with the config the command names.
- **Commit hygiene:** every task ends with a commit naming its files.

Fix inline and move on — the red-team's Executability item is the second view.

## Where the material comes from

Recon (define-goal's fan-out) is briefed to return, besides its usual findings, the
CURRENT code of every block the goal will change — 20–60 lines each with `path:line`
— and the house pattern the new code should copy, with its code. On a plan-backed
goal ideate's plan already holds the signatures, the file diff, and the Patterns to
follow; recon narrows to fetching the exact current lines. The steps are then written
on the session model — the strongest model in the session, the thinking spent once
where it is cheapest — so that dispatch can hand the goal to a medium-tier
implementer and expect a short, straight sitting.

## Old-format goals

A queued goal without this section stays valid: dispatch's implementer works from the
acceptance criteria as before (on the goal's stamped tier — usually heavy). Adding the
section to a queued `not_started` goal is `/define-goal --steps <id>` (or `--steps all`
for every queued goal lacking one): recon, steps, red-team on Executability only,
re-stamp `model:`, one commit `chore(goals): amend <id> — steps`. Criteria stay
byte-for-byte; no requeue is needed.
