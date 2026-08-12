# v11.0.0 — the plan release: riptide's design tier on flywheel's autonomous gate

Date: 2026-08-12 · Owner decision: 2026-08-12 ("superpowers-like plan file; robust
planning, robust execution, robust audit, goal completion with parallel; fewer
questions, fewer warnings, faster completion")

## Evidence base

Two sources, both examined in full on 2026-08-12:

1. **HumanLayer's RPI plugins** (`riptide-rpi` 0.35.0, `riptide-rpi-terminal`
   0.30.25) plus a REAL worked example: RPI's research → design-discussion pipeline
   run against the owner's own romy repo (kernel-audit atomicity, GitHub issue #69).
   The design discussion it produced resolved SIX design forks — each with options,
   a recommendation, and a user-resolve-only gate — before any contract existed,
   citing romy's own flywheel goal history (goals 039/040/043) as design input.
2. **Forensics across the factory's 7 real repos** (386 goals ever created; 335
   measured claim→settle cycles from git history; 109 implementer reports; 598
   filtered owner prompts from ~330 MB of session transcripts).

### What the forensics showed

- **Cycle time is fine and improving; the TAIL is the pain.** Median claim→settle
  52.7 min overall, trending 85.7 → 55.1 → 39.4 min by month; August drain days
  settle goals in 10–25 min. But the MEAN is 114 min, and goals that block on a
  contract defect take **10–85 hours** first-claim→final-complete (romy 047: 85.1 h,
  3 block/amend rounds; nonresidenttax 113: 57.7 h, 3 rounds; nonresidenttax 052:
  46.7 h). Every amend round drags the owner in. The owner's "2–3 hours minimum"
  is the mean plus this tail plus his own forced participation — the 57-min median
  the factory previously celebrated measured the wrong thing.
- **The thrash is design debt, not implementation debt.** Both currently-blocked
  goals in the whole estate (ideation 013, 015) are contract-AMBIGUITY stops — e.g.
  013's block reason is literally a design fork ("derive-it (unreachable) or
  author-it (circular oracle)"). nonresidenttax 042's implementer disproved the
  goal's own premise with an A/B measurement. These forks are exactly what a
  design-tier document with open questions resolves for pennies BEFORE contracts
  exist — and exactly what RPI's design discussion did resolve on romy.
- **Goal files are 75–85 % ceremony.** Median 115–160 lines across all repos; only
  ~25–30 lines per file are unique intent. `## If blocked` is byte-identical
  boilerplate file-to-file; `## Goal contract` restates the acceptance criteria
  above it (and its 4,000-char `/goal` cap broke on the owner once — "got 6512").
  The gate (`pg_validate.py`) reads ONLY frontmatter (`type`, `touches`,
  `acceptance`, `already_correct`) — never the body — so the diet is gate-safe.
- **The warnings are structural.** DONE_WITH_CONCERNS is ~30 % of determinable
  report statuses; 75 % of reports contain an explicit "did not / skipped"
  statement. Most of that is HONEST scope discipline (out-of-scope honored,
  pre-existing failures named) — but it lands on the owner as "x y z things
  remaining, not completed", his verbatim 2026-08-06 complaint.
- **The question burden is the owner's #1 standing objection.** "Don't ask me,
  you decide" appears independently in nonresidenttax, romy, soloreza, and
  flywheel sessions; his prompt vocabulary is ops language (fix / staging / push /
  full complete) and contains ZERO contract vocabulary. v10 fixed mid-cycle asks
  (0 genuine post-v10, measured) — define/ideate/amend interviews are what remain.
- **v10's rails work.** A real 20-goal post-v10 drain ran with zero stops; inbox
  capture works (romy 164 lines, pricing-test 35). The execution layer is not the
  problem. The design layer above it is missing.

### What RPI has that flywheel lacked (adopting)

1. A **code-shaped design altitude** below prose: type/method signatures, file-tree
   diffs, call flows — "header files, not function bodies".
2. A **vertical-slice mandate** on decomposition, with the horizontal
   counterexample stated and a mechanical test.
3. **Design questions as durable state**: OPEN/RESOLVED in the document, agent
   recommends, only the owner resolves, resolved questions keep their why.
4. **Headers state the takeaway**, not the topic.
5. A **living plan document**: phase checkboxes flip as work completes, so one
   document shows the whole effort's progress.

### What RPI has that flywheel must NOT adopt (rejected)

- **Four-plus artifacts per effort** (research-questions, research, PRD, TDD,
  outline, plan). One plan document carries the value; HumanLayer's own later
  writing blames instruction-budget overflow for RPI breaking at scale.
- **Human-gated per-phase execution.** RPI pauses for manual human verification
  between EVERY phase — the exact opposite of what this owner wants and what
  dispatch's autonomous local gate already does better (RPI has no adversarial
  gate at all; it trusts the implementer plus the human).
- The 12 `iterate-*` twin skills, the cloud/hook substrate, per-phase PR ceremony.

## The design

**One new artifact — the PLAN — and a question/ceremony diet everywhere else.**
The plan is the unit of design and review; the goal becomes a thin, cheap slice of
a plan. Quality ceremony moves from per-goal (N interviews, N contract
negotiations) to per-plan (one design, one touch). Dispatch's invariants (local
gate, serial integration, claim ledger, rollback, drain, settle triage) are
untouched — they are the part that measurably works.

### 1. The plan artifact (`docs/goals/plans/YYYY-MM-DD-<topic>.md`)

Written by ideate (which previously wrote the under-one-page "design brief" —
plans replace briefs; existing briefs stay valid where linked). Template ships at
`skills/ideate/references/plan-template.md`. Sections:

- frontmatter: `topic`, `created`, `status: open|approved|done`, `repo`, `branch`
- `## What we're doing` — 2–4 sentences in the owner's language
- `## Current state` — product-behavior altitude first, then Key discoveries with
  `path:line`
- `## What will be true when done`
- `## What we're NOT doing` — mandatory, never empty
- `## Design` — takeaway headers; code-shaped where the work touches existing
  code: exact signatures in fenced blocks (bodies elided), a file-tree diff
  (created vs modified, one line each), a call-flow sketch only where control flow
  is non-obvious. Altitude rule: signatures and shapes, never function bodies.
- `## Open questions` — every design fork the exploration raised, each OPEN or
  RESOLVED. The agent recommends an option; ONLY the owner resolves. "Go with
  your recommendations" resolves all open questions at once and is recorded as
  such. A resolved question keeps a one-line why. A plan may ship with questions
  still OPEN — an open question is information, not a blocker.
- `## Phases` — vertical slices, each mapping 1:1 onto a future goal: takeaway
  title, file changes (one line per file, signatures optional), the exact
  acceptance commands, `- [ ]` checkbox. Slice test: if a phase cannot be
  verified without a LATER phase existing, it is not a slice.

Scope guard: plans are for chains (2+ goals) and design-heavy work. Shaped wants
still skip ideate entirely; single-goal outcomes stay fileless. Under ~2 pages.

### 2. ideate — single-touch design gate

- Exploration questions collapse into the plan's Open-questions section: at most
  ONE AskUserQuestion round during exploration (only for a fork that blocks
  writing the design at all); everything else becomes an Open Question with a
  recommendation. The plan presentation is the ONE owner touchpoint: the owner
  answers any subset, or says "go with your recommendations", or parks the idea.
- Vertical-slice rule governs the decomposition step, horizontal counterexample
  named ("all schema → all API → all UI" produces nothing verifiable until the
  end).
- Every heading ideate writes states its takeaway.

### 3. define-goal — plan-backed fast path + goal-file diet

- **Plan-backed wants get ZERO question rounds.** The plan is the interview;
  recon narrows to verify-and-complete; batch mode uses the phases as the item
  list; ONE red-team pass covers the whole plan-derived batch (already batch
  behavior). Each goal's Context links the plan (`Plan: docs/goals/plans/…` +
  which phase) — the plan's Design section replaces per-goal re-derived
  Interfaces prose.
- **Goal template diet (all queued goals):** cut `## If blocked` (it was
  byte-identical boilerplate; the same rules already live in dispatch's
  implementer brief, which every implementer receives) and cut `## Goal contract`
  for QUEUED goals (dispatch's implementer works from the acceptance criteria;
  the `/goal` line remains the run-now destination only). Keep: frontmatter,
  Outcome, Context, Acceptance criteria, Constraints, Out of scope. Target ≤60
  lines. Old-format goals stay valid everywhere.
- **Red-team Slice check** (new, sits beside the Size check): a goal whose
  acceptance criteria cannot be satisfied without a goal LATER in its own chain
  is a horizontal cut → contract-blocking, with the proposed re-cut. A Context
  note explaining why the layer split is forced downgrades it to advisory.
- **Non-plan wants:** the question round asks only questions whose answer has no
  confident recommended default; when every question has one, skip the round,
  state the assumptions in the draft confirmation (still exactly one
  confirmation touch).
- **Amend mode question diet:** when the block reason plus the goal file (plus
  the linked plan, if any) make one reading clearly recommended, take it, record
  it in the amendment note, and present the amended contract as the single
  confirmation — the question round happens only when the fork is a true owner
  decision (spend, data loss, irreversible/externally-visible behavior).

### 4. dispatch — plan-aware execution, concerns diet, parallel by default

- **Implementer reads the plan.** When the goal's Context links a plan, the brief
  has the implementer Read it (Design + its own phase) before starting — no more
  re-deriving a sibling's interfaces.
- **Brief anchor fix:** implementers work from the goal's Acceptance criteria
  (older goals may still carry a Goal-contract section; same content).
- **DONE_WITH_CONCERNS redefined (the concerns diet):** the status is legal ONLY
  when a concern qualifies THIS goal's own contract (a criterion met but fragile,
  an assumption that could invalidate one). Honored out-of-scope boundaries,
  pre-existing baseline failures, and discovered follow-ups are NOT concerns:
  the first two belong in the report file, the third in settle-triage capture.
  Everything else is a plain DONE. (Measured: ~30 % of reports ended
  DONE_WITH_CONCERNS; most concern text was honest scope discipline reading as
  incomplete work.)
- **Flagless drain auto-parallel:** when `config.parallel` exists in the queue
  (the repo owner's standing opt-in) and ≥2 ready goals are co-schedulable under
  the untouched admission rules, a flagless drain runs them as `--parallel`
  waves; serial otherwise, and `--serial` forces it. Admission control,
  integration lock, and every parallel-mode ruling are unchanged.
- **Plan phase mirror (display only, self-healing):** on completing a plan-backed
  goal, flip that phase's `- [ ]` to `- [x]` in the plan file in the same settle
  commit. `index.yaml` stays the ONLY status authority; Phase 0's doctor pass
  re-syncs a drifted plan checkbox in the plan direction only. When every phase
  is checked, stamp the plan `status: done`.

### 5. Deliberately unchanged

- The local gate, both arms, budgets, and calibration text (v5.3.0–v8.3.0 scar
  tissue).
- The claim protocol, statuses, status-only-in-index, settle triage + inbox,
  escalation ladder, heartbeat/brake.
- Recon defaults and tier routing (gather medium, judgment session model).
- The always-skip path: shaped wants never bounce through ideate; run-now `/goal`
  destination and its evaluator facts.
- Droid dual-target architecture (plans are markdown — harness-neutral by
  construction; auto-parallel stays Claude-Code-only exactly as `--parallel` is).

## Testing (repo doctrine: dry-run + RED baseline)

Each compliance-critical rule gets a Sonnet subagent dry-run ("cite the section
that decides each answer") against the NEW text and a RED baseline against
`git show HEAD:<file>` proving the old text decided differently or left it
undecided:

1. Slice check — fixture pair: horizontal chain (must block), vertical chain
   (must pass).
2. Plan-backed zero-questions — scenario with an approved plan; old text runs
   the interview, new text must not.
3. DONE_WITH_CONCERNS definition — an honored out-of-scope refusal; old brief
   permits DWC, new brief requires DONE + report.
4. ideate one-touch approval — "go with your recommendations" resolves all open
   questions; old text keeps serial rounds available.
5. Auto-parallel drain — `config.parallel` present, flagless `/dispatch`; old
   text runs serial, new text runs waves.
