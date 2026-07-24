# flywheel

## Project Overview

Skills-first Claude Code marketplace from Pragmatic Growth.
The repo now publishes four plugins from one `pragmatic-growth` marketplace:
`flywheel` v6.1.0, `html-artifacts` v1.0.1, `autoresearch` v1.1.0, and
`human-writing` v1.0.1. No MCP
servers, no commands, no hooks, no build step. ONE scoped exception to the
skills-only rule, as of v5.4.0: THREE plugin agent definitions
(root `agents/` — the factory's read-only review roles `gate-reviewer`,
`fresh-check`, `contract-red-team`; added by owner-delegated decision
2026-07-16 after transcript forensics on real dispatch runs showed
hand-composed review briefs drifting across fires. Each carries the role
brief + output contract as its system prompt and a tool allowlist with no
Edit/Write/Agent, pins no `model:`, and has a deliberately narrow
description so Claude never auto-delegates to it outside flywheel skills;
the skills always keep a `general-purpose`-with-inline-brief fallback, and
the built-in Explore type is banned for review roles).
`flywheel` has six skills under root
`skills/` (three ship deterministic Python helpers in `scripts/`), forming a
plain-language → autonomous-execution pipeline around a file-based goal queue
(`docs/goals/` in target repos): `/ideate → /define-goal → /dispatch →
/goals-status`, with `loop-architect` and `factory-doctor` as the rails. `html-artifacts` lives under
`plugins/html-artifacts/` as a separate plugin for rich
plans/reports/diagrams/editors. `autoresearch` lives under
`plugins/autoresearch/` as a separate plugin for an autonomous try/measure/keep/
revert optimization loop (ships one Python helper). `human-writing` lives under
`plugins/human-writing/` as a separate single-skill plugin for AI-writing
cleanup (pure guidance, no scripts).

- **ideate** (v6.1.0, adapted from superpowers' brainstorming after the
  2026-07-24 full-plugin deep-read) — the pipeline's front door: explores a
  fuzzy idea into a user-approved design through open dialogue. Context
  orientation first (1–2 read-only subagents max; on `sonnet` as of v6.2.0 —
  gather work, same routing as define-goal recon), split-first
  scope check (decomposition before detail questions — pieces map 1:1 onto
  goals + `depends_on`), option-based question rounds with NO round cap (the
  attended stage; define-goal keeps its two-round cap), 2–3 approaches with a
  recommendation, design presented in sections scaled to complexity, inline
  self-review (placeholders, contradictions, two-readable requirements).
  HARD GATE: its only terminal states are invoking define-goal with the
  approved design or the user parking the idea — it never writes goal files,
  index entries, or code. Multi-goal chains get ONE design brief at
  `docs/goals/briefs/YYYY-MM-DD-<topic>.md` (the one sanctioned planning
  artifact beyond goal files; never carries acceptance criteria or status),
  linked from each chain goal's Context; single-goal outcomes stay fileless.
  Already-shaped wants skip it entirely.
- **define-goal** — plain-language wants → measurable goal contracts.
  Two destinations: a copy-pasteable `/goal` line to run now, or a queued
  goal file (`docs/goals/NNN-slug.md` + `index.yaml` entry). Includes
  repo grounding (CLAUDE.md rules copied verbatim, real
  verification commands) and a batch mode for documents of items.
  Stamps each queued goal's frontmatter `model:` (inherit|opus|sonnet|haiku)
  LAST, after the acceptance criteria are final, from a contract-tightness
  rubric (v4.15.0; rebalanced v6.2.0, owner decision 2026-07-24): the goal
  `type:` picks the lane and wins ties — opus is the DEFAULT for every
  feature/bug goal (tightness is never a downgrade reason; an explicit user
  ask for cheap execution is the only route down), sonnet is rote
  chore-shaped work only (lint/doc/config sweeps, ports with an exact
  source of truth); unsure → the stronger. Every queued goal gets an adversarial contract review first
  (v5.1.0): one fresh read-only subagent red-teams the drafted contract —
  gameability, command reality, type shape, gate fit, termination — one
  round, before the model stamp and the user confirmation (run-now `/goal`
  lines skip it; the `/goal` evaluator is their second view). As of v5.4.0
  that reviewer spawns as the plugin agent `flywheel:contract-red-team`
  when available (`general-purpose` + inline rubric fallback). v5.5.0 (from
  the superpowers eval-evidence deep-read): dependent goals in a `depends_on`
  chain carry an Interfaces note in Context (exact names the dependency
  produces — the implementer sees only its own goal file; red-team checks it,
  advisory), the model rubric adds turn-count-beats-token-price to the haiku
  caution, and ambiguity is named a contract defect in its own right
  (dispatch implementers STOP `CONTRACT_AMBIGUOUS` on a two-readable
  criterion instead of guessing). v5.5.1: the question round is split-first
  (split question before detail questions), option-based with a recommended
  default, and adaptively two-round — ONE extra targeted round (1–2
  questions) when a round-1 answer or review finding opens a genuine fork,
  two rounds total the hard cap
  (progressive one-at-a-time dialogue deliberately NOT adopted). Produces goals
  only, never implements. Originally adapted from
  OpenAI's curated `define-goal` skill (its `create_goal`/`get_goal`
  tools don't exist here; `/goal` is user-run, transcript-
  evaluated, 4,000-char condition cap). The `/goal` facts were verified
  against the shipped CLI internals (v5.3.0): the evaluator reads a
  recency-truncated transcript (→ contracts re-print final acceptance outputs
  in the closing turn; long runs announce "turn N of cap M"), its `impossible`
  verdict honors GOAL_UNREACHABLE only with evidence attached, it defers while
  background work runs, and it fails open on its own errors (never the only
  unattended rail). The UI scripted-check rule also generalizes to other
  drivable surfaces (CLI/API → drive-the-real-surface criterion). v6.1.0: the
  red-team rubric adds a no-placeholders check ("TBD" / "appropriate error
  handling" / command-less criteria are vague-by-construction →
  contract-blocking); fuzzy still-being-explored wants route to ideate first
  (already-shaped wants never bounce; ideate unavailable → design
  conversation inline, the two-round cap governs only the contract
  interview), and an ideate handoff is treated as the brief — question rounds
  cover only remaining gaps, recon narrows to verify-and-complete, chain
  goals link the design brief from Context.
- **dispatch** — factory orchestrator for the docs/goals queue: works ONE
  ready goal per run on the branch that's currently checked out — no PRs, no
  worktrees, no `goal/<id>` branches, no parallel implementation. Per goal it
  records the pre-claim clean
  HEAD as `anchor`, commits the claim, records the post-claim HEAD as
  `gate_base`, spawns ONE foreground implementer that commits its work
  directly on the branch — on the goal's resolved implementer model
  (goal frontmatter `model:` > `config.model` > inherit, v4.15.0; the
  orchestrator and recon/review agents always stay on the session
  model) — using a lightweight subagent-driven quality loop
  (plan/checklist, TDD, fresh verifier/reviewer subagent for non-trivial work;
  v5.4.0: the fresh-check panel spawns FOREGROUND as `flywheel:fresh-check`
  lenses — never background-then-poll, never Explore — after real runs showed
  sleep-loop waits discarding completed lens verdicts),
  then runs the LOCAL gate authoritatively: an independent review (v5.1.0 —
  for any non-trivial diff the orchestrator ALWAYS spawns one fresh read-only
  adversarial reviewer — v5.4.0: `flywheel:gate-reviewer` when available,
  `general-purpose` + inline brief fallback — over `gate_base..HEAD` + the goal file; the
  implementer's `Fresh-check:` lens verdicts are corroborating evidence,
  never the verdict; a missing block or a not-required claim the diff belies
  escalates to the full 2–3-lens panel; verified Critical/Important findings
  feed the repair path; v5.3.0 calibrates the reviewer — surface half-believed
  findings marked uncertain rather than silently dropping them, Critical
  findings quote the triggering line, pre-existing baseline failures and
  exempted test paths are named non-findings — and the implementer's verify
  step adds one off-happy-path probe at any drivable surface; v5.5.0 tightens
  gate economics + honesty from the superpowers eval-evidence deep-read:
  reviewers are diff-scoped — read the diff once, step outside only for a
  NAMED concrete risk, one focused check per named risk, else it's an
  uncertain finding, never a repo sweep — with two anti-laundering rules (a
  stated rationale never downgrades severity; a contract-mandated defect is
  still a finding → FAIL_CONTRACT, never the repair path); the implementer
  writes full evidence to `~/.local/state/pg-dispatch/<SLUG>/reports/
  <id>-report.md` and returns a ≤15-line `STATUS:` report (DONE |
  DONE_WITH_CONCERNS | BLOCKED | GOAL_UNREACHABLE | CONTRACT_AMBIGUOUS) so
  orchestrator context stays lean; an early `CONTRACT_AMBIGUOUS` stop routes
  two-readable criteria to a needs-you contract amendment before work is
  burned; repair is omnibus (one agent, complete findings list) and the
  focused re-check adds a collateral scan of the repair diff), then the
  deterministic `pg_validate.py`
  over the `gate_base..HEAD` diff plus the repo's `config.verify` build+test
  commands. PASS → squash the goal's commits to one `feat(goal NNN)` commit
  and mark it `completed`; FAIL → `git reset --hard gate_base` and mark it
  `blocked` (with reason). CI, if the repo has it, is a NON-BLOCKING post-push
  observation surfaced under needs-you — never a merge gate. Built to repeat as
  `/loop 15m /dispatch`; each fire handles at most one new goal and is idempotent. Each fire emits one report
  line leading with progress — `<done>/<total> done` plus a 20-cell fill
  bar, then labeled `ready`/`blocked` counts that sum to `total`
  (lead with done, never `ready/total`, which reads as "nothing done");
  `needs-you` holds human-blocked goals plus any non-blocking CI failures.
  Each fire APPENDS a heartbeat line (`~/.local/state/pg-dispatch/<SLUG>/heartbeat`,
  newest ~50 kept); the cross-fire brake counts heartbeat lines after a stale
  claim's date (≥3 fires with zero work commits → `blocked: repeated transient
  death`) instead of wall-clock age, so an account usage-limit pause (no fires
  → no lines) resumes a claim rather than mislabeling it dead. v6.1.0
  (superpowers full-plugin deep-read): invocation grammar —
  `/dispatch` works the next ready goal (unchanged default); `/dispatch <id>`
  formalizes solo mode with claim guards (completed/in_progress reported,
  unmet deps → needs-you, id beats a batch flag); `--count N` /
  `--unlimited` run an in-session sequential batch of the same settled
  per-goal cycles (Phase 0/1 once; per-goal report line + heartbeat, each
  cycle = one fire; a blocked goal doesn't stop a batch; the budget ALWAYS
  outranks flags — effective cap = min(flag, budget); an environment brake
  stops the batch on two consecutive infrastructure-shaped failures, skipping
  the second futile repair spawn; `--unlimited` is the attended drain —
  unattended stays `/loop` + external scheduling). The implementer status
  contract adds NEEDS_CONTEXT, and a BLOCKED escalation ladder runs before
  any goal blocks (each rung once, never a same-model-unchanged respawn:
  answer-context re-spawn → one stronger-model re-spawn for
  capability-shaped blockers on sonnet/haiku-stamped goals → too-large /
  wrong-contract → contract-defect route → else block; ladder re-spawns
  continue from the current branch state). The repair brief gains
  receiving-review discipline: verify-then-fix, rebut-with-evidence (the
  orchestrator adjudicates — confirmed-false findings drop from the re-check,
  upheld ones return as open failures), covering tests re-run and appended.
- **goals-status** (v5.2.0; simplified in v6.0.0) — read-only view of the
  docs/goals queue. Prints
  every OPEN goal — `in_progress`, `blocked`, `not_started` — with its title and
  a one-line brief (the goal file's `## Outcome (plain language)` paragraph),
  grouped in that order and id-sorted within a group; `completed` goals are
  hidden (only counted, including `archive.yaml`). Blocked goals show their
  index `reason`; a `not_started` goal waiting on an unfinished dependency shows
  what it waits on. ONE view — the `--compact`/`--json` modes and the
  `--self-test` flag were cut in v6.0.0 (zero callers; pytest already runs the
  suite). Ships `scripts/goals_status.py`, PyYAML-only: factory-doctor already
  treats a missing PyYAML and a malformed index as BLOCKERs, so v6.0.0 dropped
  the ~80-line hand-rolled fallback rather than ship a second, weaker YAML
  reader. Failure is split deliberately — an unreadable **index** exits 2 with a
  `/factory-doctor` pointer and prints nothing (a partial queue read is worse
  than none), while one unparseable **goal file** degrades to `(untitled)` and
  never takes the view down. SKILL.md resolves the helper in ONE bash block
  (`$CLAUDE_PLUGIN_ROOT`, else a `find` over `~/.claude/plugins`); the old
  brace-glob chain aborted under zsh with `no matches found`. Strictly
  read-only — never claims, changes, or implements a goal (that's
  `dispatch`) and never writes `index.yaml`.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs;
  names `docs/goals/index.yaml` the canonical factory ledger. Includes
  usage-limit proofing (Step 5): subscription 5-hour/weekly limits kill
  in-session loops with no hook fired, so unattended drains schedule OUTSIDE
  the session (cron/launchd firing fresh `claude -p "/dispatch"`), optionally
  reading the reset clock from statusline
  `rate_limits.*.resets_at` or a `StopFailure` (rate_limit) hook marker.
- **factory-doctor** — one-pass preflight/doctor for a repo + machine:
  checks software, gh auth + scopes, the git working tree, CI, queue
  state, and loop health (stale claims, underspecified goals, and
  `limit-resilience` — WARN when a repo's loop demonstrably fires but has no
  usage-limit rail: no external scheduler, no `StopFailure` hook);
  aggressively auto-fixes everything local (scaffolds the queue,
  strips deprecated v3 config keys — `merge`/`wip`/`execution`/`autonomy` —
  from a stale `index.yaml` so v3-era projects stop silently running dead
  config under the v4 model) and
  reports remote/CI issues with exact fixes. Ships `scripts/doctor_checks.py`
  (read-only probe, `BLOCKER|WARN|FIXED|INFO`, exit 0/1/2). The v4 sequential
  model commits directly on the local branch, so there is no merge allow-rule
  to provision — the gate is local. The probe checks settings in `.claude/`.
Separate marketplace plugins:

- **html-artifacts** — produces self-contained browser artifacts for
  deliverables where markdown is the wrong shape: stakeholder-ready plans,
  specs, PR/code-review writeups, module maps, diagrams, timelines,
  research explainers, status/incident reports, decks, prototypes, and
  one-off editors with export/copy round trips. Single skill with
  `references/` for progressive disclosure under
  `plugins/html-artifacts/skills/html-artifacts/`. No listener, server,
  command, MCP surface, or build step; interactive results export through
  the HTML file's copy/export button.
- **autoresearch** — autonomous optimization loop: given a measurable metric,
  a benchmark command, files-in-scope, constraints, and a termination
  condition, it works an `autoresearch/<goal>-<date>` branch — try one
  hypothesis, run the benchmark, keep the change if the primary metric improves
  and `git`-revert it if not, journaling every run — with MAD-based confidence
  scoring separating real gains from noise. All state lives in files
  (`autoresearch.md`/`.sh`/`.jsonl` in the target repo) so any fresh session
  resumes exactly where the last stopped; on termination it groups kept
  experiments into independently-mergeable branches. Single skill +
  `scripts/autoresearch_helper.py` (stdlib-only JSONL/confidence helper,
  resolved via `$CLAUDE_PLUGIN_ROOT`) under
  `plugins/autoresearch/skills/autoresearch/`. Unattended cadence via `/loop`.
- **human-writing** — edits AI-sounding text into human prose: scans for the tells
  catalogued in Wikipedia's "Signs of AI writing" (inflated significance,
  promotional language, `-ing` filler, em-dash/rule-of-three overuse, AI
  vocabulary, vague attributions, chatbot artifacts), rewrites them, and pushes
  for real voice. Pure writing guidance, one
  `SKILL.md`, no scripts/state/references.
  Single skill under `plugins/human-writing/skills/human-writing/`. Based on
  Wikipedia's guide (WikiProject AI Cleanup, CC BY-SA).

## Queue design invariants (research-backed; one-goal-at-a-time dispatch model, 2026-06-28; batch flags 2026-07-24)

- **One-goal-AT-A-TIME dispatch model** (v4.1.x; restated for v6.1.0's batch
  flags — the invariant was never "one per run"): dispatch works ready goals
  strictly sequentially,
  committing work DIRECTLY on the branch that's checked out — no PRs, no
  worktrees, no `goal/<id>` branches, no parallel implementation. A flagless
  run works one goal; `--count N` / `--unlimited` extend the run to a
  sequential batch of the same fully-settled cycles (each goal claims → gates
  → settles before the next claim; budget outranks flags). Each
  goal is bracketed by two anchors: `anchor` (the pre-claim clean HEAD) and
  `gate_base` (HEAD right after the claim commit). The implementer commits on
  the branch; then the orchestrator runs the LOCAL gate over the
  `gate_base..HEAD` diff — an independent second-view review (one fresh
  read-only adversarial reviewer for any non-trivial diff, v5.1.0) plus
  `pg_validate.py` plus the repo's `config.verify`
  commands — and that local gate is the ONLY merge gate. PASS → squash the
  goal's commits into one `feat(goal NNN)` commit + `completed`; FAIL →
  `git reset --hard gate_base` + `blocked`. CI, where the repo has it, is a
  NON-BLOCKING post-push observation surfaced under needs-you, never a gate.
  `/loop /dispatch` advances the queue by repeating the same one-goal cycle
  across fires; a batch flag repeats it within one run.
- Status lives ONLY in `index.yaml`, never in goal-file frontmatter —
  dual-write drifts. Goal files are immutable contracts.
- Statuses: `not_started | in_progress | completed | blocked` — blocked
  (with reason) is required to avoid re-dispatch livelock. `completed`
  only when the gate has PASSED and the goal's commit is on the branch.
- `index.yaml` `config:` block: `base` (the branch goals are worked on;
  per-goal `base:` override allowed), `model` (inherit|opus|sonnet|haiku —
  the repo-wide DEFAULT for code agents dispatch spawns; each goal's
  frontmatter `model:` — stamped by define-goal from its contract-tightness
  rubric (opus default for features/bugs since v6.2.0) — overrides it per
  goal, and the orchestrator and review agents
  always stay on the session model; the depth-vs-limit trade), repo-wide
  `skills`, `verify` (the ordered local
  build+test commands the gate runs after each implementer), and `budget`
  (optional; `max_goals_per_session` + optional `max_iterations` — a simple
  cap on cumulative spend across repeated dispatch fires; absent = no loop cap).
  Defaults: repo default branch, inherit, no extra skills,
  repo-detected verify commands, no budget.
- Goal frontmatter `type: bug|feature|chore` shapes the contract: bugs
  always lead with a failing-test-reproduces-root-cause criterion (all
  recon hypotheses recorded); features must fill Out of scope; chores
  prove "no behavior change" (suite green before and after) plus one
  mechanical check.
- Claim protocol is LOCAL: every status write is flip ONE entry → commit
  (`chore(goals): claim|complete|block|archive <id>`). One entry per commit,
  status-only-in-index; no push, no push-arbitration — the single session
  owns the branch. NNN minting is local too (a collision renumbers the NEW
  goal only; never renumber existing goals).
- Skills mandates come in three layers: method skills (writing-plans,
  TDD, verification-before-completion, and a lightweight subagent-driven
  verifier/reviewer loop for non-trivial work) hardcoded in dispatch's brief;
  repo skills in `config.skills`; goal-specific skills in goal
  frontmatter `skills:` (populated by define-goal from actually
  available skills).
- Recon (define-goal) runs BY DEFAULT before any goal touching an existing
  system: investigate-first via parallel read-only subagents is not
  optional — "the description sounds clear" is the failure mode it replaces;
  skip only for genuinely greenfield or one-liner wants. Reaches the system
  wherever it lives (local checkout, separate repo, a host you connect to, a
  service/DB), told to each subagent, never hardcoded. Recon search subagents
  run on `sonnet` (v6.2.0, owner routing decision 2026-07-24 — gather is
  strong-tool-use work; the prior always-inherit rule guarded against
  shallow recon, and that guard now lives in the gather/judge split instead).
  Use the `general-purpose` type with `model: sonnet`, strictly read-only,
  and never the built-in Explore type (its model cannot be pinned). The
  synthesis/judgment agent — and the contract writing itself — ALWAYS stays
  on the current session model; a per-run explicit user ask is the only
  override for the gather model. `config.model`
  governs only code-writing agents, never recon. (Recon stays plain parallel
  subagents, NOT a Workflow: 2–4 agents is below the workflow scale threshold
  and a workflow can be disabled on a user's machine — define-goal batch mode
  is the only place that conditionally uses Workflow.)
- Workflow tool only where the docs' thresholds say it wins: define-goal
  batch mode at ~5+ items (drafts in script variables, approval table
  gates file writes). Dispatch implementers may use workflow mode only
  for bounded read-only fan-out or review inside a single goal; they are NEVER
  workflows for parallel code-writing or cross-run state. The branch commits +
  the two-anchor rollback are the recovery path. The tool needs CLI ≥2.1.154 and
  can be disabled, so skills never assume it.

History note: this repo was previously `mcp-do`, a stdio MCP server
wrapping external coding CLIs (removed in v1.0.0 at ac2bd7c). The
**wish** skill (wants → GitHub issues) was retired in v2.0.0 on
2026-06-12 — the docs/goals file queue replaced GitHub issues as the
work queue (issue bodies cap at 65,536 chars; labels needed per-repo
bootstrap). The v3.x model — one isolated `goal/<id>` worktree PR per
goal, parallel `wip` implementers, an optional herdr spawn substrate,
and `merge: auto` integration gated by a deterministic + optional-LLM
validator before a `pg_safe_merge` wrapper — was replaced in v4.0.0
(2026-06-27) by the sequential, local-gated, direct-to-branch model
above. Two real autonomous `/loop /dispatch` runs motivated the change:
on a website repo and on a tax-filing app, the per-goal PR/CI/worktree
churn produced pile-ups of unmergeable PRs and orchestrator livelock —
the loop burned tokens shepherding PRs that never merged. The v4 model
deletes that machinery (worktrees, PRs, the merge wrapper, herdr, the
multi-stage merge gate) in favor of working the branch in place behind
a local gate. The **telegram-message** skill (v4.11.0 → v4.14.0) — a bot
DMing the owner on errors/limits/waiting/completion — was sunset in v6.0.0
on 2026-07-17 along with `hooks/hooks.json`, the repo's only hook bundle,
and dispatch's `active` fire marker (written every fire; the notifier was
its only reader — the heartbeat, which factory-doctor and the cross-fire
brake actually use, is a separate file and stays). Git history has every
prior model if ever needed.

## Structure

```
.claude-plugin/plugin.json        # root flywheel plugin manifest
.claude-plugin/marketplace.json   # marketplace — name: pragmatic-growth, lists flywheel + html-artifacts + autoresearch + human-writing
agents/<name>.md                  # three flywheel plugin agents — read-only factory review roles: gate-reviewer, fresh-check, contract-red-team (v5.4.0)
skills/<name>/SKILL.md            # six flywheel skills (ideate, define-goal, dispatch, goals-status, loop-architect, factory-doctor)
plugins/html-artifacts/.claude-plugin/plugin.json
plugins/html-artifacts/skills/html-artifacts/SKILL.md
plugins/html-artifacts/skills/html-artifacts/references/ # HTML artifact recipes and foundation rules
plugins/autoresearch/.claude-plugin/plugin.json
plugins/autoresearch/skills/autoresearch/SKILL.md
plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py # stdlib JSONL/MAD-confidence helper
plugins/human-writing/.claude-plugin/plugin.json
plugins/human-writing/skills/human-writing/SKILL.md # AI-writing cleanup (no scripts)
skills/<name>/scripts/*.py        # dispatch/pg_validate.py (local gate), factory-doctor/doctor_checks.py, goals-status/goals_status.py (read-only queue view)
CHANGELOG.md                      # canonical, git-tracked version history (site carries no on-page changelog)
public/index.html                 # the public site (flywheel.pragmaticgrowth.com) — self-contained, themed
public/Logo*Black.svg             # Pragmatic Growth brand marks (icon + wordmark)
wrangler.jsonc                    # Cloudflare Workers static-assets deploy config for the site
```

## Rules

- **Skills-first (formerly skills-only).** Don't add MCP servers, commands,
  agents, or hooks here without an explicit ask. ONE exception to date: the
  three root `agents/` definitions (the factory's read-only review roles,
  owner-delegated decision 2026-07-16). Keep it minimal: plugin agents
  must stay read-only-by-tools (no Edit/Write/Agent), pin no `model:`, carry
  narrow non-auto-triggering descriptions, and every skill that spawns one keeps
  a `general-purpose` inline-brief fallback so nothing breaks where plugin
  agents are unavailable. A new hook or agent needs the same explicit ask.
  (The repo carried a second exception — `hooks/hooks.json` for the
  `telegram-message` notifier, owner decision 2026-07-07 — from v4.11.0 until
  the v6.0.0 sunset removed the skill and the hook bundle; flywheel ships no
  hooks again.)
- **Portability.** Skills must not contain user-specific absolute paths
  (`/Users/...`, `~/.claude/...`). They run in arbitrary repos.
- **This repo is the single source of truth.** The plugins are installed
  user-scoped from the `pragmatic-growth` marketplace; the former
  user-level copies in `~/.claude/skills/` were deleted on 2026-06-10.
  Root flywheel skill edits land here, bump the root `plugin.json` version,
  push, then
  refresh with `/plugin marketplace update pragmatic-growth`. `html-artifacts`,
  `autoresearch`, and `human-writing` edits
  bump their own `plugins/<name>/.claude-plugin/plugin.json`; if the root
  marketplace copy/docs also change, keep the root release metadata aligned too.
- **Push every time — on every completion, the FULL tree (owner decision
  2026-07-14).** Pushing to GitHub (`origin main`) after committing is
  pre-authorized — always push without asking. Whenever you complete a unit of
  work (a fix, a plugin, a doc change), commit AND push before treating it as
  done; keep everything in the remote. End every turn with a fully-pushed tree:
  no modified or untracked files left dangling (commit them, or say why one
  can't be), no unpushed commits, no unpushed tags — `git status` clean and
  `main` in sync with `origin/main`. The only files that stay local are the
  gitignored maintainer config (`CLAUDE.local.md`, `.claude/settings.json`) and
  tool caches — never force-add those. The installed plugin refreshes from
  GitHub, so an unpushed commit is an unshipped skill.
- **Internal docs are tracked and pushed.** Planning/design artifacts under
  `docs/` (specs, plans, research) are a normal tracked directory as of
  2026-07-01 — commit and push them with the rest. The remote is **public and
  permanent**, so the one hard guard (enforced by the `pre-push` hook) is **no
  secrets/credentials**, and stay mindful of real client/project names in any
  committed file, message, or history. (`CLAUDE.local.md` and
  `.claude/settings.json` remain gitignored local maintainer config.)
- **Validation.** After changing plugin structure or manifests, run the
  `plugin-dev:plugin-validator` agent before committing.
- **Skill edits are tested.** New or changed skill mechanics get a
  subagent dry-run (scenario + "cite the section that decides each
  answer") before shipping; close every flagged ambiguity. For
  compliance-critical rules, add a RED baseline — run the same scenario
  against the pre-change text (`git show HEAD:<file>`) and confirm the old
  text decided it differently or left it undecided, so the rule is proven to
  change behavior, not just read well (adopted from superpowers'
  RED-baseline doctrine, 2026-07-17).

## Public site, changelog & releases (flywheel.pragmaticgrowth.com)

The marketplace has a public landing/docs site at **https://flywheel.pragmaticgrowth.com**,
served from Cloudflare (Workers static assets, Pragmatic Growth account). It is
part of this repo — `public/index.html` (self-contained, light/dark, no external
deps) plus the brand SVGs in `public/`, with `wrangler.jsonc` at the root.

- **Keep the docs current with the skills.** Whenever you change what a skill
  does, how it's invoked, the plugin boundaries, the install commands, or the
  queue/config model,
  update BOTH `public/index.html` AND `README.md` to match in the SAME change.
  The site and README both document the two marketplace plugins, the flywheel
  workflow skills, the html-artifacts plugin, the docs/goals pipeline, the
  config model, and install — drift in either is a
  shipped-but-wrong doc, same severity as a stale SKILL.md.
- **Versioned changelog (CHANGELOG.md is the single source).** `CHANGELOG.md`
  (repo root) is the canonical, git-tracked history. The public site carries NO
  on-page changelog timeline (removed in the site-simplify pass — canonical
  history lives in `CHANGELOG.md` plus the GitHub Releases page). On every
  `plugin.json` version bump: add a `## [X.Y.Z] — <date>` block + a commit link to
  `CHANGELOG.md`, bump the site's `.ver-pill` and `<title>` in `public/index.html`,
  and bump the README's version badge (`version-X.Y.Z`). Never delete history.
- **Tag AND release every version in GitHub (this repo manages its own
  Releases page).** Each version bump gets BOTH an annotated git tag `vX.Y.Z`
  on its bump commit (`git tag -a vX.Y.Z <sha> -m "…"`, `git push --tags`) AND a
  GitHub Release created from that tag. Generate the release notes from the
  version's `CHANGELOG.md` section — the block between `## [X.Y.Z]` and the next
  `## ` — not the bare tag message:
  `gh release create vX.Y.Z --title "vX.Y.Z — <headline>" --notes-file <section> --verify-tag --latest`.
  Pass `--latest` only on the newest version; historical backfills use
  `--latest=false`. Releases are how a reader browses version history on GitHub,
  so one release per version, notes mirroring the changelog, newest = Latest.
  The full backfill (v1.0.0 → current) already exists; on each new bump just add
  the one new release.
- **Redeploy after changes.** From the repo root, with `CLOUDFLARE_API_TOKEN`
  set: `wrangler deploy`. The custom domain `flywheel.pragmaticgrowth.com` is bound
  in `wrangler.jsonc` (the `pragmaticgrowth.com` zone is in the same account), so
  a deploy redeploys to the same URL. Push the repo too — the site source is
  tracked here, single source of truth.
- The site is **content only** — bumping a plugin's own `plugin.json` version is
  NOT required just to ship a site/changelog edit (installed plugins don't
  depend on the site). Bump a plugin manifest only for actual skill changes, and
  when you do, that's the trigger to add the changelog entry + tag above.
