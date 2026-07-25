---
id: 002-answerable-needs-you
title: Every human decision names the exact command that resolves it
created: 2026-07-25
type: feature
skills: []
model: heavy
size: M
touches: ["skills/dispatch/SKILL.md", "skills/define-goal/SKILL.md", "CLAUDE.md", "AGENTS.md", "README.md", "public/index.html"]
acceptance: ["python3 -m pytest -q"]
---

## Outcome (plain language)

Today the factory tells you a goal is blocked and why, but never what to do about it:
`needs-you: 004 — contract defect: criterion 3 ambiguous`. The escalation ladder's last rung
is always "ask the human", and the human is whoever needed the factory. After this goal every
needs-you item names the exact command that resolves it, and `define-goal --amend <id>` walks
a blocked goal's defect with plain-language options and a recommendation, repairs the
contract, and puts the goal back in the queue.

## Context / why

Design brief: `docs/goals/briefs/2026-07-25-close-the-gap.md` (piece B).

Located by recon:

- Dispatch emits needs-you items from ~19 distinct prose sites (`skills/dispatch/SKILL.md:68,
  152, 159, 165, 198, 248, 273, 341, 370-374, 409, 427-428, 442, 619, 625, 638, 650,
  666-667, 735`). Each spells out its own phrasing; there is no shared format block. That
  duplication is why a suffix cannot be added uniformly today.
- The report line is `skills/dispatch/SKILL.md:672`; the rules for what needs-you contains
  are at `:696-703`.
- Block reasons dispatch writes, by flavor: `contract defect: <criterion> ambiguous`
  (`:202-203, 619`), `contract defect: <criterion> unreachable` (`:198, 625`),
  `contract defect: <the verified finding>` (`:370-371`), `contract defect: <reason>`
  (`:650`), `no runnable local gate: <evidence>` (`:372-374, 428`),
  `repeated transient death` (`:205, 227`), the implementer's ask verbatim (`:638`), and
  free-form gate/no-progress reasons (`:152-153`).
- **No attendedness detection exists anywhere in the repo.** `--unlimited` is *labeled* the
  attended mode (`:75`) but that is a user-chosen flag, not a probe. `claude -p` /
  `droid exec` appear only as crontab-grep strings in `doctor_checks.py:247`. Dispatch has
  **zero** AskUserQuestion calls; only ideate and define-goal use it
  (`ideate/SKILL.md:66`, `define-goal/SKILL.md:46,186,310,652`). This mechanism is new.
- Queue verbs: dispatch owns the closed set `claim|complete|block|archive`
  (`skills/dispatch/SKILL.md:180`); define-goal already owns verbs outside it —
  `chore(goals): reserve <id>` and `chore(goals): add <id>`
  (`skills/define-goal/SKILL.md:343-350`) — so a define-goal-owned `amend` verb has direct
  precedent.
- Blocked entries carry `status` + free-form `reason`; `goals_status.py:211` surfaces
  `reason` only while `status == "blocked"`, so a stale reason left behind after a requeue is
  invisible but still present in the index.
- define-goal's frontmatter `argument-hint` is free text (`:4`); dispatch is the only
  flag-taking skill and its Invocation table + argument rules (`:34-44`) are the template.
- Implementer report path is `~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md`,
  `<SLUG>` = the repo dir name (`skills/dispatch/SKILL.md:421, 559, 714`). The implementer
  **overwrites any prior attempt's file** (`:559`), so it may not correspond to the block
  that produced the current `reason`.
- `test_docs_model_policy.py::test_active_docs_use_tier_vocabulary` requires every line in
  the 9 active docs naming a legacy model to also name its tier (or say alias/maps). New
  prose in those docs must keep the tier vocabulary.

**Invariant conflict this goal must resolve.** `CLAUDE.md:257` and `AGENTS.md:57` both state
"Goal files are immutable contracts", while dispatch routes contract defects to "a needs-you
contract amendment (the human re-specifies via define-goal)" in eight places. Owner decision
(2026-07-25): amend **in place**, and narrow the invariant text to what it actually protects —
a goal file is immutable to implementers and immutable while claimable; only
`define-goal --amend`, only on a `blocked` goal, may edit one.

**Interfaces this goal produces** (consumed by 003-surface-subjective-criteria):

- A single canonical needs-you format section in `skills/dispatch/SKILL.md` defining the line
  shape `<id or item> — <reason> → <what to run>`.
- A table in that section with the explicit columns `class | trigger | what to run`. The
  column set deliberately admits NON-blocking classes: goal 003 adds a PASS-time
  informational class whose trigger is a successful gate and whose "what to run" is
  per-criterion prose rather than a fixed command. 003 adds one row to this table and must
  not invent a second format.

**Queue ordering this goal requires.** Goal `003-surface-subjective-criteria` consumes the
format section above and MUST carry `depends_on: [002-answerable-needs-you]` in its
`index.yaml` entry — without it dispatch's ready rule (`skills/dispatch/SKILL.md:437`) makes
003 claimable before this section exists, and its implementer (who sees only its own goal
file) would invent a second format.

## Acceptance criteria

- [ ] `skills/dispatch/SKILL.md` gains ONE canonical needs-you format section defining the
  line shape `<id or item> — <reason> → <command>` plus a blocker-class → resolving-command
  table covering at minimum: the four `contract defect: …` flavors →
  `/define-goal --amend <id>`; `no runnable local gate: …` → `/factory-doctor`; environment
  brake → `/factory-doctor`; `repeated transient death` → `/dispatch <id>`; budget exhausted
  → the config edit; `base:` mismatch → the branch-switch command; multiple `in_progress` →
  the manual-review pointer; CI failure → the `gh run` command.
- [ ] The individual needs-you emission sites reference that section by class rather than
  restating the format, proven by a countable check: after the change the literal line-shape
  string `<id or item> — <reason> → <what to run>` occurs EXACTLY ONCE in
  `skills/dispatch/SKILL.md` (command:
  `grep -c '<id or item> — <reason> → <what to run>' skills/dispatch/SKILL.md` prints `1`),
  and each of these sites names its class: `:68` environment brake, `:159` conflict, `:165`
  budget, `:198`/`:625` unreachable, `:248` CI, `:273` environment failure, `:341`/`:370`
  FAIL_CONTRACT, `:372` INCONCLUSIVE, `:409` multiple in_progress, `:442` base mismatch,
  `:619` ambiguous, `:638` NEEDS_CONTEXT, `:650` ladder rung 3, `:666` unmet deps, `:735`
  lesson-encoding. Line numbers are pre-change anchors — match the site by its text, not the
  number.
- [ ] `skills/dispatch/SKILL.md` states an attended-only interactive-question rule with ALL
  of these conditions required together: the user invoked `/dispatch` conversationally in
  this session, AND no batch flag (`--count`/`--unlimited`) is active, AND the run is not
  `/loop`, `claude -p`, or `droid exec`. It states explicitly that when any condition is
  unknown or unverifiable the orchestrator does NOT ask, and that a batch run never asks.
  Limits stated: one round, at most 2 questions, options with a recommended default.
- [ ] `skills/define-goal/SKILL.md` gains an `--amend <id>` mode with an Invocation section
  modeled on dispatch's (`:34-44`), and its `argument-hint` and `description` are updated so
  the mode is discoverable and routable.
- [ ] The `--amend` mode specifies, in order: refuses any goal whose index status is not
  `blocked` (reporting the actual status); reads the goal file, the index `reason`, and the
  implementer report at `~/.local/state/pg-dispatch/<SLUG>/reports/<id>-report.md` when it
  exists, treating a missing or stale report as non-fatal; runs ONE question round in plain
  language with options and a recommended default; rewrites ONLY the criteria the reason
  identifies as defective; re-runs the contract red-team on the amended draft; and requeues.
- [ ] The requeue step specifies flipping `status` back to `not_started` AND clearing the
  stale `reason` field, committed as `chore(goals): amend <id>` — one entry, its own commit,
  matching the claim protocol convention.
- [ ] The amended goal file records a one-line amendment note in its Context section stating
  the defect and the resolved reading, so the next implementer cannot re-open the same fork.
- [ ] The "immutable contracts" invariant is narrowed at ALL FOUR sites where it appears —
  `CLAUDE.md:257`, `AGENTS.md:57`, `README.md:309`, `public/index.html:417` — to read that
  goal files are immutable to implementers and while claimable, with `define-goal --amend` on
  a `blocked` goal named as the sole exception. Proven by:
  `grep -rn 'immutable contracts' README.md public/index.html CLAUDE.md AGENTS.md` — every hit
  carries the exception, and the count is unchanged (4).
- [ ] `README.md` and `public/index.html` describe the `--amend` mode (per CLAUDE.md's
  docs-move-with-the-skills rule).
- [ ] A subagent dry-run is run on the attended-question rule with a RED baseline: the same
  scenario against `git show HEAD:skills/dispatch/SKILL.md` must be shown to decide it
  differently or leave it undecided. Both transcripts are quoted in the report.
- [ ] `python3 -m pytest -q` (full suite) passes.

## Constraints (hard rules)

From CLAUDE.md, verbatim:

- **Skills-first (formerly skills-only).** Don't add MCP servers, commands, agents, or hooks
  here without an explicit ask.
- **Portability.** Skills must not contain user-specific absolute paths (`/Users/...`) for
  either harness.
- **Docs move with the skills.** Changing what a skill does, how it's invoked, plugin
  boundaries, install, or the queue/config model means updating `README.md` AND
  `public/index.html` in the SAME change.
- **Skill edits are tested.** New or changed skill mechanics get a subagent dry-run before
  shipping; for compliance-critical rules, add a RED baseline.
- **Push every time — on every completion, the FULL tree.**
- Never push protected branches.

Plus:

- Status still lives ONLY in `index.yaml` — the amend mode never writes status into goal
  frontmatter.
- `--amend` never touches a goal that is not `blocked`, and never edits `docs/goals/` for a
  goal another session has claimed.
- Dispatch must remain safe to run unattended: no unconditional interactive call may be
  added to any dispatch path.
- Keep the tier vocabulary in any new prose: the docs model-policy test requires every line
  naming a legacy model in an active doc to also name its tier or say alias/maps.

## Out of scope

- Any runtime/programmatic attendedness probe (TTY checks, env sniffing) — the rule is
  stated in the skill and evaluated by the orchestrator from evidence it already has.
- Superseding goal files (new `-v2` files, a `superseded` status) — rejected in favor of
  in-place amend plus git history.
- Changing how blocked goals are chosen or ordered by dispatch.
- Auto-amending: `--amend` is always human-invoked and always asks before rewriting.
- Version bump, `CHANGELOG.md` entry, git tag, and GitHub release. Goals 001-003 ship as ONE
  release performed by the repo owner after all three complete. Do NOT edit
  `.claude-plugin/plugin.json`, `CHANGELOG.md`, the site `.ver-pill`, or the README version
  badge.

## If blocked

Stop and report attempted paths, evidence, the blocker, and what would unlock you.
If the same acceptance command fails the same way twice in a row, or after ~3 honest
attempts a criterion can be neither satisfied nor shown measurable, declare
GOAL_UNREACHABLE with evidence and stop — never retry the identical failing approach.

## Goal contract

/goal Make every needs-you item name the command that resolves it, and add
`define-goal --amend <id>`, per the Acceptance criteria of
docs/goals/002-answerable-needs-you.md. In `skills/dispatch/SKILL.md`: add ONE canonical
needs-you format section (`<id or item> — <reason> → <command>`) plus a blocker-class →
command table, have the ~19 emission sites reference it by class instead of restating the
format, and add an attended-only question rule requiring conversational invocation AND no
batch flag AND not `/loop`/`claude -p`/`droid exec`, defaulting to NOT asking when unknown.
In `skills/define-goal/SKILL.md`: add an `--amend <id>` Invocation section that refuses
non-blocked goals, reads the goal file + index reason + implementer report, runs one
plain-language option round, rewrites only the defective criteria, re-runs the contract
red-team, records a one-line amendment note in Context, and requeues via
`chore(goals): amend <id>` flipping status to not_started and clearing reason. Narrow the
"immutable contracts" invariant at all four sites (CLAUDE.md, AGENTS.md, README.md,
public/index.html) to name this exception, and describe --amend in README.md and
public/index.html. The canonical line-shape string must occur exactly once in
skills/dispatch/SKILL.md. Run a subagent dry-run of the attended rule WITH a RED
baseline against `git show HEAD:skills/dispatch/SKILL.md`, quoting both transcripts. Done
when `python3 -m pytest -q` passes and the dry-run + RED baseline are shown. Before stopping
on success, re-print the final acceptance-command outputs. Stop when every criterion
verifiably passes, or when blocked or a criterion proves unreachable (follow "If blocked").
Stop after 25 turns.
