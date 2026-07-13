# Maker–Checker Validation (v5.1.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two self-grading trust gaps in the factory pipeline — dispatch's gate
gets an ALWAYS-on orchestrator-spawned independent reviewer (today the LLM review is
implementer-self-reported unless the evidence block is missing), and define-goal gets an
adversarial contract review before any goal is queued (today nothing validates the drafted
contract except prompt rules + a human glance).

**Architecture:** Both changes are prose edits to two SKILL.md files plus release sync
(manifest, changelog, README, site, root CLAUDE.md). No scripts change; no new state,
statuses, files, or schedulers. Each change adds exactly one read-only subagent at an
existing trust boundary, keeping the repo's proportionality rule.

**Tech Stack:** Markdown skills (Claude Code plugin), `plugin-dev:plugin-validator`
agent, subagent dry-runs as the test harness (this repo has no code test suite — skill
mechanics are tested by scenario + cite-the-section dry-runs per CLAUDE.md).

## Design rationale (the spec, condensed)

Motivated by a reverse-engineering comparison against Factory's Automations / Software
Factory pipeline. One structural idea survives adversarial evaluation: **maker–checker
separation as an invariant** — their Validate stage (Code Review / QA / Security Audit)
is always a separate principal from the implementation worker. In flywheel:

- The deterministic half of the gate (`pg_validate.py` + `config.verify`) is already
  independent and re-run by the orchestrator. No change.
- The semantic half (Fresh-check lens panel) is spawned and summarized by the implementer;
  the orchestrator runs it itself only when the block is missing/implausible. The party
  being graded writes the grade report. **Fix: unconditional single independent reviewer,
  with the existing 2–3-lens panel kept as the escalation for missing evidence.**
- The queue path has no second model at all between contract and completion (run-now
  `/goal` has the transcript evaluator; the queue path lost that layer). The independent
  reviewer restores parity.
- define-goal validates its inputs (recon) and its rules are strong, but its OUTPUT — the
  contract — is never checked by a fresh agent. Every `FAIL_CONTRACT` / `GOAL_UNREACHABLE`
  at dispatch time costs a full implementer run + rollback; the same defect found at
  define time costs one read-only agent. **Fix: contract red-team before queueing.**

Evaluated and REJECTED from Factory's model (reasons on record): parallel workers/PRs
(v3 scar tissue — livelocked on real runs), signal intake + triage automations
(product-scope expansion; batch mode already covers document intake with dedupe), a
per-change approval inbox (draft confirmation at define time is the same human gate,
placed earlier), dashboards/HTML visualizations (report line + Telegram is the right
unattended shape), per-automation side-memory (lesson-encoding into repo config/CLAUDE.md
is strictly better), post-completion review sweeps (validation belongs BEFORE `completed`,
at the gate), wall-clock orphan detection (our fires-observed brake is strictly better
under quota pauses).

## Global Constraints

- Skills must stay portable: no user-specific absolute paths.
- Skills-first: no new hooks, commands, agents, MCP servers.
- Review/recon agents ALWAYS inherit the session model — never `config.model` or the
  goal's `model:` (existing invariant; both new reviewers follow it).
- Status lives only in `index.yaml`; the new mechanics add NO new queue state.
- One version bump: root `plugin.json` 5.0.2 → **5.1.0** (feature, two skills).
- Site + README must be updated in the SAME change as the skill mechanics (CLAUDE.md rule).
- Every completion is committed AND pushed; version bump gets tag `v5.1.0` + GitHub
  release from the changelog section + `wrangler deploy`.

---

### Task 1: dispatch — unconditional independent review at the gate

**Files:**
- Modify: `skills/dispatch/SKILL.md` (frontmatter description; Working-a-goal steps 2–4;
  Phase 3 brief Quality-loop step 5 + Finish paragraph; post-brief paragraph)

**Interfaces:**
- Produces: the step-3 gate now reads "independent review first, then commands"; the term
  **independent review** replaces "review-evidence check" everywhere. Task 4's doc sync
  and Task 3's dry-run scenarios depend on these exact behaviors:
  (a) non-trivial diff → ALWAYS one fresh read-only adversarial reviewer, session model;
  (b) missing/implausible `Fresh-check:` block → escalate to the full 2–3-lens panel;
  (c) one-file mechanical edit → no reviewer (deterministic gate only);
  (d) verified Critical/Important findings → FAIL_FIXABLE repair path; re-gate includes a
      focused re-check of exactly those findings.

- [ ] **Step 1: Rewrite Working-a-goal step 3's review layer.** Replace the
  "Review-evidence check." paragraph with:

  ```
  **Independent review — maker–checker, ALWAYS for non-trivial work.** For any diff bigger
  than a one-file mechanical edit, spawn ONE fresh read-only adversarial reviewer
  (`general-purpose`, no model override — review agents always inherit the session model)
  over the `gate_base..HEAD` diff plus the goal file. Its brief: try to REFUTE the work,
  not confirm it — (a) contract conformance: any acceptance criterion unmet or met
  vacuously; (b) test realness: proving tests assert real behavior, not tautologies or
  mirrors of the implementation; (c) scope: changes beyond the goal's surfaces, or criteria
  quietly narrowed. Hand it the implementer's `Fresh-check:` block as corroborating
  evidence to challenge — the implementer graded its own work, so this reviewer runs even
  when that block looks clean; the block is evidence, never the verdict. It returns a
  verdict per lens plus findings with severity and `path:line` evidence. Findings are
  hypotheses to verify, not orders; verified Critical/Important findings enter the
  FAIL_FIXABLE repair path like any gate finding. A one-file mechanical edit skips the
  reviewer — the deterministic gate + `config.verify` suffice; that carve-out keeps the
  second view proportional.
  **Escalation to the full panel.** A missing `Fresh-check:` block, or a not-required claim
  on plainly multi-file work, upgrades the single reviewer to the full 2–3 read-only lenses
  (same lenses as the brief's Quality loop step 5, fresh windows, concurrent). A skipped
  implementer panel is a compliance miss: when the same miss recurs across goals in this
  session's fires (no persisted counter — session memory only, per the
  status-only-in-index rule), surface it once via Hygiene's lesson-encoding rule.
  ```

  Keep the surrounding "**Then the gate commands:**" block unchanged. Update the step-3
  lead-in from "review evidence first, then commands" to "independent review first, then
  commands".

- [ ] **Step 2: Wire the repair path re-check.** In step 4's FAIL_FIXABLE sentence, after
  "one repair agent, re-gate" add: "(the re-gate re-runs the commands; when verified review
  findings drove the repair, it includes a focused fresh re-check that exactly those
  findings are resolved — not a new full panel)". Mirror the same parenthetical in Phase 1
  item 1 where FAIL_FIXABLE is repeated.

- [ ] **Step 3: Update the implementer brief so incentives stay honest.**
  - Quality-loop step 5 ending: replace "the orchestrator checks for it and runs the panel
    itself if it is missing" with "the orchestrator ALWAYS runs its own independent
    reviewer over your diff — your block is corroborating evidence for it, never the
    verdict; a missing block escalates to a full orchestrator-run panel".
  - Finish paragraph: replace "This block is not optional — the orchestrator checks for it
    and runs the review panel itself when it is missing OR when a not-required claim
    doesn't match the diff (multi-file work claiming a one-file edit)." with "This block is
    not optional — the orchestrator independently reviews your diff regardless (your
    verdicts are corroborating evidence, not the verdict), and a missing block or a
    not-required claim that doesn't match the diff (multi-file work claiming a one-file
    edit) escalates to a full orchestrator-run panel."
  - Working-a-goal step 2: "(step 3 checks for it)" → "(step 3's independent review
    challenges it)".

- [ ] **Step 4: Post-brief paragraph + frontmatter.** In "After the implementer returns,
  run the review-evidence check and the gate yourself" → "run the independent review and
  the gate yourself"; "from an orchestrator-run review panel" → "from the independent
  review". Frontmatter description: "then the orchestrator runs the LOCAL gate
  authoritatively" → "then the orchestrator runs the LOCAL gate authoritatively — an
  independent second-view review plus deterministic checks".

- [ ] **Step 5: Self-read the diff** (`git diff skills/dispatch/SKILL.md`) for dangling
  references to "review-evidence check". Expected: none remain.

### Task 2: define-goal — contract red-team before queueing

**Files:**
- Modify: `skills/define-goal/SKILL.md` (new section before "Implementer model — decide it
  last"; flow wiring in "Brief first, then artifact"; queue-rules confirm bullet; batch
  mode step list + workflow sizing; "decide it last" ordering note)

**Interfaces:**
- Consumes: the term "independent review" from Task 1 (cross-referenced once).
- Produces: a **Contract review** section with these exact behaviors Task 3 tests:
  (a) queue destination → ALWAYS one fresh read-only red-team subagent, session model,
      before `model:` stamping and before the user confirmation;
  (b) run-now `/goal` destination → skipped;
  (c) ONE round only (review → verify findings → fix contract-blocking → proceed);
  (d) batch mode → one reviewer over ALL drafts between drafting and the approval table.

- [ ] **Step 1: Insert the new section** immediately before `## Implementer model — decide
  it last`:

  ```markdown
  ## Contract review — red-team the draft before it queues (queue destination only)

  A contract defect discovered at dispatch time costs a full implementer run plus a
  rollback (`FAIL_CONTRACT` / `GOAL_UNREACHABLE`); the same defect found now costs one
  read-only agent. So every QUEUED goal gets an independent contract review after its
  criteria are drafted — the second view on the contract itself, mirroring the independent
  review dispatch runs on the diff. Run-now `/goal` lines skip it: the user is present and
  the `/goal` evaluator model already provides a second view at run time.

  Spawn ONE fresh read-only subagent (`general-purpose`, no model override — it inherits
  the session model, same rule as recon) with the drafted goal file content. Its brief: try
  to BREAK the contract, not approve it —

  - **Gameability**: can any criterion be satisfied without the outcome being true — a
    proxy metric, a vacuous/tautological test, a drive-to-zero criterion missing its
    legitimate exceptions?
  - **Command reality**: does every command named in the acceptance criteria and
    `acceptance:` actually exist and run in THIS repo (script present in
    package.json/Makefile, test paths exist, right package manager)? Verify by reading the
    repo — read-only, no heavy runs.
  - **Type shape**: bug → `acceptance:` executes the proving test and Context records ALL
    recon hypotheses; feature → Out of scope non-empty, and UI work carries the scripted
    browser check + `agent-browser` in `skills:`; chore → suite-green-before-and-after
    plus the one mechanical check.
  - **Gate fit**: `touches:` globs cover the surfaces recon located without
    over-constraining; nothing dev-server-dependent sits in `acceptance:` (headless-only).
  - **Termination**: the `/goal` line is transcript-provable and under the 4,000-char cap,
    the turn cap is present and sized, and the If-blocked / GOAL_UNREACHABLE path exists.

  It returns findings with severity — **contract-blocking** vs **advisory** — each naming
  the draft line and what would fix it. Findings are hypotheses: verify each against the
  repo and the draft before rewriting, then fix the verified contract-blocking ones. ONE
  round only — review → fix → proceed; never a review loop. Carry unresolved advisory
  findings into the draft you confirm with the user. Only then stamp `model:` (next
  section) — the review can change criteria, and the tightness rubric must rate the final
  contract.

  Batch mode: one reviewer covers ALL drafted goals in a single pass — it also catches
  cross-goal overlap and duplicated criteria that per-item drafting can't see — between
  drafting and the approval table.
  ```

- [ ] **Step 2: Wire the flow.**
  - "Brief first, then artifact": "After the brief, recon, and any approval required for
    file writes" → "After the brief, recon, the contract review (queue destination), and
    any approval required for file writes".
  - Queue-rules bullet: "Confirm the draft (title + acceptance criteria) with the user
    before writing; batch mode uses its approval table instead." → append "Queued drafts
    are confirmed after their contract review (see Contract review)."
  - "Implementer model — decide it last": "Stamp it LAST, after the acceptance criteria
    are final" → "Stamp it LAST, after the acceptance criteria are final (for queued
    goals: after the contract review)".

- [ ] **Step 3: Batch mode.** Renumber the 5-step list to include a new step 4 —
  "**Contract review**: one fresh read-only reviewer red-teams all drafts in a single pass
  (see Contract review above); verify and fix contract-blocking findings." — old steps 4–5
  become 5–6. In the workflow-sizing paragraph, extend `pipeline(items, locate, draft)`
  with "…then ONE contract-review agent over all drafts (a genuine barrier — it needs
  every draft) before the approval table".

- [ ] **Step 4: Self-read the diff** for contradictions with the recon section's model
  rules and the 4,000-char/`acceptance:` headless rules. Expected: none.

### Task 3: Dry-run verification (the test suite for prose skills)

**Files:** none modified (fix-ups loop back into Tasks 1–2 files).

- [ ] **Step 1: Dispatch dry-run.** Spawn a Sonnet read-only subagent (CLAUDE.md routing:
  research → Sonnet) given ONLY `skills/dispatch/SKILL.md`, asking it to answer with
  section citations:
  1. Multi-file diff, clean `Fresh-check:` block present — what review runs before the
     gate commands, on which agent/model? (Expected: ONE fresh adversarial reviewer,
     general-purpose, session model; block = corroborating evidence.)
  2. Report claims `Fresh-check: not required` but the diff touches 4 files — what
     happens? (Expected: full 2–3-lens panel.)
  3. Genuine one-file mechanical edit — reviewer? (Expected: skipped.)
  4. Reviewer returns a Critical finding — path? (Expected: verify → FAIL_FIXABLE repair →
     re-gate incl. focused re-check.)
- [ ] **Step 2: define-goal dry-run.** Same shape:
  1. Queued bug goal drafted — what happens before `model:` stamping and user
     confirmation? (Expected: contract review, red-team brief, one round.)
  2. Run-now destination — contract review? (Expected: skipped, with the evaluator-parity
     reason.)
  3. Batch mode, 7 items, workflow available — where does contract review sit?
     (Expected: one reviewer over all drafts, barrier before the approval table.)
- [ ] **Step 3: Fix every flagged ambiguity** in the SKILL.md texts; re-run only the
  failed scenario. Expected: all answers match with correct citations.

### Task 4: Docs sync — CLAUDE.md, README, site

**Files:**
- Modify: `CLAUDE.md` (dispatch + define-goal bullets; v4.1.x invariants gate sentence)
- Modify: `README.md` (badge → 5.1.0; intro para ~line 24; skills table rows for
  define-goal/dispatch; dispatch "Per goal" step 3; define-goal section; "The local gate"
  section)
- Modify: `public/index.html` (`<title>` + `.ver-pill` → v5.1.0; pipeline step 01/03/04
  cards; define-goal + dispatch skill cards)

**Interfaces:**
- Consumes: the terms **independent review** (dispatch) and **contract review**
  (define-goal) exactly as named in Tasks 1–2.

- [ ] **Step 1: CLAUDE.md.** dispatch bullet: replace the "review-evidence check (…)"
  clause with "an independent review (for non-trivial work the orchestrator ALWAYS spawns
  one fresh read-only adversarial reviewer over the diff — the implementer's `Fresh-check:`
  verdicts are corroborating evidence, never the verdict; a missing block escalates to the
  2–3-lens panel; verified findings feed the repair path, v5.1.0)". define-goal bullet:
  add "Every queued goal gets an adversarial contract review — one fresh read-only
  subagent red-teams the drafted contract (gameability, command reality, type shape, gate
  fit, termination) before the model stamp and user confirmation (v5.1.0)." Invariants
  bullet: "the LOCAL gate over the `gate_base..HEAD` diff — `pg_validate.py` plus the
  repo's `config.verify` commands" → "— an independent second-view review plus
  `pg_validate.py` plus the repo's `config.verify` commands".
- [ ] **Step 2: README.** Badge `version-5.1.0`; intro sentence gains "the orchestrator
  independently reviews the diff (a fresh adversarial second view) and runs a local
  build + test gate"; dispatch table row "review-evidence-verified local gate" →
  "independent-review-backed local gate"; define-goal row → "a measurable, red-teamed goal
  contract"; "Per goal" step 3 and "The local gate" section each gain one sentence naming
  the always-on independent reviewer; define-goal section gains one sentence on the
  contract review.
- [ ] **Step 3: Site.** Title/ver-pill v5.1.0. Step 01 card: "grounded by recon" →
  "grounded by recon, red-teamed before it queues". Step 03 card: "…backed by TDD and
  fresh review checks the gate verifies were actually run." → "…backed by TDD and fresh
  review — then the orchestrator re-reviews the diff with its own independent reviewer."
  Step 04 card: "after a local build+test gate passes" → "after an independent review and
  a local build+test gate pass". define-goal card: append "Red-teams every queued contract
  before it lands." dispatch card: "passes TDD-backed local checks" → "passes an
  independent second-view review plus the local build+test gate".

### Task 5: Release — bump, changelog, validate, ship

**Files:**
- Modify: `.claude-plugin/plugin.json` (version 5.1.0; description's dispatch/define-goal
  clauses updated to name the second-view review)
- Modify: `CHANGELOG.md` (new 5.1.0 block above 5.0.2, same format incl. commit link
  convention used by existing entries)
- Memory: update `~/.claude/projects/-root-flywheel/memory/flywheel-v4-followups.md`

- [ ] **Step 1: Bump `plugin.json`** to `"version": "5.1.0"`; in `description`, extend
  the dispatch clause to "…local build+test gate behind an independent second-view
  review…" and the define-goal clause to "…measurable, red-teamed goal contracts…".
- [ ] **Step 2: CHANGELOG 5.1.0 block** — headline "maker–checker: an independent
  second-view review at the dispatch gate + an adversarial contract review in
  define-goal"; body: the two mechanics, the run-now/queue evaluator-parity rationale,
  the Factory-comparison origin with the adopted/rejected summary, pointer to this plan
  doc. Match the existing entries' commit-link convention exactly.
- [ ] **Step 3: Validate** — run the `plugin-dev:plugin-validator` agent (manifest
  changed). Expected: no errors.
- [ ] **Step 4: Commit + push** — one commit:
  `feat(dispatch,define-goal): independent gate review + contract red-team (v5.1.0)`
  including plan doc, skills, docs, manifest, changelog, README, site.
- [ ] **Step 5: Tag + release** — `git tag -a v5.1.0 <sha>`, `git push --tags`,
  `gh release create v5.1.0 --title "v5.1.0 — maker–checker validation" --notes-file
  <changelog section> --verify-tag --latest`.
- [ ] **Step 6: Deploy site** — `wrangler deploy` from repo root (CLOUDFLARE_API_TOKEN).
- [ ] **Step 7: Memory** — one line in `flywheel-v4-followups.md`: maker–checker shipped
  v5.1.0.
