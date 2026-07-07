# flywheel

## Project Overview

Skills-only Claude Code and Droid (Factory CLI) marketplace from Pragmatic Growth.
The repo now publishes four plugins from one `pragmatic-growth` marketplace:
`flywheel` v4.12.0, `html-artifacts` v1.0.0, `autoresearch` v1.0.0, and
`human-writing` v1.0.0. No MCP
servers, no commands, no
agents, no build step, and — as of v4.11.0 — ONE hook bundle
(`hooks/hooks.json`, the `telegram-message` notifier; added by explicit owner
decision 2026-07-07, the first exception to the former skills-only rule).
`flywheel` has five skills under root
`skills/` (three ship deterministic Python helpers in `scripts/`), forming a
plain-language → autonomous-execution pipeline around a file-based goal queue
(`docs/goals/` in target repos). `html-artifacts` lives under
`plugins/html-artifacts/` as a separate plugin for rich
plans/reports/diagrams/editors. `autoresearch` lives under
`plugins/autoresearch/` as a separate plugin for an autonomous try/measure/keep/
revert optimization loop (ships one Python helper). `human-writing` lives under
`plugins/human-writing/` as a separate single-skill plugin for AI-writing
cleanup (pure guidance, no scripts). All four plugins work in
both CLIs via Droid's
Claude Code compatibility layer (Droid auto-translates the `.claude-plugin/`
manifest format). Skills are CLI-aware — they detect the runtime and use
appropriate paths, commands, and scheduling primitives.

- **define-goal** — plain-language wants → measurable goal contracts.
  Two destinations: a copy-pasteable `/goal` line (Claude Code) or
  `droid exec --auto high "…"` (Droid) to run now, or a queued
  goal file (`docs/goals/NNN-slug.md` + `index.yaml` entry). Includes
  repo grounding (CLAUDE.md/AGENTS.md rules copied verbatim, real
  verification commands) and a batch mode for documents of items.
  Produces goals only, never implements. Originally adapted from
  OpenAI's curated `define-goal` skill (its `create_goal`/`get_goal`
  tools don't exist in either CLI; `/goal` is user-run, transcript-
  evaluated in Claude Code, self-verified by the agent in Droid,
  4,000-char condition cap).
- **dispatch** — factory orchestrator for the docs/goals queue: works ONE
  ready goal per run on the branch that's currently checked out — no PRs, no
  worktrees, no `goal/<id>` branches, no parallel implementation. Per goal it
  records the pre-claim clean
  HEAD as `anchor`, commits the claim, records the post-claim HEAD as
  `gate_base`, spawns ONE foreground implementer that commits its work
  directly on the branch, using a lightweight subagent-driven quality loop
  (plan/checklist, TDD, fresh verifier/reviewer subagent for non-trivial work),
  then runs the LOCAL gate authoritatively: a review-evidence check (the
  implementer's report must carry its `Fresh-check:` lens verdicts or an
  explicit not-required line — missing ⇒ the orchestrator runs the 2–3
  read-only review lenses itself, feeding verified findings into the repair
  path), then the deterministic `pg_validate.py`
  over the `gate_base..HEAD` diff plus the repo's `config.verify` build+test
  commands. PASS → squash the goal's commits to one `feat(goal NNN)` commit
  and mark it `completed`; FAIL → `git reset --hard gate_base` and mark it
  `blocked` (with reason). CI, if the repo has it, is a NON-BLOCKING post-push
  observation surfaced under needs-you — never a merge gate. Built to repeat as
  `/loop 15m /dispatch` (Claude Code) or `CronCreate` same_session every 15m
  (Droid); each fire handles at most one new goal and is idempotent. Each fire emits one report
  line leading with progress — `<done>/<total> done` plus a 20-cell fill
  bar, then labeled `ready`/`blocked` counts that sum to `total`
  (lead with done, never `ready/total`, which reads as "nothing done");
  `needs-you` holds human-blocked goals plus any non-blocking CI failures.
  Each fire APPENDS a heartbeat line (`~/.local/state/pg-dispatch/<SLUG>/heartbeat`,
  newest ~50 kept); the cross-fire brake counts heartbeat lines after a stale
  claim's date (≥3 fires with zero work commits → `blocked: repeated transient
  death`) instead of wall-clock age, so an account usage-limit pause (no fires
  → no lines) resumes a claim rather than mislabeling it dead.
- **loop-architect** — designs loop contracts (prompt + verification +
  stop conditions) for autonomous /goal, /loop, routine, or remote runs;
  names `docs/goals/index.yaml` the canonical factory ledger. Includes
  usage-limit proofing (Step 5): subscription 5-hour/weekly limits kill
  in-session loops with no hook fired, so unattended drains schedule OUTSIDE
  the session (cron/launchd firing fresh `claude -p "/dispatch"`; Droid
  `CronCreate new_session`), optionally reading the reset clock from statusline
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
  to provision — the gate is local. The probe checks settings in both
  `.claude/` and `.factory/` (Droid) paths.
- **telegram-message** (v4.11.0, scopes + Droid/cloud in v4.12.0) —
  `/telegram-message <bot_token> [chat_id]` wires a Telegram bot to DM the owner
  when an autonomous run needs a human: an API/usage-limit error killed a turn
  (`StopFailure`), the agent is waiting on a permission/idle prompt
  (`Notification`), a run finished (`SessionEnd`), or a dispatch fire reported
  (hook-free `dispatch` category — dispatch Phase 4 pipes its report line to the
  notifier). Personal settings are PROJECT-SCOPED by default and always OUTSIDE
  the repo (structurally unpushable): chmod-600
  `~/.local/state/pg-telegram/projects/<slug>.json` (longest-`project_root`-
  prefix match on cwd; `enabled:false` = per-project opt-out), `--global` for
  the machine-wide fallback, `PG_TELEGRAM_BOT_TOKEN`/`PG_TELEGRAM_CHAT_ID`(/
  `PG_TELEGRAM_EVENTS`) env vars for cloud runs — resolution env > project >
  global. Hook events verified on Claude Code incl. headless `claude -p`;
  **Droid gets dispatch-category pings only** (no error hook exists AND hooks
  don't fire under `droid exec`/`CronCreate` — empirically tested 2026-07-07).
  Stdlib notifier `scripts/pg_telegram_notify.py` never crashes a session and
  no-ops until configured. Sets up notifications only; never implements goals.

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
  resolved via `$CLAUDE_PLUGIN_ROOT`/`$DROID_PLUGIN_ROOT`) under
  `plugins/autoresearch/skills/autoresearch/`. CLI-aware: `/loop` (Claude Code)
  or same-session `CronCreate` (Droid) for unattended cadence. Adapted from
  Factory's `autoresearch` plugin (MIT).
- **human-writing** — edits AI-sounding text into human prose: scans for the tells
  catalogued in Wikipedia's "Signs of AI writing" (inflated significance,
  promotional language, `-ing` filler, em-dash/rule-of-three overuse, AI
  vocabulary, vague attributions, chatbot artifacts), rewrites them, and pushes
  for real voice. Deliberately CLI-neutral — pure writing guidance, one
  `SKILL.md`, no scripts/state/references, so it needs no runtime translation.
  Single skill under `plugins/human-writing/skills/human-writing/`. Based on
  Wikipedia's guide (WikiProject AI Cleanup, CC BY-SA); adapted from Factory's
  `droid-evolved` plugin.

## Queue design invariants (research-backed; v4.1.x one-goal dispatch model, 2026-06-28)

- **v4.1.x one-goal dispatch model.** dispatch works ONE ready goal per run,
  committing work DIRECTLY on the branch that's checked out — no PRs, no
  worktrees, no `goal/<id>` branches, no parallel implementation. Each
  goal is bracketed by two anchors: `anchor` (the pre-claim clean HEAD) and
  `gate_base` (HEAD right after the claim commit). The implementer commits on
  the branch; then the orchestrator runs the LOCAL gate over the
  `gate_base..HEAD` diff — `pg_validate.py` plus the repo's `config.verify`
  commands — and that local gate is the ONLY merge gate. PASS → squash the
  goal's commits into one `feat(goal NNN)` commit + `completed`; FAIL →
  `git reset --hard gate_base` + `blocked`. CI, where the repo has it, is a
  NON-BLOCKING post-push observation surfaced under needs-you, never a gate.
  `/loop /dispatch` or Droid same-session cron advances the queue by repeating the
  same one-goal run.
- Status lives ONLY in `index.yaml`, never in goal-file frontmatter —
  dual-write drifts. Goal files are immutable contracts.
- Statuses: `not_started | in_progress | completed | blocked` — blocked
  (with reason) is required to avoid re-dispatch livelock. `completed`
  only when the gate has PASSED and the goal's commit is on the branch.
- `index.yaml` `config:` block: `base` (the branch goals are worked on;
  per-goal `base:` override allowed), `model` (inherit|sonnet|haiku —
  applied to every code agent dispatch spawns; the repo owner's
  depth-vs-limit trade), repo-wide `skills`, `verify` (the ordered local
  build+test commands the gate runs after each implementer), and `budget`
  (optional; `max_goals_per_session` + optional `max_iterations` — a simple
  cap on cumulative spend across repeated dispatch fires; absent = no loop cap).
  Defaults: repo default branch, inherit, no extra skills, repo-detected
  verify commands, no budget.
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
  inherit the current session/runtime model; do not set a fixed model alias,
  including Sonnet, unless the user explicitly asks for it in that run.
  In Claude Code, use the `general-purpose` type without a model override,
  strictly read-only, and avoid the built-in Explore type if it would force a
  cheaper model instead of inheriting the current one. The optional synthesis
  agent also inherits the current session/runtime model. `config.model`
  governs only code-writing agents, never recon. (Recon stays plain parallel
  subagents, NOT a Workflow: 2–4 agents is below the workflow scale threshold
  and a workflow can be disabled on a user's machine — define-goal batch mode
  is the only place that conditionally uses Workflow.)
- Workflow tool only where the docs' thresholds say it wins: define-goal
  batch mode at ~5+ items (drafts in script variables, approval table
  gates file writes). Dispatch implementers may use workflow/mission mode only
  for bounded read-only fan-out or review inside a single goal; they are NEVER
  workflows for parallel code-writing or cross-run state. The branch commits +
  the two-anchor rollback are the recovery path. The tool needs CLI ≥2.1.154 and
  can be disabled, so skills never assume it.

History note: this repo was previously `mcp-do`, a stdio MCP server
wrapping droid/opencode CLIs (removed in v1.0.0 at ac2bd7c). The
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
a local gate. Git history has every prior model if ever needed.

## Structure

```
.claude-plugin/plugin.json        # root flywheel plugin manifest
.claude-plugin/marketplace.json   # marketplace — name: pragmatic-growth, lists flywheel + html-artifacts + autoresearch + human-writing
hooks/hooks.json                  # flywheel plugin hooks — telegram-message notifier (v4.11.0; Claude Code)
skills/<name>/SKILL.md            # five flywheel skills (define-goal, dispatch, loop-architect, factory-doctor, telegram-message)
plugins/html-artifacts/.claude-plugin/plugin.json
plugins/html-artifacts/skills/html-artifacts/SKILL.md
plugins/html-artifacts/skills/html-artifacts/references/ # HTML artifact recipes and foundation rules
plugins/autoresearch/.claude-plugin/plugin.json
plugins/autoresearch/skills/autoresearch/SKILL.md
plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py # stdlib JSONL/MAD-confidence helper
plugins/human-writing/.claude-plugin/plugin.json
plugins/human-writing/skills/human-writing/SKILL.md # AI-writing cleanup (no scripts)
skills/<name>/scripts/*.py        # dispatch/pg_validate.py (local gate), factory-doctor/doctor_checks.py, telegram-message/pg_telegram_notify.py
CHANGELOG.md                      # canonical, git-tracked version history (site carries no on-page changelog)
public/index.html                 # the public site (plugin.pragmaticgrowth.com) — self-contained, themed
public/Logo*Black.svg             # Pragmatic Growth brand marks (icon + wordmark)
wrangler.jsonc                    # Cloudflare Workers static-assets deploy config for the site
AGENTS.md                         # symlink → CLAUDE.md (one source, no drift)
```

## Rules

- **Skills-first (formerly skills-only).** Don't add MCP servers, commands,
  agents, or hooks here without an explicit ask. The sole hook exception to date
  is `hooks/hooks.json` (the `telegram-message` notifier, explicit owner decision
  2026-07-07). Keep it minimal: hooks must no-op safely when unconfigured and
  never disrupt a session; a new hook needs the same explicit ask.
- **Portability applies to the notifier too.** The `telegram-message` config and
  state live under `~/.local/state/pg-telegram/`; the bot token NEVER enters the
  repo, `hooks/hooks.json`, or any tracked file (the pre-push secret hook is the
  backstop). Notifier resolves its own path at runtime via `${CLAUDE_PLUGIN_ROOT}`.
- **Portability.** Skills must not contain user-specific absolute paths
  (`/Users/...`, `~/.claude/...`, `~/.factory/...`). They run in arbitrary repos.
- **This repo is the single source of truth.** The plugins are installed
  user-scoped from the `pragmatic-growth` marketplace; the former
  user-level copies in `~/.claude/skills/` were deleted on 2026-06-10.
  Root flywheel skill edits land here, bump the root `plugin.json` version,
  push, then
  refresh with `/plugin marketplace update pragmatic-growth` (Claude Code)
  or `droid plugin marketplace update flywheel` (Droid; Factory registers the
  GitHub marketplace as `flywheel`). `html-artifacts`, `autoresearch`, and
  `human-writing` edits
  bump their own `plugins/<name>/.claude-plugin/plugin.json`; if the root
  marketplace copy/docs also change, keep the root release metadata aligned too.
- **Keep CLAUDE.md and AGENTS.md aligned.** `AGENTS.md` is a symlink to
  `CLAUDE.md`; preserve that one-source setup. When Claude Code updates
  `CLAUDE.md`, it must verify `AGENTS.md` reflects the same content. When Codex
  or Droid updates `AGENTS.md`, it must update `CLAUDE.md` too (prefer editing
  `CLAUDE.md` and keeping `AGENTS.md` as the symlink). If the symlink is missing
  or broken, restore it or update both filenames in the same commit. Do not leave
  either name stale.
- **Push every time — on every completion.** Pushing to GitHub (`origin main`)
  after committing is pre-authorized — always push without asking. Whenever you
  complete a unit of work (a fix, a plugin, a doc change), commit AND push before
  treating it as done; keep everything in the remote. The installed plugin
  refreshes from GitHub, so an unpushed commit is an unshipped skill.
- **Internal docs are tracked and pushed.** Planning/design artifacts under
  `docs/` (specs, plans, research) are a normal tracked directory as of
  2026-07-01 — commit and push them with the rest. The remote is **public and
  permanent**, so the one hard guard (enforced by the `pre-push` hook) is **no
  secrets/credentials**, and stay mindful of real client/project names in any
  committed file, message, or history. (`CLAUDE.local.md` and
  `.claude/settings.json` remain gitignored local maintainer config.)
- **Validation.** After changing plugin structure or manifests, run the
  `plugin-dev:plugin-validator` agent before committing (Claude Code only;
  Droid has no equivalent agent — validate manually: check skill frontmatter
  has `name` + `description`, then test the published Claude-compatible
  marketplace path with `droid plugin marketplace add https://github.com/pragmaticgrowth/flywheel`
  (skip if already added), `droid plugin marketplace list`, and
  `droid plugin install flywheel@flywheel` plus
  `droid plugin install html-artifacts@flywheel` / `droid plugin install autoresearch@flywheel`
  / `droid plugin install human-writing@flywheel` when those plugins change.
  `droid plugin link .` is only for native
  `.factory-plugin` plugins, not this `.claude-plugin` manifest).
- **Skill edits are tested.** New or changed skill mechanics get a
  subagent dry-run (scenario + "cite the section that decides each
  answer") before shipping; close every flagged ambiguity.

## Public site, changelog & releases (plugin.pragmaticgrowth.com)

The marketplace has a public landing/docs site at **https://plugin.pragmaticgrowth.com**,
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
  shipped-but-wrong doc, same severity as a stale SKILL.md. (`AGENTS.md` is a
  symlink to this file; no separate edit.)
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
  set: `wrangler deploy`. The custom domain `plugin.pragmaticgrowth.com` is bound
  in `wrangler.jsonc` (the `pragmaticgrowth.com` zone is in the same account), so
  a deploy redeploys to the same URL. Push the repo too — the site source is
  tracked here, single source of truth.
- The site is **content only** — bumping a plugin's own `plugin.json` version is
  NOT required just to ship a site/changelog edit (installed plugins don't
  depend on the site). Bump a plugin manifest only for actual skill changes, and
  when you do, that's the trigger to add the changelog entry + tag above.
