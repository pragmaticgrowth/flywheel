# Autoresearch Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Factory's `autoresearch` skill as a third standalone plugin in the `pragmatic-growth` marketplace, translated to be Claude-Code-first while staying CLI-aware (still works in Droid).

**Architecture:** Mirror the `html-artifacts` standalone-plugin layout under `plugins/autoresearch/`. The Python helper is copied verbatim (stdlib-only, CLI-agnostic); the SKILL.md is ported with surgical translations (script-path resolution, mission→Claude-Code primitives, default-branch detection, session-neutral context wording, attribution). Then register the plugin across all marketplace surfaces (marketplace.json, README, site, CLAUDE.md) and release it under its own namespaced tag.

**Tech Stack:** Markdown skills, JSON manifests, Python 3 stdlib, git, `gh` CLI, wrangler (Cloudflare).

## Global Constraints

- **Skills-only.** No MCP servers, commands, agents, or hooks.
- **Portability.** No user-specific absolute paths (`/Users/...`, `~/.claude/...`, `~/.factory/...`) inside skill *content*. Path-resolution globs that reference `~/.claude/plugins` / `~/.factory/plugins` are the sanctioned exception (they mirror the existing flywheel scripts).
- **CLI-aware, Claude-Code-first.** Detect runtime (Droid if `CronCreate`/`CreateAutomation` available or `$DROID_PLUGIN_ROOT` set; else Claude Code). Primary wording is Claude Code; Droid is the documented alternative.
- **New plugin version:** `autoresearch` `1.0.0`. Do **not** bump `flywheel`'s `plugin.json` — its skills are unchanged. marketplace.json / README / site / CHANGELOG / CLAUDE.md edits are content-only and need no flywheel bump.
- **Tag namespacing:** flywheel already owns `v1.0.0`. Autoresearch's tag MUST be namespaced: `autoresearch-v1.0.0`.
- **Attribution:** credit Factory (MIT origin), the way `define-goal` was adapted from OpenAI's skill.
- **Skill frontmatter:** `name` + `description` only (no `version:` field — matches the flywheel skills).
- **docs/ never committed.** This plan and its spec live under `docs/` — never `git add` them. Stage specific files only; never `git add -A`/`git add .` for pushed commits.
- **Push is pre-authorized** to `origin main` after committing.

---

### Task 1: Plugin scaffold — manifest + helper

**Files:**
- Create: `plugins/autoresearch/.claude-plugin/plugin.json`
- Create: `plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py`

**Interfaces:**
- Produces: the helper CLI `python3 autoresearch_helper.py {init,log,evaluate,summary,status}` (signatures exactly as in the Factory source — unchanged). Task 2 references it via `$AR`.

- [ ] **Step 1: Create the manifest** at `plugins/autoresearch/.claude-plugin/plugin.json`:

```json
{
  "name": "autoresearch",
  "version": "1.0.0",
  "description": "Autonomous optimization loop for Claude Code and Droid — try an idea, measure it, keep what works, revert what doesn't, repeat. MAD-based confidence scoring, git branch isolation, and file-based experiment logging any fresh session can resume. Adapted from Factory's autoresearch pattern (MIT).",
  "author": {
    "name": "pragmaticgrowth"
  },
  "repository": "https://github.com/pragmaticgrowth/flywheel",
  "homepage": "https://github.com/pragmaticgrowth/flywheel/tree/main/plugins/autoresearch",
  "license": "MIT",
  "keywords": ["skills", "autoresearch", "optimization", "experiments", "benchmark", "autonomous", "loop"]
}
```

- [ ] **Step 2: Copy the helper verbatim** to `plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py`. Source of truth is the full file already fetched in this session (Factory `plugins/autoresearch/skills/autoresearch/autoresearch_helper.py`) — NO logic changes. To pull it deterministically:

```bash
mkdir -p plugins/autoresearch/skills/autoresearch/scripts
gh api "repos/Factory-AI/factory-plugins/contents/plugins/autoresearch/skills/autoresearch/autoresearch_helper.py" --jq '.content' | base64 -d > plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py
```

- [ ] **Step 3: Syntax-check the helper.**

Run: `python3 -c "import ast; ast.parse(open('plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Smoke-test the full helper CLI** against a temp JSONL (exercises init→log→evaluate→summary→status and the MAD confidence path):

```bash
AR=plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py
TMP=$(mktemp -d)
python3 "$AR" init --jsonl "$TMP/a.jsonl" --name demo --metric-name lat --metric-unit ms --direction lower
python3 "$AR" log --jsonl "$TMP/a.jsonl" --commit abc1234 --metric 10 --status keep --description baseline --asi '{"hypothesis":"baseline"}'
python3 "$AR" log --jsonl "$TMP/a.jsonl" --commit def5678 --metric 9  --status keep --description try1 --asi '{"hypothesis":"try1"}'
python3 "$AR" log --jsonl "$TMP/a.jsonl" --commit 0000000 --metric 12 --status discard --description try2 --asi '{"hypothesis":"try2","rollback_reason":"slower"}'
python3 "$AR" evaluate --jsonl "$TMP/a.jsonl" --metric 8 --direction lower
python3 "$AR" summary --jsonl "$TMP/a.jsonl"
python3 "$AR" status --jsonl "$TMP/a.jsonl"
rm -rf "$TMP"
```

Expected: `init` prints "Initialized: demo …"; each `log` prints "Logged #N …"; `evaluate` prints `DECISION: keep` (8 < best-kept 9); `summary` lists 3 experiments (2 kept, 1 discarded); `status` prints JSON with `"bestKept": 9` and a numeric or null `confidence`. No tracebacks.

- [ ] **Step 5: Commit** (helper + manifest only; NOT docs/):

```bash
git add plugins/autoresearch/.claude-plugin/plugin.json plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py
git commit -m "feat(autoresearch): scaffold plugin manifest + experiment helper"
```

---

### Task 2: Translated SKILL.md

**Files:**
- Create: `plugins/autoresearch/skills/autoresearch/SKILL.md`

**Interfaces:**
- Consumes: `$AR` helper CLI from Task 1.
- Produces: the user-facing `autoresearch` skill. No downstream code depends on its internals.

The SKILL.md is the Factory source (fetched this session) **ported section-for-section in the same order**, with the surgical edits below. Sections kept verbatim from source: *Overview* (para 1 only), *Setup* (Steps 1–4, including the `autoresearch.md`/`autoresearch.sh`/`autoresearch.checks.sh` templates and examples), *The Experiment Loop* (steps 1–8), *State Files Reference* + *JSONL Schema* + *ASI*, *Confidence Scoring*, *Loop Rules Summary*, *Finalization* (Steps 1–5). The edits:

- [ ] **Step 1: Frontmatter** — `name` + `description` only (drop the source's `version:` field):

```markdown
---
name: autoresearch
description: |
  Autonomous experiment loop for optimization research. Use when the user wants to:
  - Optimize a metric through systematic experimentation (ML training loss, test speed, bundle size, build time, etc.)
  - Run an automated research loop: try an idea, measure it, keep improvements, revert regressions, repeat
  - Set up autoresearch for any codebase with a measurable optimization target
  Implements the autoresearch pattern with MAD-based confidence scoring, git branch
  isolation, and structured experiment logging. Works in Claude Code and Droid.
---
```

- [ ] **Step 2: Title + CLI-detection + attribution block** (immediately after frontmatter — mirrors `define-goal`'s house pattern):

```markdown
# Autoresearch

Autonomous experiment loop: try ideas, keep what works, discard what doesn't, never stop.

**CLI detection**: this skill works in both Claude Code and Droid (Factory CLI). Detect
your runtime: if Droid-specific tools (CronCreate, CreateAutomation) are available or
`$DROID_PLUGIN_ROOT` is set, you are in Droid. Otherwise Claude Code. The loop procedure
is identical in both; only the autonomous-cadence primitive and the helper path differ.

*Adapted from Factory's `autoresearch` plugin (MIT), translated to be Claude-Code-first
and CLI-aware for the Pragmatic Growth marketplace.*
```

- [ ] **Step 3: Resolve-the-helper-path section** (new — insert as the first subsection of *Overview*, before Setup; models factory-doctor's chain, scoped to this plugin):

````markdown
## Resolve the helper path

The experiment helper ships with this plugin. Set `$AR` to its path once, trying in
order and stopping at the first that exists:

1. `$CLAUDE_PLUGIN_ROOT/skills/autoresearch/scripts/autoresearch_helper.py`
2. `$DROID_PLUGIN_ROOT/skills/autoresearch/scripts/autoresearch_helper.py` (Droid)
3. newest match of `~/.claude/plugins/{cache,marketplaces}/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py`
4. newest match of `~/.factory/plugins/{cache,marketplaces}/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py`

```bash
AR=""
for c in \
  "$CLAUDE_PLUGIN_ROOT/skills/autoresearch/scripts/autoresearch_helper.py" \
  "$DROID_PLUGIN_ROOT/skills/autoresearch/scripts/autoresearch_helper.py"; do
  [ -n "$c" ] && [ -f "$c" ] && AR="$c" && break
done
if [ -z "$AR" ]; then
  AR=$(ls -t ~/.claude/plugins/{cache,marketplaces}/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py \
              ~/.factory/plugins/{cache,marketplaces}/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py \
       2>/dev/null | head -1)
fi
```

Every helper invocation below is `python3 "$AR" …`. (State files — `autoresearch.md`,
`autoresearch.sh`, `autoresearch.jsonl` — live in the **target repo** and are committed
there; only this helper lives in the plugin.)
````

Then throughout the ported body, replace every source occurrence of `python3 autoresearch_helper.py` with `python3 "$AR"`.

- [ ] **Step 4: Replace the source's Overview mission paragraphs** (the two paragraphs beginning "If the user is asking you to do this and you are not currently in mission mode…" and "If you are already in mission mode…") with a CLI-aware autonomous-run block:

```markdown
**Running autonomously.** This loop runs *in-session* and resumes across sessions from
its state files — a fresh session with no memory reads them and continues exactly where
the last one stopped. For unattended cadence you don't have to babysit:

- **Claude Code:** let the loop run in one session until the termination condition or
  context limit; for periodic re-entry, wrap the resume in `/loop` —
  e.g. `/loop 15m "resume autoresearch"` — so each fire reads the state files and runs
  more experiments.
- **Droid:** schedule a same-session `CronCreate` on the same interval. Optionally run
  inside a mission (`/enter-mission`) for milestone tracking and multi-session
  validation — helpful, not required; the loop procedure is unchanged either way.

Pick the primitive matching your runtime once at setup; everything below is identical in
both.
```

- [ ] **Step 5: Default-branch detection in Finalization.** In *Finalization* Step 4 (and the Step 1 `git log` range and Step 5 "merges cleanly with main"), replace the hardcoded `main` with a detected base. Use this exact snippet in Step 4 and reuse `$base`/`$merge_base` in the surrounding steps:

```bash
base=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
base=${base:-main}
merge_base=$(git merge-base HEAD "$base")
git checkout -b autoresearch/finalize/<group-name> "$merge_base"
git checkout autoresearch/<session-branch> -- <file1> <file2> ...
git commit -m "<group description>

Autoresearch results:
- Metric: <name> improved from <baseline> to <best> (<delta>%)
- Confidence: <score>x noise floor
- Experiments: <count> total, <kept> kept"
```

In *Finalization* Step 1, the review command becomes `git log --oneline --stat "$merge_base"..HEAD` (compute `$merge_base` as above). In Step 5, "verify it merges cleanly with main" → "verify it merges cleanly with `$base`".

- [ ] **Step 6: Session-neutral context wording.** In *Context Management*, replace "Droid sessions have finite context." with "Every session has finite context (Claude Code and Droid alike)." Keep the rest of the section (file-based resume protocol) verbatim, with the `status` call as `python3 "$AR" status --jsonl autoresearch.jsonl`.

- [ ] **Step 7: Generalize "Mission Worker Mode"** (last section) to a runtime-neutral worker mode:

```markdown
## Unattended / worker mode

When the goal, termination condition, files in scope, and constraints are supplied up
front — a Droid mission feature description, a `/loop` prompt, or a cron spec — read them
carefully, follow the same loop procedure above, and respect the termination condition.
When the condition is met, run finalization and report results in the handoff. In Droid
mission-worker mode specifically, proceed with the best grouping in Finalization without
waiting for user confirmation.
```

- [ ] **Step 8: Verify no stale references remain.**

Run:
```bash
grep -nE "python3 autoresearch_helper\.py|Droid sessions|enter-mission|mission worker mode|merge-base HEAD main" plugins/autoresearch/skills/autoresearch/SKILL.md
```
Expected: no matches EXCEPT the sanctioned optional `/enter-mission` mention inside the Step 4 autonomous block and the Droid note. (i.e. `python3 autoresearch_helper.py`, `Droid sessions`, `mission worker mode`, and `merge-base HEAD main` must return nothing.)

- [ ] **Step 9: Commit:**

```bash
git add plugins/autoresearch/skills/autoresearch/SKILL.md
git commit -m "feat(autoresearch): Claude-Code-first, CLI-aware SKILL"
```

---

### Task 3: Register the plugin across marketplace surfaces

**Files:**
- Modify: `.claude-plugin/marketplace.json` (add third `plugins[]` entry)
- Modify: `README.md` (plugin table ~line 51-52; install region ~line 287-303; the "two plugins" prose ~line 31)
- Modify: `public/index.html` (plugin list + `<title>`/meta if they enumerate plugins)
- Modify: `CLAUDE.md` (Project Overview, Structure tree, Rules validation-install line, "two plugins"→"three")

**Interfaces:**
- Consumes: the plugin from Tasks 1–2.
- Produces: a marketplace that lists and installs `autoresearch@pragmatic-growth`.

- [ ] **Step 1: Add the marketplace entry.** In `.claude-plugin/marketplace.json`, append to `plugins[]` after the `html-artifacts` object:

```json
    {
      "name": "autoresearch",
      "description": "Autonomous optimization loop — try an idea, measure it, keep what works, revert what doesn't, repeat. MAD-based confidence scoring, git branch isolation, and file-based experiment logs any fresh session can resume.",
      "source": "./plugins/autoresearch",
      "homepage": "https://github.com/pragmaticgrowth/flywheel/tree/main/plugins/autoresearch",
      "author": {
        "name": "pragmaticgrowth"
      },
      "category": "productivity"
    }
```

Also update the top-level marketplace `description` to mention three plugins / add autoresearch.

- [ ] **Step 2: Validate the marketplace JSON parses.**

Run: `python3 -c "import json; d=json.load(open('.claude-plugin/marketplace.json')); print([p['name'] for p in d['plugins']])"`
Expected: `['flywheel', 'html-artifacts', 'autoresearch']`

- [ ] **Step 3: README — plugin table + install + prose.** Read `README.md` first. Then:
  - Add a table row after the `html-artifacts` row (~line 52):
    `| **autoresearch** | One `autoresearch` skill (+ Python helper) for an autonomous try/measure/keep/revert optimization loop. | `/plugin install autoresearch@pragmatic-growth` |`
  - In the Claude Code install block (~line 294), add: `/plugin install autoresearch@pragmatic-growth`
  - In the Droid install block (~line 303), add: `droid plugin install autoresearch@flywheel`
  - Update "exposes two plugins" / "two plugins" prose (~line 31, 34) to three, naming autoresearch as the autonomous-optimization plugin.
  - Add a short subsection near the html-artifacts one (~line 98) describing autoresearch (2–4 sentences: what it optimizes, the loop, the finalize-to-branches output).

- [ ] **Step 4: public/index.html.** Read it, find where the plugins are enumerated (the html-artifacts card/section and any plugin count in copy or `<title>`/meta description). Add an autoresearch entry mirroring html-artifacts' treatment, and bump any "two plugins" copy to three. Do NOT touch the `.ver-pill` (that tracks flywheel's version, which is unchanged).

- [ ] **Step 5: CLAUDE.md.** Read the relevant regions, then:
  - Project Overview: change "two plugins … `flywheel` v4.x.x and `html-artifacts` v1.0.0" to include `autoresearch` v1.0.0; add a one-paragraph bullet describing the autoresearch plugin under the "Separate marketplace plugin:" area (rename to plugins, plural, if needed).
  - Structure tree: add `plugins/autoresearch/.claude-plugin/plugin.json`, `plugins/autoresearch/skills/autoresearch/SKILL.md`, and `.../scripts/autoresearch_helper.py`.
  - Rules → Validation: add `droid plugin install autoresearch@flywheel` to the manual-validation install list.
  - Verify `AGENTS.md` is still the symlink to `CLAUDE.md` (`ls -l AGENTS.md`) — no separate edit needed if the symlink is intact.

- [ ] **Step 6: Commit** (explicit paths only):

```bash
git add .claude-plugin/marketplace.json README.md public/index.html CLAUDE.md
git commit -m "docs(autoresearch): register plugin in marketplace, README, site, CLAUDE.md"
```

---

### Task 4: CHANGELOG entry + release notes

**Files:**
- Modify: `CHANGELOG.md`
- Create: `docs/superpowers/tmp/autoresearch-1.0.0-notes.md` (untracked scratch for the GitHub release body)

**Interfaces:**
- Consumes: nothing.
- Produces: a changelog block + a release-notes file consumed by Task 6's `gh release create`.

- [ ] **Step 1: Inspect how a standalone plugin's debut was recorded.**

Run: `grep -n "html-artifacts" CHANGELOG.md | head`
Use the html-artifacts precedent to decide whether autoresearch's debut is folded under a dated block or gets its own heading. Match that format.

- [ ] **Step 2: Add the changelog block** near the top (under the intro, above/at the latest dated entry as the format dictates). Content:

```markdown
### Added — `autoresearch` plugin 1.0.0 (2026-07-01)

New third plugin in the `pragmatic-growth` marketplace: **autoresearch**, an
autonomous optimization loop (try an idea → measure → keep improvements → revert
regressions → repeat) with MAD-based confidence scoring, git branch isolation, and
file-based experiment logs any fresh session can resume. Adapted from Factory's
`autoresearch` plugin (MIT) and translated to be Claude-Code-first and CLI-aware:
`.claude-plugin` manifest; helper resolved via `$CLAUDE_PLUGIN_ROOT`/`$DROID_PLUGIN_ROOT`;
mission-mode spine replaced with `/loop` (Claude Code) / same-session `CronCreate`
(Droid); default-branch detection instead of hardcoded `main`; session-neutral context
wording. Install: `/plugin install autoresearch@pragmatic-growth`.
```

(If Step 1 shows the file uses `## [X.Y.Z]` headings for standalone plugins, use `## [autoresearch 1.0.0] — 2026-07-01` instead, matching the html-artifacts precedent.)

- [ ] **Step 3: Write the release-notes file** `docs/superpowers/tmp/autoresearch-1.0.0-notes.md` = the changelog block body (without the heading), for `gh release create --notes-file`.

- [ ] **Step 4: Commit** (CHANGELOG only — the notes file is under docs/, never committed):

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add autoresearch 1.0.0"
```

---

### Task 5: Validation gate

**Files:** none (verification only).

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: a go/no-go signal. Fix any failure inline before Task 6.

- [ ] **Step 1: Run the plugin-validator agent** (Claude Code, per repo rules). Dispatch the `plugin-dev:plugin-validator` agent against the repo; it must pass for the new `plugins/autoresearch` structure and manifests. Fix anything it flags.

- [ ] **Step 2: Skill dry-run subagent** (per repo "Skill edits are tested" rule). Dispatch a general-purpose subagent with this scenario and require it to cite the SKILL section that decides each answer:

  > Scenario: "Optimize `pnpm build` bundle size (lower is better) in a repo whose default branch is `develop`, run until 20 experiments." Walk the skill: (a) where does the helper live and how do you call it? (b) what's the exact baseline-logging command? (c) an experiment crashes — exact log + revert sequence? (d) at finalization, what base branch is used and how is it detected? (e) you're in Claude Code and want it to run unattended overnight — what do you set up? For each, quote the section that decides it.

  Expected citations: Resolve-the-helper-path (`$AR`); Setup Step 4 baseline; Loop step 5 discard/crash branch; Finalization Step 4 default-branch detection (`develop`, not `main`); the "Running autonomously" `/loop` bullet. Close every ambiguity the subagent surfaces.

- [ ] **Step 3: Confirm the symlink and clean tree.**

Run: `ls -l AGENTS.md && git status --porcelain`
Expected: `AGENTS.md -> CLAUDE.md`; `git status` shows only untracked `docs/` (and any `__pycache__`) — no staged docs/, no stray tracked scratch.

---

### Task 6: Ship

**Files:** none (git/release/deploy operations).

**Interfaces:**
- Consumes: the validated, committed work from Tasks 1–5.
- Produces: pushed commits, a namespaced tag, a GitHub Release, refreshed marketplace, redeployed site.

- [ ] **Step 1: Ensure docs/ is absent from the push range.** The pre-push hook aborts if `docs/` is in any pushed commit. Confirm nothing under `docs/` was ever `git add`ed:

Run: `git log origin/main..HEAD --name-only --pretty=format: | sort -u | grep '^docs/' || echo "clean"`
Expected: `clean`

- [ ] **Step 2: Push** (pre-authorized):

```bash
git push origin main
```

- [ ] **Step 3: Tag the plugin debut** on the SKILL/scaffold commit's tip (namespaced to avoid the existing `v1.0.0`):

```bash
git tag -a autoresearch-v1.0.0 -m "autoresearch plugin 1.0.0 — autonomous optimization loop (Claude-Code-first, CLI-aware)"
git push --tags
```

- [ ] **Step 4: Create the GitHub Release** from the tag, notes from Task 4's file (historical/side release — NOT flywheel's latest, so `--latest=false`):

```bash
gh release create autoresearch-v1.0.0 \
  --title "autoresearch-v1.0.0 — autonomous optimization loop" \
  --notes-file docs/superpowers/tmp/autoresearch-1.0.0-notes.md \
  --verify-tag --latest=false
```

- [ ] **Step 5: Redeploy the site** (only if `CLOUDFLARE_API_TOKEN` is set; else report that it needs a manual `wrangler deploy`):

```bash
wrangler deploy
```

- [ ] **Step 6: Report the refresh commands** to the user (cannot run them here — they refresh the installed plugin from GitHub):
  - Claude Code: `/plugin marketplace update pragmatic-growth` then `/plugin install autoresearch@pragmatic-growth`
  - Droid: `droid plugin marketplace update flywheel` then `droid plugin install autoresearch@flywheel`

---

## Self-Review

**Spec coverage:**
- Package layout → Task 1 (manifest, helper) + Task 2 (SKILL). ✓
- Manifest fields → Task 1 Step 1. ✓
- Script-path house convention → Task 2 Step 3. ✓
- Mission→Claude-Code translation → Task 2 Steps 4, 7. ✓
- Default-branch detection → Task 2 Step 5. ✓
- Context wording → Task 2 Step 6. ✓
- Attribution → Task 2 Step 2 + manifest description (Task 1). ✓
- Helper verbatim → Task 1 Step 2. ✓
- marketplace.json / README / site / CHANGELOG → Tasks 3, 4. ✓ (CLAUDE.md added — Task 3 Step 5, required since the marketplace goes two→three plugins.)
- Validation + subagent dry-run → Task 5. ✓
- Push / tag / release / deploy / refresh → Task 6. ✓

**Placeholder scan:** `<goal>`, `<group-name>`, `<file1>` etc. inside the SKILL template snippets are intentional skill-template placeholders (they're the skill's own authored content, copied from the Factory source), not plan gaps. All plan-level commands are concrete.

**Type consistency:** helper subcommands (`init/log/evaluate/summary/status`) and `$AR` naming are consistent across Tasks 1, 2, 5. Tag name `autoresearch-v1.0.0` consistent across Tasks 4, 6. Plugin name `autoresearch` and install ref `autoresearch@pragmatic-growth` (Claude) / `autoresearch@flywheel` (Droid) consistent across Tasks 3, 6.
