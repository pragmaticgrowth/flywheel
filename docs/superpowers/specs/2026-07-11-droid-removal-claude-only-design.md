# Design: Remove Droid, make flywheel Claude-Code-only

**Date:** 2026-07-11
**Author:** Serkan (via Claude Code)
**Status:** Approved scope, pending spec review

## Goal

Remove every Droid / Factory-CLI code path and dual-CLI framing across the whole
repo so the `pragmatic-growth` marketplace and all four plugins target **Claude
Code exclusively**. After this change, `grep -ri droid` returns hits only in
historical records (see "History policy").

## Approved decisions

- **Scope: whole repo** — all 4 plugins, scripts, README, public site, CLAUDE.md.
- **History intact** — `CHANGELOG.md` and `docs/superpowers/**` are left untouched
  (they record what actually shipped). One new `CHANGELOG.md` entry documents this
  removal. The CLAUDE.md "History note" provenance sentence about the former
  `mcp-do` MCP server is reworded to drop the literal word "droid" but keep the
  fact.
- **Remove AGENTS.md** — delete the symlink and every rule/structure line/
  parenthetical that references keeping CLAUDE.md ↔ AGENTS.md aligned.
- **Version bumps:** flywheel root `4.16.0 → 5.0.0` (major: a whole supported
  runtime is dropped). Other plugins, bump only what changed:
  `autoresearch 1.0.1 → 1.1.0` (removes the CronCreate cadence branch — behavior
  change), `html-artifacts 1.0.0 → 1.0.1` and `human-writing 1.0.0 → 1.0.1`
  (stray-ref doc edits).

## Two judgment calls — RESOLVED

1. **Attribution lines — PURGE (owner decision 2026-07-11).** Remove the five
   *"Adapted from Factory's `<x>` plugin (MIT)"* credits and all references to
   **Factory the company** (`Factory CLI`, `Factory app`, `Factory web app`,
   `Droid Computers`, `factory.ai`). **Scope guard:** this means Factory the
   *company* only — it does NOT rename the `factory-doctor` skill, the
   "flywheel factory" metaphor, or any generic "factory" pipeline language, which
   are flywheel's own naming. If a `LICENSE` file carries an upstream copyright
   notice, that legal instrument is left intact (prose credits are what's purged).
2. **Target-repo grounding source — CLAUDE.md only (owner decision 2026-07-11).**
   Drop "/ AGENTS.md" from define-goal's and README's grounding mentions; the
   Claude-Code-only skill grounds on the CLAUDE.md convention.

## Removal policy — three kinds of Droid content

1. **DUAL-BRANCH** ("in Claude Code do X; in Droid do Y") → keep the Claude Code
   branch, delete the Droid branch, and drop the "in Claude Code" qualifier so
   the prose reads single-target.
2. **DROID-ONLY** (features that exist only for Droid) → delete entirely:
   `config.droid_models`, factory-doctor's droid-models interview, the
   `doctor_checks.py --runtime droid` flag + `droid_models_check`, `.factory/`
   path probing, `$DROID_PLUGIN_ROOT` fallbacks, `CronCreate` scheduling, the
   telegram "Droid gets dispatch-only pings" caveats.
3. **FRAMING** ("CLI detection", "CLI-aware", "detect the runtime", "works in
   both CLIs") → reword to drop CLI-awareness; the skill simply targets Claude
   Code.

## Per-file edit plan

Derived from a full line-anchored inventory (three research passes). Anchors are
approximate; implementation reads current line state before each edit.

### Skills (`skills/<name>/SKILL.md`)

- **define-goal** (17 hits): delete the top "CLI detection" para; rename
  "Goal command facts (CLI-specific)" → "Goal command facts"; delete every
  `droid exec --auto high` paragraph; collapse AskUserQuestion dual-branches;
  the recon per-run model override loses its Droid model-ID half; the model
  resolution note loses "in Droid … config.droid_models …"; batch mode loses
  the "Droid mission mode" aside.
- **dispatch** (9 hits): `/loop /dispatch` only (drop "or same-session Droid
  cron"); delete the `config.droid_models` half of implementer-model resolution;
  PushNotification framed as the tool (drop "Droid has no PushNotification");
  drop the `~/.factory/plugins/...` fallback parenthetical; "mission mode" →
  "Workflow mode"; delete the "on Droid — model alias unmapped" needs-you item;
  drop "works identically in Claude Code, Droid, and cloud … on Droid hooks
  don't fire" → "Claude Code and cloud runs".
- **factory-doctor** (7 hits): delete the "CLI detection" block; collapse the
  script-path candidate list to the two Claude paths; drop the `--runtime` flag
  from the invocation; **delete the entire `droid-models` fix bullet** (the whole
  interview subsystem); user-scope settings path → `~/.claude/settings.json`;
  remove the `models:` status-line field + its explanatory parenthetical.
  (Do NOT touch generic "factory"/"factory-doctor" naming — that's flywheel's own
  pipeline metaphor, not Factory CLI.)
- **loop-architect** (17 hits): delete the "CLI detection" block; **collapse the
  11-row × 3-column primitive table to 2 columns** (drop the Droid column and the
  now-redundant "Claude Code" header); every "workflow (Claude Code) or mission
  mode (Droid)" → "workflow"; delete the `droid exec --auto high` paragraph;
  `/loop 10m` only; drop CronCreate same_session/new_session prose; the usage-
  limit-proofing section keeps `cron/launchd firing claude -p` and drops
  `CronCreate new_session`; remote/notification sections drop Droid Computers /
  Factory app clauses.
- **telegram-message** (6 hits): replace the CLI-split intro paragraph with one
  sentence ("Claude Code gets the full hook set plus dispatch pings"); env-var
  cloud scope keeps cloud, drops "Droid automations"; "Hook wiring (Claude Code)"
  → "Hook wiring"; the dispatch category drops "the only category that fires on
  Droid"; **delete the "Droid:" bullet** and rename "## Droid & cloud" → "## Cloud".

### Scripts

- **`factory-doctor/scripts/doctor_checks.py`**: delete the `--runtime` argparse
  arg + the `auto→droid/claude` / `DROID_PLUGIN_ROOT` resolution; drop `runtime`
  from `run_checks()`; **delete `ANTHROPIC_ALIASES`, `droid_models_check()`, its
  call site, and the `goal_models` accumulation + `_frontmatter_model()`** (all
  dead once the check is gone — no other caller); in `_has_stop_failure_hook`
  drop `".factory"` from both candidate tuples and reword the "both CLIs" comment;
  drop `"droid exec"` from `_external_scheduler_evidence`'s pattern tuple; drop
  the `Droid: CronCreate new_session` clause from the limit-resilience fix string.
- **`factory-doctor/scripts/test_doctor_checks.py`**: delete the six
  `test_droid_models_*` tests (they call the removed function). No other test
  changes.
- **`telegram-message/scripts/pg_telegram_notify.py`**: reword the one docstring
  parenthetical ("routines / Droid automations" → "cloud runs"). No code change.

### Other plugins

- **autoresearch** SKILL.md (8 hits): delete the "CLI detection" para; drop the
  Droid cadence bullet and reword the lead-in/stop instruction to `/loop` only;
  delete `$DROID_PLUGIN_ROOT` + `~/.factory/...` from the helper-path resolution
  list and bash snippet; drop "(Claude Code and Droid alike)"; drop the Droid
  mission-worker sentence. Keep the MIT attribution. → `plugin.json 1.0.1→1.1.0`,
  drop "and Droid" from description.
- **html-artifacts** source-map.md (1 hit): "works in Claude Code, Droid, local
  browsers…" → drop "Droid". → `plugin.json 1.0.0→1.0.1`, drop "and Droid" from
  description.
- **human-writing** SKILL.md (1 hit): "Works the same in Claude Code and Droid —
  it's pure writing guidance…" → "Pure writing guidance, no runtime-specific
  mechanics." Keep the MIT attribution. → `plugin.json 1.0.0→1.0.1`.

### Docs & manifests

- **CLAUDE.md** (37 hits): rewrite the Project Overview + per-skill bullets to
  drop Droid; delete the "works in both CLIs via Droid's compatibility layer /
  CLI-aware" sentences; delete the `droid_models` config-block clause + default;
  delete the AGENTS.md alignment rule, the Structure `AGENTS.md` line, and the
  public-site AGENTS.md parenthetical; collapse the Validation rule to just the
  plugin-validator agent; the marketplace-refresh rule drops the `droid plugin
  marketplace update` alternative; portability rule drops `~/.factory/...`;
  reword the mcp-do provenance to drop "droid".
- **README.md** (26 hits): drop the Droid link/badge in the header; both-
  destinations → `/goal` only; dispatch cadence → `/loop /dispatch`; loop-
  architect primitive clause dropped; factory-doctor "both .claude/ and .factory/"
  → ".claude/"; telegram bullet → "Cloud covered too"; autoresearch "both CLIs"
  → single; human-writing clause simplified; **delete the config `droid_models`
  yaml lines + table row**; **delete the Droid install block + the Droid headless
  quick-start block + the "Works in both CLIs" section**; fix the dangling
  `#works-in-both-clis` anchor; project-layout tree drops AGENTS.md; bump the
  version badge `4.16.0 → 5.0.0`.
- **public/index.html** (25 hits): drop "and Droid" from `<title>`/meta/og-alt/
  hero badge; **repurpose or drop the "2 CLIs, one marketplace" hero stat**;
  factory-doctor + telegram skill cards drop their Droid sentences; **strip
  `droid_models` from the config example `<pre>` and its copy string**; install
  intro → "One marketplace, four plugins."; **remove the Droid install tab and
  collapse the tab UI to a single install block**; delete the Droid install pane
  + the Droid headless-doctor code block; bump `<title>` + `.ver-pill`
  `4.16.0 → 5.0.0`.
- **`.claude-plugin/plugin.json`**: `version 4.16.0 → 5.0.0`; description drops
  "and Droid (Factory CLI)"; keywords drop `"factory"` + `"droid"`.
- **`.claude-plugin/marketplace.json`**: top-level + flywheel-plugin descriptions
  drop "and Droid".
- **`hooks/hooks.json`**: description ends at "All three events are Claude
  Code-verified." (drop the Droid sentence).
- **`CHANGELOG.md`**: add `## [5.0.0] — 2026-07-11` block (Droid removal) +
  commit link. Do not alter prior entries.

## Definition of done

1. `grep -rIi droid` over the repo (excluding `.git/`) returns hits **only** in
   `CHANGELOG.md` and `docs/superpowers/**` (history) — plus the single new
   CHANGELOG entry. No `droid`/`.factory`/`CronCreate`/`DROID_PLUGIN_ROOT`/
   `droid_models` in any active skill, script, manifest, README, or site file.
   `grep -rn "AGENTS.md"` returns nothing (symlink and all refs gone).
2. `python3 skills/factory-doctor/scripts/test_doctor_checks.py` passes.
3. `python3 skills/factory-doctor/scripts/doctor_checks.py --base main` still
   runs and emits valid JSON (smoke test).
4. Manifests validate (plugin-validator agent).
5. Version bumps + CHANGELOG + site ver-pill/title + README badge all consistent.
6. Ship: commit, annotated tag `v5.0.0`, GitHub Release from the CHANGELOG
   section, `wrangler deploy` (site), `git push origin main --tags`.

## Non-goals

- No behavior change for Claude Code users — every Claude Code path is preserved
  exactly. This is pure Droid removal + version/doc alignment.
- No rewrite of CHANGELOG history or `docs/superpowers/**` prior artifacts.
- No renaming of "factory"/"factory-doctor"/"flywheel factory" (own metaphor).
