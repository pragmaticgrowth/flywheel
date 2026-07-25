# Design: Dual-target flywheel — Factory Droid + Claude Code, native tier vocabulary

**Date:** 2026-07-25
**Author:** Serkan (via Droid)
**Status:** Approved approach (B), pending spec review

## Goal

Make the `pragmatic-growth` marketplace and all four plugins work first-class in
**Factory Droid** while keeping **Claude Code** first-class, with
**heavy / medium / light** as the native execution-tier vocabulary replacing
opus / sonnet / haiku in skill text and goal contracts. Old model names remain
valid read-time aliases forever.

## Relationship to v5.0.0 (conscious reversal)

`docs/superpowers/specs/2026-07-11-droid-removal-claude-only-design.md` removed
the previous dual-CLI support (owner decision, shipped as v5.0.0). This design
reverses that direction by owner decision 2026-07-25, but does NOT restore the
old architecture. The v4.x dual support failed because it was **dual-branch
prose** ("in Claude Code do X; in Droid do Y") plus a per-repo
`config.droid_models` mapping table — two vocabularies maintained everywhere,
drift-prone. The new architecture is **one harness-neutral vocabulary (tiers)**
plus one small per-skill harness-mapping block. Git history (pre-v5.0.0) is
reference material only; no old Droid branch is restored verbatim.

## Approved decisions (owner, 2026-07-25)

1. **Dual-target, both first-class.** Tiers are the native vocabulary; each
   harness maps them. Claude Code support is preserved exactly (no behavior
   regression for Claude Code users beyond the vocabulary rename).
2. **Tier vocabulary:** `inherit | heavy | medium | light`.
   - Claude Code mapping: heavy → `opus`, medium → `sonnet`, light → `haiku`.
   - Droid mapping: heavy / medium / light are Droid's own complexity tiers
     (Task-tool `complexity` param and custom-droid routing); `inherit` = the
     session model, both harnesses.
3. **Legacy aliases forever:** `opus`/`sonnet`/`haiku` in existing goal
   frontmatter or `config.model` are read as heavy/medium/light wherever
   consumed (dispatch, goals-status, factory-doctor, tests). New goals are
   always stamped with tier names. No hard break; no re-stamping required.
4. **define-goal stays** and is ported like every other skill (owner correction
   2026-07-25 after a mistaken deletion request — the skill was deleted only
   from user-level installed skills, never from the repo).
5. **Unattended scheduling doctrine is harness-parallel:** an OS scheduler
   (cron/launchd/Task Scheduler) firing fresh sessions —
   `claude -p "/dispatch"` on Claude Code, `droid exec "/dispatch"` on Droid.
   Droid's built-in CronCreate/automations are NOT the primary rail (session-
   bound loops die with the session — the exact failure Step 5 exists to avoid);
   loop-architect may mention them as building blocks only.
6. **Verification against live Droid during the work** — every Droid-side claim
   (subagent types, `droid exec` flags, plugin translation behavior, tool
   names, path resolution) is verified in this Droid environment before it is
   written into a skill, mirroring the v5.3.0 verified-facts doctrine for
   `/goal`. Skill-mechanic edits get the repo-mandated subagent dry-runs with
   RED baselines.
7. **AGENTS.md is intentional:** commit the untracked root `AGENTS.md` and keep
   it current as the harness-neutral agent guide alongside CLAUDE.md.

## Architecture

### 1. Tier vocabulary (the core change)

- Goal frontmatter `model:` and `index.yaml` `config.model` take
  `inherit | heavy | medium | light` (field name stays `model:` — renaming the
  key would break every existing queue; the VALUES change).
- **define-goal** stamps tiers from the same rubric, relabeled:
  heavy = DEFAULT for every `type: feature`/`type: bug` goal (tightness never
  downgrades; explicit user ask for cheap execution is the only route down);
  medium = rote chore-shaped work only; light = truly rote one-file mechanical
  chores, with the turn-count-beats-token-price caution. The rubric's reasoning
  is unchanged — only the names.
- **dispatch** resolves goal `model:` > `config.model` > inherit exactly as
  today, then maps at spawn time per harness: Claude Code → `model:` pin on the
  implementer subagent; Droid → `complexity` on the Task spawn. The escalation
  ladder's "stronger-model re-spawn for capability-shaped blockers" applies to
  medium/light-stamped goals (was sonnet/haiku) and escalates to heavy.
- **Alias table** (single canonical statement in dispatch, referenced
  elsewhere): `opus→heavy`, `sonnet→medium`, `haiku→light`, applied wherever a
  tier value is READ. `goals_status.py` and `doctor_checks.py` normalize via
  the same 3-entry mapping; script tests cover both vocabularies.

### 2. Subagent spawning (harness mapping block)

Each skill that spawns subagents describes roles harness-neutrally and carries
ONE short mapping block:

- **Claude Code:** `general-purpose` type with an explicit `model:` pin
  (gather/recon on the medium tier = sonnet); the built-in `Explore` type stays
  banned (model unpinnable). Plugin agents spawn as `flywheel:<name>` when
  available, `general-purpose` + inline brief fallback — unchanged.
- **Droid:** `worker` (read-write roles) / `explorer` (read-only gather) with
  the `complexity` param (gather/recon on medium); plugin `agents/*.md` are
  auto-translated to Droid custom droids and spawn by name when available, with
  the same inline-brief fallback. Exact type names, param names, and
  translation behavior are live-verified before writing (decision 6).
- The gather-on-medium / judgment-on-session-model split (v6.2.0) is preserved
  verbatim in tier terms.

### 3. Plugin agents (`agents/*.md`)

Kept in the Claude Code layout (Droid translates automatically). Tool
allowlists are audited against BOTH harnesses' tool names so the read-only
guarantee holds on Droid too (e.g. Droid's `Create`/`ApplyPatch` must be
excluded just as `Edit`/`Write` are); pin no model, per the existing rule.

### 4. Scheduling rail (loop-architect Step 5, factory-doctor limit-resilience)

Doctrine unchanged, expressed per harness: unattended drains schedule OUTSIDE
the session via an OS scheduler firing fresh `claude -p "/dispatch"` or
`droid exec "/dispatch"` sessions. `doctor_checks.py`:

- `_external_scheduler_evidence` patterns gain `droid exec`.
- Settings/hook probes check both `.claude/` and `.factory/` (project and
  user scope).
- The limit-resilience fix string names both commands.

The Claude-Code-specific reset-clock details (statusline
`rate_limits.*.resets_at`, `StopFailure` rate_limit hook) stay, labeled as
Claude Code facts; Droid equivalents are added only if live-verified to exist.

### 5. Path portability

- `$CLAUDE_PLUGIN_ROOT` stays the primary script-resolution variable (Droid
  aliases it to `$DROID_PLUGIN_ROOT`).
- Every `find`/glob fallback over `~/.claude/plugins/...` gains a parallel
  `~/.factory/plugins/...` candidate (dispatch, goals-status, factory-doctor,
  autoresearch SKILL.mds). Newest match wins across both.
- `pg_validate.py` `FORBIDDEN_PATHS` adds `.factory/*` alongside `.claude/*`.
- The portability rule in CLAUDE.md widens: no user-specific absolute paths for
  EITHER harness.

### 6. define-goal run-now destination

- Claude Code: the copy-pasteable `/goal` line, all v5.3.0 verified evaluator
  facts intact (labeled as Claude Code facts).
- Droid: run-now = a self-contained prompt block for a fresh
  `droid exec` session — the full contract inline (outcome, acceptance
  criteria, verification commands, stop conditions), no evaluator assumed.
  The 4,000-char condition cap and transcript-evaluation facts are `/goal`-
  specific and do not constrain the Droid block.
- The queue destination (goal file + index entry) is identical on both
  harnesses — the file-based queue is already harness-neutral.

### 7. Other plugins

- **autoresearch:** helper-path resolution gains the `~/.factory/plugins/...`
  fallback; unattended cadence text names both `/loop` (Claude Code) and the
  OS-scheduler + `droid exec` pattern. Minor bump.
- **html-artifacts, human-writing:** pure-guidance content already
  harness-neutral; descriptions mention both harnesses. Patch bumps only if
  text changes.

### 8. Docs, site, manifests, versioning

- **CLAUDE.md** rewritten for dual-target + tier vocabulary; **AGENTS.md**
  committed and aligned (harness-neutral commands/architecture; CLAUDE.md ↔
  AGENTS.md kept consistent as part of the doc-currency rule).
- **README.md + public/index.html:** dual install instructions
  (`/plugin marketplace add` for Claude Code; `droid plugin marketplace add`
  for Droid), tier vocabulary in the config/goal examples, version badge/pill.
- **Root `plugin.json` 6.2.0 → 7.0.0** (major: vocabulary change in stamped
  goal contracts, even with aliases). CHANGELOG entry, annotated tag `v7.0.0`,
  GitHub Release, `wrangler deploy`, push — per the standing release rules.
- The two root-level tests (`test_skill_inventory.py`,
  `test_docs_model_policy.py`) — already failing against `main` per AGENTS.md —
  are updated to assert the new tier-vocabulary inventory so the full suite
  goes green.

## Verification plan

1. **Live-verify Droid facts first** (before writing skill text): Task-tool
   subagent types + `complexity` values; custom-droid translation of
   `agents/*.md`; `droid exec` invocation shape; `$CLAUDE_PLUGIN_ROOT`
   aliasing; plugin install of this marketplace into Droid
   (`droid plugin marketplace add` + install, both scopes).
2. **Script tests:** extend `test_goals_status.py`, `test_doctor_checks.py`,
   `test_pg_validate.py` for tier names + legacy aliases + `.factory/*` paths;
   `python3 -m pytest -q` green at repo root.
3. **Subagent dry-runs with RED baselines** for changed skill mechanics
   (repo rule): tier stamping in define-goal, dispatch tier resolution +
   escalation ladder, scheduling-rail text — old text must decide differently.
4. **End-to-end smoke in Droid:** install the plugins into this Droid session,
   run `/goals-status` and `/factory-doctor` against a scratch queue, and one
   `/dispatch` cycle on a trivial goal.
5. Manifest validation (plugin-validator agent on Claude Code side).

## Definition of done

1. All six flywheel skills + three agents + four plugins install and function
   in Droid (verified live) and in Claude Code (no regression).
2. `grep -rn "opus\|sonnet\|haiku"` in active skill/script/doc files returns
   only: the alias table, harness-mapping blocks, alias-coverage tests in the
   script test files, and history (CHANGELOG, docs/superpowers/**).
3. Legacy-stamped queues (opus/sonnet/haiku) work unmodified through dispatch,
   goals-status, and factory-doctor.
4. Full pytest suite green, including the two root-level tests.
5. Docs/site/README/CLAUDE.md/AGENTS.md consistent; v7.0.0 shipped per the
   standing release rules (tag, Release, deploy, push).

## Non-goals

- No restoration of the v4.x `config.droid_models` mapping, the `--runtime`
  flag, or dual-branch prose style.
- No renaming of the goal frontmatter KEY (`model:` stays; values change).
- No re-stamping of existing goal files in target repos.
- No Droid-built-in-automations primary rail (building-block mention only).
- No telegram-message revival (sunset in v6.0.0 stands).
