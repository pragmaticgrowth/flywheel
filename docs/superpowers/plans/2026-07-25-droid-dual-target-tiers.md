# Dual-Target (Droid + Claude Code) Tier Vocabulary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all four `pragmatic-growth` plugins first-class in Factory Droid AND Claude Code, with `heavy|medium|light` as the native execution-tier vocabulary (legacy `opus|sonnet|haiku` read as aliases forever).

**Architecture:** One harness-neutral tier vocabulary in skill text, goal contracts, and scripts; each spawning skill carries ONE short harness-mapping block (Claude Code: tier→model pin; Droid: tier→Task `complexity`). Scripts normalize legacy aliases at read time. Scheduling doctrine is harness-parallel (`claude -p` / `droid exec` via OS scheduler).

**Tech Stack:** Markdown skills, stdlib Python 3 + PyYAML helpers, pytest.

**Spec:** `docs/superpowers/specs/2026-07-25-droid-dual-target-tiers-design.md`

## Global Constraints

- Field name `model:` in goal frontmatter and `config.model` in index.yaml is UNCHANGED — only VALUES change to `inherit | heavy | medium | light`.
- Legacy aliases read forever: `opus`→`heavy`, `sonnet`→`medium`, `haiku`→`light`. Never written into new goals.
- No user-specific absolute paths in any skill (both harnesses).
- `$CLAUDE_PLUGIN_ROOT` stays primary (Droid aliases it to `$DROID_PLUGin_ROOT` — verified in Factory docs); every `~/.claude/plugins/...` glob fallback gains a `~/.factory/plugins/...` sibling.
- No dual-branch prose ("in Claude Code do X; in Droid do Y") outside the one mapping block per skill.
- Repo rules apply: full pytest green, plugin-validator before commit of manifest changes, push after every completed task, RED-baseline subagent dry-runs for changed skill mechanics.
- Versions at end: root flywheel `6.2.0 → 7.0.0`; `autoresearch 1.1.0 → 1.2.0`; `html-artifacts 1.0.1 → 1.0.2`; `human-writing 1.0.1 → 1.0.2`.

## Live-verified Droid facts (verified 2026-07-25 in this environment — cite, don't re-derive)

- `droid exec "<prompt>"` runs headless; flags: `--auto low|medium|high`, `-m <model-id>`, `-f <file>`, `--cwd <path>`, `-s <session-id>`, `--use-spec`, `--list-tools`.
- Plugin CLI: `droid plugin marketplace add <url-or-path>`, `droid plugin install <name>@<marketplace> [--scope user|project]`, `droid plugin update`, `droid plugin list`.
- Claude Code plugin layout (`.claude-plugin/plugin.json`, `agents/`) is auto-translated on install; translated agents land in `<cache>/droids/*.md` (observed: `~/.factory/plugins/cache/claude-plugins-official/plugin-dev/<hash>/droids/`).
- Plugin cache layout: `~/.factory/plugins/cache/<marketplace>/<plugin>/<commit-hash>/` — so the glob `~/.factory/plugins/cache/*/flywheel/*/skills/...` finds installed flywheel scripts.
- Droid tool names (from `droid exec --list-tools`): `Read, Grep, Glob, LS, Execute, Create, Edit, Task, ToolSearch, TodoWrite, FetchUrl, WebSearch, Skill` — there is NO `Bash` (Droid's shell tool is `Execute`), no `Write`, and `ApplyPatch` exists for some models.
- Droid built-in subagent types: `worker` (read-write general) and `explorer` (read-only, cannot modify files or run commands); Task tool takes `complexity: light|medium|heavy`.
- Droid settings dir: project `<repo>/.factory/settings.json`, user `~/.factory/settings.json`.

**Still to verify live (Task 1):** installing THIS marketplace into Droid; whether translated plugin droids are spawnable by name; how a `tools:` allowlist containing `Bash` translates.

---

### Task 1: Live-verify remaining Droid facts with this repo

**Files:**
- Create: `docs/superpowers/tmp/droid-verified-facts.md` (scratch notes; folded into skill text later, then deletable)

**Interfaces:**
- Produces: verified answers to (a) marketplace-add of a local Claude-layout repo, (b) plugin-droid spawn naming, (c) `tools: Bash` translation — consumed by Tasks 7, 8, 10.

- [ ] **Step 1: Register this repo as a local Droid marketplace and install flywheel**

```bash
droid plugin marketplace add /Users/serkan/flywheel
droid plugin install flywheel@pragmatic-growth --scope user
droid plugin list --scope user
```

Expected: install succeeds; `flywheel@pragmatic-growth` listed. If marketplace name resolves differently (folder name vs manifest `name`), record the actual ID.

- [ ] **Step 2: Inspect the translated cache**

```bash
find ~/.factory/plugins/cache/pragmatic-growth -maxdepth 3 2>/dev/null || find ~/.factory/plugins/cache -maxdepth 2 -newer ~/.factory/plugins/known_marketplaces.json
ls ~/.factory/plugins/cache/*/flywheel/*/droids/ 2>/dev/null
head -8 ~/.factory/plugins/cache/*/flywheel/*/droids/gate-reviewer.md
```

Expected: `agents/*.md` translated into `droids/`; record whether the `tools: Bash, Read, Grep, Glob, ToolSearch, SendMessage` line survives verbatim or is mapped (e.g. Bash→Execute). Record exact translated frontmatter.

- [ ] **Step 3: Verify plugin-droid spawnability and skill registration in a fresh Droid session**

```bash
droid exec --auto low "List the custom droids and skills available to you right now. Answer with two plain lists, nothing else."
```

Expected: the six flywheel skills appear; record the exact droid names shown (e.g. `gate-reviewer` bare vs `flywheel:gate-reviewer`). This naming is written into dispatch/define-goal mapping blocks in Tasks 7–8.

- [ ] **Step 4: Write findings to `docs/superpowers/tmp/droid-verified-facts.md`** — one bullet per fact with the observed evidence, plus the three answers from the "Still to verify" list.

- [ ] **Step 5: Uninstall the test install (leave the machine clean; reinstall happens in Task 13)**

```bash
droid plugin uninstall flywheel@pragmatic-growth --scope user
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/tmp/droid-verified-facts.md
git commit -m "docs(tmp): live-verified Droid plugin/translation facts for the dual-target port"
git push origin main
```

---

### Task 2: `goals_status.py` — tier alias normalization

**Files:**
- Modify: `skills/goals-status/scripts/goals_status.py` (frontmatter handling ~line 156, badge ~line 211)
- Test: `skills/goals-status/scripts/test_goals_status.py`

**Interfaces:**
- Produces: `TIER_ALIASES` dict and `normalize_tier(value) -> str` in `goals_status.py`; display always shows tier names. Tasks 3 uses the same 3-entry mapping (duplicated — scripts are standalone by design, no shared module).

- [ ] **Step 1: Write the failing tests** (append to `test_goals_status.py`, following its existing fixture style — it builds goal files with a `model:` line):

```python
def test_legacy_model_names_display_as_tiers(tmp_path):
    # goal stamped with the pre-v7 vocabulary must render as its tier
    repo = make_repo(tmp_path, goals=[
        ("001-legacy", "Legacy goal", "feature", "sonnet", "not_started", "Brief."),
    ])
    out = run_view(repo)
    assert "medium" in out
    assert "sonnet" not in out


def test_tier_names_display_verbatim(tmp_path):
    repo = make_repo(tmp_path, goals=[
        ("001-tiered", "Tiered goal", "feature", "heavy", "not_started", "Brief."),
    ])
    out = run_view(repo)
    assert "heavy" in out
```

(Adapt `make_repo`/`run_view` to the file's actual helper names — read the existing tests first and reuse their fixtures verbatim.)

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest -q skills/goals-status/scripts/test_goals_status.py -k "legacy_model or tier_names"`
Expected: FAIL — `"medium" in out` assertion error (legacy name passes through).

- [ ] **Step 3: Implement normalization** in `goals_status.py`, next to the frontmatter reader:

```python
TIER_ALIASES = {"opus": "heavy", "sonnet": "medium", "haiku": "light"}


def normalize_tier(value):
    """Map legacy model names to tier names; tier names and '' pass through."""
    v = (value or "").strip().lower()
    return TIER_ALIASES.get(v, v)
```

and change the meta extraction line to `"model": normalize_tier(meta.get("model")),`. Update the module docstring's model mention to name tiers + aliases.

- [ ] **Step 4: Run the file's full test suite**

Run: `python3 -m pytest -q skills/goals-status/scripts/test_goals_status.py`
Expected: PASS, including pre-existing tests (they stamp legacy names — if any assert the legacy name in OUTPUT, update those assertions to the tier name; stamping legacy in FIXTURES stays, that's the alias path under test).

- [ ] **Step 5: Commit**

```bash
git add skills/goals-status/scripts/
git commit -m "feat(goals-status): normalize legacy model names to heavy/medium/light tiers at read time"
git push origin main
```

---

### Task 3: `doctor_checks.py` — dual-harness probes

**Files:**
- Modify: `skills/factory-doctor/scripts/doctor_checks.py` (`_has_stop_failure_hook` ~line 221, `_external_scheduler_evidence` ~line 239, limit-resilience fix string ~line 203)
- Test: `skills/factory-doctor/scripts/test_doctor_checks.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: probes that recognize Droid evidence; consumed by factory-doctor SKILL.md text (Task 9).

- [ ] **Step 1: Write the failing tests** (append, reusing the file's existing monkeypatch/fixture style for these two functions):

```python
def test_scheduler_evidence_matches_droid_exec(monkeypatch):
    # a crontab firing fresh droid sessions is limit-proof evidence, same as claude -p
    _patch_scheduler_sources(monkeypatch, crontab='0 * * * * droid exec "/dispatch"')
    assert dc._external_scheduler_evidence()


def test_stop_failure_hook_found_in_factory_settings(tmp_path, monkeypatch):
    proj = tmp_path / ".factory"
    proj.mkdir()
    (proj / "settings.json").write_text('{"hooks": {"StopFailure": [{"matcher": "rate_limit"}]}}')
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    assert dc._has_stop_failure_hook(str(tmp_path))
```

(`_patch_scheduler_sources` = whatever mechanism the existing scheduler-evidence tests use; read them first and mirror exactly.)

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest -q skills/factory-doctor/scripts/test_doctor_checks.py -k "droid_exec or factory_settings"`
Expected: FAIL — `droid exec` not in patterns; `.factory` not in candidates.

- [ ] **Step 3: Implement**. In `_external_scheduler_evidence`:

```python
    patterns = ("claude -p", "claude --print", "droid exec", "/dispatch")
```

In `_has_stop_failure_hook`, extend candidates (comment updated to "project + user settings, both harnesses"):

```python
    candidates = [os.path.join(repo_root, d, f)
                  for d in (".claude", ".factory")
                  for f in ("settings.json", "settings.local.json")]
    candidates += [os.path.join(home, ".claude", "settings.json"),
                   os.path.join(home, ".factory", "settings.json")]
```

In the limit-resilience `fix` string, replace the scheduler clause with:

```python
            "fix": "schedule fresh sessions OUTSIDE the CLI (cron/launchd running "
                   "claude -p \"/dispatch\" or droid exec \"/dispatch\"), and/or add a "
                   "StopFailure hook (rate_limit matcher) that arms a resume at "
                   "rate_limits.*.resets_at — see loop-architect Step 5 limit-proofing"
```

- [ ] **Step 4: Run full file suite**

Run: `python3 -m pytest -q skills/factory-doctor/scripts/test_doctor_checks.py`
Expected: PASS.

- [ ] **Step 5: Smoke the probe end-to-end**

Run: `python3 skills/factory-doctor/scripts/doctor_checks.py --base main | python3 -m json.tool > /dev/null && echo OK`
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add skills/factory-doctor/scripts/
git commit -m "feat(factory-doctor): recognize droid exec schedulers and .factory settings in doctor probes"
git push origin main
```

---

### Task 4: `pg_validate.py` — `.factory/*` forbidden path

**Files:**
- Modify: `skills/dispatch/scripts/pg_validate.py:25`
- Test: `skills/dispatch/scripts/test_pg_validate.py`

- [ ] **Step 1: Write the failing test** (mirror the existing `.claude/settings.json` blast-radius test at the bottom of the file):

```python
def test_blast_radius_blocks_factory_settings():
    r = pgv.blast_radius([".factory/settings.json"], [])
    assert not r["pass"]
    assert "forbidden path" in r["evidence"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest -q skills/dispatch/scripts/test_pg_validate.py -k factory_settings`
Expected: FAIL — check passes because `.factory/*` is not forbidden.

- [ ] **Step 3: Implement**

```python
FORBIDDEN_PATHS = (".claude/*", ".factory/*", ".github/workflows/*", "*/deploy*.sh", "deploy*.sh")
```

- [ ] **Step 4: Run full file suite**

Run: `python3 -m pytest -q skills/dispatch/scripts/test_pg_validate.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/dispatch/scripts/
git commit -m "feat(dispatch): pg_validate forbids .factory/* changes same as .claude/*"
git push origin main
```

---

### Task 5: Root policy tests rewritten for the tier vocabulary (RED first)

**Files:**
- Modify: `test_skill_inventory.py`, `test_docs_model_policy.py`

These two tests already fail against `main` (pre-ideate inventory). They become the executable spec for Tasks 6–12: rewrite them NOW to assert the END state, watch them fail, and let Tasks 6–12 turn them green.

**Interfaces:**
- Produces: the canonical policy strings the skill edits must satisfy (exact phrases below) — Tasks 6–12 copy them verbatim.

- [ ] **Step 1: Fix the inventory test** — in `test_skill_inventory.py`, the expected list becomes:

```python
    assert skills == [
        "define-goal",
        "dispatch",
        "factory-doctor",
        "goals-status",
        "ideate",
        "loop-architect",
    ]
```

- [ ] **Step 2: Rewrite `test_docs_model_policy.py`** as the tier policy (replace the three tests entirely):

```python
def test_define_goal_stamps_tiers_not_model_names():
    text = read("skills/define-goal/SKILL.md").lower()
    assert "inherit | heavy | medium | light" in text
    assert "inherit | opus | sonnet | haiku" not in text


def test_active_docs_use_tier_vocabulary():
    # model names may appear ONLY inside the alias/mapping context, tested by
    # requiring the alias arrow next to every mention.
    active_docs = [
        "CLAUDE.md", "README.md", "public/index.html",
        "skills/define-goal/SKILL.md", "skills/dispatch/SKILL.md",
        "skills/ideate/SKILL.md", "skills/goals-status/SKILL.md",
        "skills/loop-architect/SKILL.md", "skills/factory-doctor/SKILL.md",
    ]
    for path in active_docs:
        text = read(path).lower()
        for name, tier in (("opus", "heavy"), ("sonnet", "medium"), ("haiku", "light")):
            for i, line in enumerate(text.splitlines(), 1):
                if name in line:
                    assert tier in line or "alias" in line or "maps" in line or "claude code" in line, \
                        f"{path}:{i}: bare model name '{name}' outside alias/mapping context"


def test_dispatch_carries_the_canonical_alias_table():
    text = read("skills/dispatch/SKILL.md").lower()
    assert "opus` → heavy" in text or "opus → heavy" in text
    assert "sonnet` → medium" in text or "sonnet → medium" in text
    assert "haiku` → light" in text or "haiku → light" in text


def test_scheduling_rail_names_both_harnesses():
    for path in ["skills/loop-architect/SKILL.md", "skills/factory-doctor/SKILL.md"]:
        text = read(path)
        assert 'claude -p "/dispatch"' in text, path
        assert 'droid exec "/dispatch"' in text, path
```

- [ ] **Step 3: Run to verify RED**

Run: `python3 -m pytest -q test_skill_inventory.py test_docs_model_policy.py`
Expected: inventory test PASSES (ideate exists); all four policy tests FAIL (docs still on old vocabulary).

- [ ] **Step 4: Commit the RED baseline**

```bash
git add test_skill_inventory.py test_docs_model_policy.py
git commit -m "test: root policy tests assert tier vocabulary + dual-harness rail (RED until port lands)"
git push origin main
```

---

### Task 6: define-goal SKILL.md — tier rubric + Droid run-now + mapping block

**Files:**
- Modify: `skills/define-goal/SKILL.md` (19 model-name hits)

**Interfaces:**
- Consumes: droid facts from Task 1 (spawn naming), policy phrases from Task 5.
- Produces: the rubric text pattern reused by CLAUDE.md/README (Task 11–12).

- [ ] **Step 1: Mechanical rename of the rubric and stamps.** Every rubric/stamp occurrence: `opus` → `heavy`, `sonnet` → `medium`, `haiku` → `light`, including headings/bullets like "**`opus` — the DEFAULT…**" → "**`heavy` — the DEFAULT…**", `model: opus` examples → `model: heavy`, and the enum `inherit | opus | sonnet | haiku` → `inherit | heavy | medium | light`. Rubric REASONING text is unchanged (heavy = default for features/bugs; medium = rote chores; light = truly rote one-file mechanical; turn-count-beats-token-price caution moves to the light bullet).

- [ ] **Step 2: Add the alias sentence** right after the enum in the goal-frontmatter template comment:

```
model: heavy    # execution tier for dispatch: inherit | heavy | medium | light —
                #   heavy is the default for features/bugs; medium only for rote
                #   chore-shaped work. Legacy values opus/sonnet/haiku are read
                #   as heavy/medium/light aliases — never write them.
```

- [ ] **Step 3: Rewrite the recon model rule harness-neutrally.** The "**Model (mandatory — gather on sonnet…)**" block becomes "**Model (mandatory — gather on the medium tier, judgment on the session model)**", with one mapping block replacing the Claude-only spawn instructions:

```
  Harness mapping — Claude Code: spawn `general-purpose` with `model: sonnet`
  (medium tier; never the built-in Explore type — its model cannot be pinned).
  Droid: spawn `explorer` (read-only by construction) with `complexity: medium`.
  The synthesis/judgment agent and the contract writing always stay on the
  session model; a per-run explicit user ask is the only gather override.
```

- [ ] **Step 4: Add the Droid run-now destination.** In the "Goal command facts" / run-now section, keep the `/goal` facts labeled as Claude Code facts, and add:

```
On Droid there is no `/goal` evaluator. The run-now destination is a
self-contained prompt block for a fresh headless session — the full contract
inline (outcome, every acceptance criterion with its exact command, stop
conditions), invoked as:

    droid exec -f goal-prompt.md --auto medium

The `/goal`-specific facts (4,000-char condition cap, transcript evaluation,
turn-cap announcements) do not apply to the Droid block; the contract itself
carries the verification.
```

- [ ] **Step 5: Update the contract-red-team spawn note** — spawn `flywheel:contract-red-team` when available (Claude Code) / the translated plugin droid by its Task-1-verified name (Droid); `general-purpose` (Claude Code) or `worker` with the inline rubric (Droid) as fallback; no model override, session model.

- [ ] **Step 6: Verify with the policy tests + grep**

Run: `python3 -m pytest -q test_docs_model_policy.py -k "define_goal or active_docs" ; grep -n "opus\|sonnet\|haiku" skills/define-goal/SKILL.md`
Expected: `test_define_goal_stamps_tiers_not_model_names` PASSES; every remaining grep hit sits on an alias/mapping line.

- [ ] **Step 7: Commit**

```bash
git add skills/define-goal/SKILL.md
git commit -m "feat(define-goal): heavy/medium/light tier rubric, Droid run-now block, harness mapping"
git push origin main
```

---

### Task 7: dispatch SKILL.md — canonical alias table + spawn mapping + paths

**Files:**
- Modify: `skills/dispatch/SKILL.md`

**Interfaces:**
- Consumes: Task 1 droid-spawn naming; Task 5 policy phrases.
- Produces: the canonical alias table other skills reference.

- [ ] **Step 1: Insert the canonical tier block** where implementer-model resolution is defined (goal `model:` > `config.model` > inherit — resolution ORDER unchanged):

```
**Execution tiers (canonical alias table).** `model:` values are
`inherit | heavy | medium | light`. Legacy values are read as aliases forever —
`opus` → heavy, `sonnet` → medium, `haiku` → light — and never written into new
goals or claims. Spawn-time mapping:
- Claude Code: heavy → `model: opus`, medium → `model: sonnet`, light →
  `model: haiku` on the implementer spawn; `inherit` omits the pin.
- Droid: pass `complexity: heavy|medium|light` on the Task spawn (`worker`
  type for implementers); `inherit` omits it.
The orchestrator and all recon/review agents always stay on the session model.
```

- [ ] **Step 2: Mechanical rename elsewhere:** `inherit | opus | sonnet | haiku` → tier enum; escalation-ladder trigger "implementer model is `sonnet` or `haiku`" → "implementer tier is `medium` or `light`"; "goals already resolved to `inherit`/`opus` skip this" → "`inherit`/`heavy`"; "features and bugs default to an `opus` stamp" → "a `heavy` stamp".

- [ ] **Step 3: Review-agent spawn mapping.** Where `flywheel:gate-reviewer`/`flywheel:fresh-check` spawns are described, add the Droid halves: plugin droid by its Task-1-verified name when available, else `worker` with the inline brief and a read-only instruction; Explore stays banned on Claude Code (unpinnable model), `explorer` is acceptable on Droid ONLY for gather roles, never for review lenses (reviews need Execute to run commands — `explorer` cannot).

- [ ] **Step 4: Script path fallback.** The `pg_validate.py` resolution sentence becomes: `$CLAUDE_PLUGIN_ROOT/skills/dispatch/scripts/pg_validate.py`, else newest match of `~/.claude/plugins/{cache,marketplaces}/*/flywheel/*/skills/dispatch/scripts/pg_validate.py`, else newest match of `~/.factory/plugins/cache/*/flywheel/*/skills/dispatch/scripts/pg_validate.py`.

- [ ] **Step 5: Verify**

Run: `python3 -m pytest -q test_docs_model_policy.py -k "alias_table or active_docs" ; grep -n "opus\|sonnet\|haiku" skills/dispatch/SKILL.md`
Expected: alias-table test PASSES; grep hits only on alias/mapping lines.

- [ ] **Step 6: Commit**

```bash
git add skills/dispatch/SKILL.md
git commit -m "feat(dispatch): canonical tier alias table, dual-harness spawn mapping, .factory path fallback"
git push origin main
```

---

### Task 8: ideate + goals-status SKILL.md — small mapping edits

**Files:**
- Modify: `skills/ideate/SKILL.md` (1 hit), `skills/goals-status/SKILL.md` (path fallback)

- [ ] **Step 1: ideate** — the orientation-subagent sentence ("`general-purpose` with `model: sonnet` … never the built-in Explore") becomes:

```
subagents on the medium tier — Claude Code: `general-purpose` with
`model: sonnet` (never the built-in Explore type; its model cannot be pinned);
Droid: `explorer` with `complexity: medium` — same routing as define-goal's
recon gather agents.
```

- [ ] **Step 2: goals-status** — extend the one-bash-block resolver with the Droid fallback:

```bash
GS="$CLAUDE_PLUGIN_ROOT/skills/goals-status/scripts/goals_status.py"
[ -f "$GS" ] || GS=$(find ~/.claude/plugins ~/.factory/plugins/cache -path '*/flywheel/*/skills/goals-status/scripts/goals_status.py' 2>/dev/null | sort -V | tail -1)
```

- [ ] **Step 3: Verify the resolver works on this machine** (Droid side; Claude side is the pre-existing path):

Run: `GS=$(find ~/.claude/plugins ~/.factory/plugins/cache -path '*/flywheel/*/skills/goals-status/scripts/goals_status.py' 2>/dev/null | sort -V | tail -1); echo "$GS"; [ -n "$GS" ] && echo RESOLVES`
Expected: `RESOLVES` (via the ~/.claude install now; Task 13 re-checks post-Droid-install).

- [ ] **Step 4: Commit**

```bash
git add skills/ideate/SKILL.md skills/goals-status/SKILL.md
git commit -m "feat(ideate,goals-status): medium-tier mapping and dual-harness script resolution"
git push origin main
```

---

### Task 9: loop-architect + factory-doctor SKILL.md — dual-harness scheduling rail

**Files:**
- Modify: `skills/loop-architect/SKILL.md`, `skills/factory-doctor/SKILL.md`

- [ ] **Step 1: loop-architect Step 5** — every `claude -p "/dispatch"` scheduler mention becomes `claude -p "/dispatch"` (Claude Code) or `droid exec "/dispatch"` (Droid), doctrine unchanged (OS scheduler, fresh sessions, outside the session). The statusline `rate_limits.*.resets_at` / `StopFailure` reset-clock details stay, labeled "(Claude Code facts; on Droid schedule blind by cadence — no verified reset-clock surface)". Droid's CronCreate/automations get ONE building-block sentence: session-bound loops die with the session, so they are never the unattended rail.

- [ ] **Step 2: factory-doctor** — script resolution gains the `~/.factory/plugins/cache/*/flywheel/*/skills/factory-doctor/scripts/doctor_checks.py` fallback; the settings-probe sentence "checks settings in `.claude/`" becomes "checks settings in `.claude/` and `.factory/` (project + user)"; the limit-resilience description names both scheduler commands (matching the Task 3 fix string).

- [ ] **Step 3: Verify**

Run: `python3 -m pytest -q test_docs_model_policy.py -k scheduling`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add skills/loop-architect/SKILL.md skills/factory-doctor/SKILL.md
git commit -m "feat(loop-architect,factory-doctor): dual-harness scheduling rail and settings probes"
git push origin main
```

---

### Task 10: Plugin agents — dual-harness tool allowlists

**Files:**
- Modify: `agents/contract-red-team.md`, `agents/fresh-check.md`, `agents/gate-reviewer.md` (frontmatter `tools:` lines only, plus one body sentence if translation findings require it)

**Interfaces:**
- Consumes: Task 1 finding on how `tools: Bash` translates.

- [ ] **Step 1: Decide the allowlist per the Task 1 finding.** Goal: read-only-by-tools on BOTH harnesses. If Droid maps `Bash`→`Execute` automatically, the line stays `tools: Bash, Read, Grep, Glob, ToolSearch, SendMessage` and only a comment is added. If it does NOT map (tool silently unavailable on Droid), the line becomes `tools: Bash, Execute, Read, Grep, Glob, ToolSearch, SendMessage` — each harness ignores the other's shell tool name; verify on Droid that listing an unknown tool (`Bash`) is ignored rather than an error, and on neither harness do `Edit/Write/Create/ApplyPatch/Task/Agent` appear.

- [ ] **Step 2: Apply the same edit to all three agent files.**

- [ ] **Step 3: Verify read-only on Droid** (after Task 13's reinstall — placeholder check now against the cached translation from Task 1):

Run: `grep -n "^tools:" ~/.factory/plugins/cache/*/flywheel/*/droids/*.md 2>/dev/null || echo "verify in Task 13"`
Expected: no write-capable tool in any translated allowlist.

- [ ] **Step 4: Commit**

```bash
git add agents/
git commit -m "feat(agents): dual-harness read-only tool allowlists for the three review roles"
git push origin main
```

---

### Task 11: Other plugins — autoresearch paths/cadence, descriptions

**Files:**
- Modify: `plugins/autoresearch/skills/autoresearch/SKILL.md`, `plugins/autoresearch/.claude-plugin/plugin.json`
- Modify: `plugins/html-artifacts/.claude-plugin/plugin.json`, `plugins/human-writing/.claude-plugin/plugin.json` (descriptions only)

- [ ] **Step 1: autoresearch SKILL.md** — helper resolution adds the Droid fallback (mirroring Task 8's pattern) after the existing two candidates:

```bash
  AR=$(ls -t ~/.claude/plugins/{cache,marketplaces}/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py \
       ~/.factory/plugins/cache/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py 2>/dev/null | head -1)
```

Unattended-cadence text: `/loop` (Claude Code) or an OS scheduler firing `droid exec` (Droid), one sentence.

- [ ] **Step 2: Manifest bumps.** `autoresearch` 1.1.0→1.2.0, description gains "Claude Code and Factory Droid". `html-artifacts` 1.0.1→1.0.2 and `human-writing` 1.0.1→1.0.2 only IF their descriptions change to mention both harnesses — do change them (one clause each), so both bump.

- [ ] **Step 3: Validate manifests** — run the `plugin-dev:plugin-validator` agent (Claude Code) or its checklist manually: required fields present, JSON parses, versions semver.

Run: `python3 -c "import json;[json.load(open(p)) for p in ['plugins/autoresearch/.claude-plugin/plugin.json','plugins/html-artifacts/.claude-plugin/plugin.json','plugins/human-writing/.claude-plugin/plugin.json','.claude-plugin/plugin.json','.claude-plugin/marketplace.json']];print('OK')"`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add plugins/
git commit -m "feat(plugins): dual-harness path fallbacks and descriptions for autoresearch, html-artifacts, human-writing"
git push origin main
```

---

### Task 12: CLAUDE.md, AGENTS.md, README, site, root manifest — v7.0.0

**Files:**
- Modify: `CLAUDE.md`, `AGENTS.md`, `README.md`, `public/index.html`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`

- [ ] **Step 1: CLAUDE.md** — Project Overview and per-skill bullets: tier vocabulary throughout (rubric bullets say "heavy is the DEFAULT for every feature/bug goal"); the `config:` block doc: `model` takes `inherit|heavy|medium|light`, legacy names as aliases; recon rule: gather on the medium tier with the harness mapping; skills-first rule: note plugin agents are read-only on both harnesses; marketplace-refresh rule adds `droid plugin marketplace update pragmatic-growth`; portability rule: no user-specific absolute paths for either harness; a one-paragraph history note recording that v5.0.0 removed Droid and v7.0.0 restored it with the tier architecture.

- [ ] **Step 2: AGENTS.md** — update the Architecture section to the dual-target model (it currently says "This repo *is* a Claude Code plugin marketplace"); the root-tests note is deleted (they pass after Task 5–12); keep commands harness-neutral. CLAUDE.md ↔ AGENTS.md must not contradict.

- [ ] **Step 3: README.md** — install section gets both harnesses:

````markdown
### Claude Code
```
/plugin marketplace add pragmaticgrowth/flywheel
/plugin install flywheel@pragmatic-growth
```
### Factory Droid
```
droid plugin marketplace add https://github.com/pragmaticgrowth/flywheel
droid plugin install flywheel@pragmatic-growth
```
````

Config example + rubric mentions → tier names; version badge → `version-7.0.0`.

- [ ] **Step 4: public/index.html** — `<title>`, meta, `.ver-pill` → 7.0.0; install section mirrors the README's two blocks; the one model-name mention → tier phrasing; add "Claude Code + Factory Droid" to the hero copy.

- [ ] **Step 5: Root manifest + marketplace** — `.claude-plugin/plugin.json` version `7.0.0`, description mentions both harnesses; marketplace.json descriptions likewise.

- [ ] **Step 6: CHANGELOG.md** — add `## [7.0.0] — 2026-07-25` block: dual-target restoration (reverses v5.0.0 with the tier architecture), tier vocabulary + aliases, dual-harness rail/probes/paths, agent allowlists, per-plugin bumps; commit link added after the version-bump commit exists (amend or follow-up, repo pattern).

- [ ] **Step 7: Full suite + policy green**

Run: `python3 -m pytest -q`
Expected: ALL tests pass, including the Task 5 policy tests (this is the moment RED goes GREEN).

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md AGENTS.md README.md public/index.html .claude-plugin/ CHANGELOG.md
git commit -m "feat: v7.0.0 — dual-target Claude Code + Factory Droid, heavy/medium/light tier vocabulary"
git push origin main
```

---

### Task 13: Live Droid end-to-end + subagent dry-runs (RED baselines)

**Files:**
- Create: `docs/superpowers/tmp/droid-e2e-notes.md` (evidence notes)

- [ ] **Step 1: Reinstall into Droid from the pushed repo and re-run the Task 1 checks**

```bash
droid plugin marketplace add https://github.com/pragmaticgrowth/flywheel
droid plugin install flywheel@pragmatic-growth --scope user
droid plugin list
```

Expected: v7.0.0 content installs; skills + droids registered (re-run the Task 1 Step 3 listing probe).

- [ ] **Step 2: Scratch-queue smoke in Droid.** Create a throwaway repo with a minimal `docs/goals/index.yaml` + one goal file stamped `model: sonnet` (legacy alias on purpose), then:

```bash
cd $(mktemp -d) && git init -q . && mkdir -p docs/goals
# write index.yaml (config: base main, model: inherit, verify: true) + 001-smoke.md with model: sonnet
droid exec --auto low --cwd . "Use the flywheel goals-status skill to show this repo's goal queue. Output the view verbatim."
```

Expected: view renders; the goal shows tier `medium` (alias normalization live).

- [ ] **Step 3: factory-doctor smoke in Droid**

```bash
droid exec --auto low --cwd <scratch-repo> "Run the flywheel factory-doctor skill preflight on this repo and print the findings."
```

Expected: runs, resolves `doctor_checks.py` via the Droid cache fallback, emits findings (BLOCKER for missing PyYAML config acceptable — record what fires).

- [ ] **Step 4: One trivial /dispatch cycle in Droid** on the scratch repo (goal: "append one line to NOTES.md", acceptance: `grep -q <line> NOTES.md`). Expected: claim → implement → gate (pg_validate resolves) → squash → `completed` in index.yaml.

- [ ] **Step 5: Subagent dry-runs with RED baselines** (repo rule) for the three changed mechanics. For each, run the scenario against `git show v6.2.0:<file>` (RED: old text decides differently or is silent) and against the new text (GREEN):
  1. **Tier stamping:** "A `type: feature` goal with exact-command criteria — what does define-goal stamp?" Old: `opus`. New: `heavy`. Also: "frontmatter says `model: sonnet` — what tier does dispatch resolve and how does it spawn on Droid?" Old: silent on Droid. New: medium → `complexity: medium`.
  2. **Escalation ladder:** "A medium-stamped goal hits a capability-shaped blocker on Droid — which rung fires?" Old: names sonnet/haiku only. New: tier language, one stronger-tier re-spawn.
  3. **Scheduling rail:** "Unattended drain on a Droid-only machine — what does loop-architect Step 5 prescribe?" Old: `claude -p` only. New: OS scheduler + `droid exec "/dispatch"`.
  Cite-the-deciding-section required in each answer; close any flagged ambiguity by editing the skill text and re-running.

- [ ] **Step 6: Record evidence** in `docs/superpowers/tmp/droid-e2e-notes.md`; fix anything that failed (loop back to the owning task's file).

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/tmp/droid-e2e-notes.md
git commit -m "test: live Droid E2E evidence + RED-baseline dry-runs for the v7.0.0 port"
git push origin main
```

---

### Task 14: Ship v7.0.0

- [ ] **Step 1: Final full-suite + clean-tree check**

Run: `python3 -m pytest -q && git status --porcelain`
Expected: all pass; empty status.

- [ ] **Step 2: Tag + GitHub Release** (notes = the CHANGELOG 7.0.0 section, per repo rule)

```bash
git tag -a v7.0.0 -m "v7.0.0 — dual-target Claude Code + Factory Droid, tier vocabulary"
git push --tags
awk '/^## \[7.0.0\]/{f=1;next} /^## \[/{f=0} f' CHANGELOG.md > /tmp/notes-7.0.0.md
gh release create v7.0.0 --title "v7.0.0 — Dual-target: Claude Code + Factory Droid" --notes-file /tmp/notes-7.0.0.md --verify-tag --latest
```

- [ ] **Step 3: Deploy the site**

Run: `wrangler deploy` (repo root, `CLOUDFLARE_API_TOKEN` set)
Expected: deploy succeeds to flywheel.pragmaticgrowth.com.

- [ ] **Step 4: Refresh installed plugins on this machine**

```bash
droid plugin marketplace update pragmatic-growth && droid plugin update flywheel@pragmatic-growth
```

(Claude Code side: `/plugin marketplace update pragmatic-growth` next time that CLI is open.)

- [ ] **Step 5: Final push-state check**

Run: `git status --porcelain && git log origin/main..main --oneline`
Expected: both empty.
