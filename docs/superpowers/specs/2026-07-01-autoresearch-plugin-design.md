# Autoresearch plugin — design spec

**Date:** 2026-07-01
**Status:** Approved (brainstorming), pending implementation plan
**Author:** Serkan Haslak (Pragmatic Growth)

## Goal

Bring Factory's `autoresearch` plugin
(`Factory-AI/factory-plugins/plugins/autoresearch`) into the
`pragmatic-growth` marketplace as a **third standalone plugin**, translated to be
**Claude-Code-first while staying CLI-aware** (still works in Droid via the
compatibility layer), matching the conventions of the existing `flywheel` and
`html-artifacts` plugins.

## What autoresearch does (unchanged behavior)

An autonomous optimization loop. Given a measurable metric, a benchmark command,
files-in-scope, constraints, and a termination condition, it:

1. Creates an `autoresearch/<goal>-<date>` git branch + state files
   (`autoresearch.md` living doc, `autoresearch.sh` benchmark emitting
   `METRIC name=value`, `autoresearch.jsonl` append-only log, optional
   `.checks.sh`, optional `.ideas.md`).
2. Runs a baseline, then loops forever: pick hypothesis → edit → run benchmark →
   evaluate with MAD-based confidence scoring → keep (commit) or
   discard/crash/checks_failed (revert, preserving state files) → journal
   learnings (ASI) → repeat.
3. On termination, finalizes kept experiments into clean, independently-mergeable
   branches for review.

Ships a stdlib-only Python helper (`init/log/evaluate/summary/status`) owning the
JSONL state + confidence math.

## Package layout (standalone plugin, mirrors html-artifacts)

```
plugins/autoresearch/.claude-plugin/plugin.json
plugins/autoresearch/skills/autoresearch/SKILL.md
plugins/autoresearch/skills/autoresearch/scripts/autoresearch_helper.py
```

`.factory-plugin/` is dropped — Droid reads the `.claude-plugin/` manifest via its
Claude Code compatibility layer (same as flywheel + html-artifacts).

## Manifest (`plugins/autoresearch/.claude-plugin/plugin.json`)

- `name: autoresearch`
- `version: 1.0.0`
- `author: { name: pragmaticgrowth }`
- `license: MIT`
- `repository: https://github.com/pragmaticgrowth/flywheel`
- `homepage: https://github.com/pragmaticgrowth/flywheel/tree/main/plugins/autoresearch`
- `keywords`: skills, autoresearch, optimization, experiments, benchmark,
  autonomous, loop
- description credits the pattern's origin (Factory).

## Skill translation — the real work

Changes from the source SKILL.md:

1. **Script invocation → house convention.** Add a "Resolve paths" step that sets
   `$AR` = `autoresearch_helper.py` via the same resolution chain the other
   flywheel scripts use, scoped to the `autoresearch` plugin:
   `$CLAUDE_PLUGIN_ROOT/skills/autoresearch/scripts/autoresearch_helper.py`,
   else `$DROID_PLUGIN_ROOT/...` (Droid), else newest
   `~/.claude/plugins/{cache,marketplaces}/*/autoresearch/*/skills/autoresearch/scripts/autoresearch_helper.py`,
   else the `~/.factory/...` equivalent. All calls become `python3 "$AR" …`.
   Fixes the source's cwd-relative `python3 autoresearch_helper.py` (which assumed
   the helper lived in the target repo root).

2. **Mission mode → Claude-Code-first, CLI-aware.** Replace the Factory-specific
   spine (`/enter-mission`, `mission-planning`, `define-mission-skills`, "mission
   worker mode") with Claude Code primitives: run the loop in-session; for
   cadence/resume across sessions use `/loop <interval> "resume autoresearch"`
   (Claude Code) or `CronCreate` same_session (Droid), documented the way
   `dispatch` documents both runtimes. Keep a short optional note: "In Droid you
   can run this inside a mission for milestone tracking" — preserved as a note,
   not the backbone.

3. **Rigor hooks → superpowers method skills.** Where they fit, reference the
   ecosystem's method skills: TDD/verification framing for the optional
   `.checks.sh`; the finalization grouping mirrors
   `finishing-a-development-branch`. Light references, not hard gates — the loop
   is the spine.

4. **Default-branch detection.** Finalization's hardcoded `main`
   (`git merge-base HEAD main`) becomes a detected default branch: resolve via
   `git symbolic-ref refs/remotes/origin/HEAD` (strip `refs/remotes/origin/`),
   fall back to `main`.

5. **Context wording.** "Droid sessions have finite context" → session-/CLI-neutral
   wording, same file-based resume protocol.

6. **Attribution.** One-line "Adapted from Factory's autoresearch plugin (MIT)"
   note, matching how `define-goal` credits OpenAI.

Preserved as-is (good, CLI-agnostic): branch isolation model, MAD confidence
scoring, keep/discard/crash/checks_failed decisioning, ASI journaling, JSONL
schema, finalize-into-clean-branches phase. The branch/isolation model is correct
here (speculative change-and-revert research), even though flywheel v4 moved away
from per-goal branches for the goal queue — different problem.

## Helper script

Copied verbatim (stdlib-only, `python3`, already CLI-agnostic). No logic changes.

## Required doc updates (mandated by CLAUDE.md when adding a marketplace plugin)

- `.claude-plugin/marketplace.json` → add third `plugins[]` entry
  (`source: ./plugins/autoresearch`, category, homepage, author).
- `README.md` → document the third plugin + install command.
- `public/index.html` → add autoresearch to the plugin list (no flywheel version
  bump — autoresearch carries its own version).
- `CHANGELOG.md` → new entry for autoresearch 1.0.0 (new plugin), plus annotated
  tag `autoresearch-v1.0.0` + GitHub Release per the release rules.
- Validation + a subagent dry-run of the translated skill before shipping.
- Push (pre-authorized), then `/plugin marketplace update`.

## Scope guard (YAGNI)

No Workflow orchestration, no parallel implementers, no new state formats — the
loop stays sequential and file-resumable. Isolation branch + revert is the
recovery path. Matches the "safe + quality but not complicated" preference.

## Verification

- `plugin-dev:plugin-validator` agent passes (Claude Code).
- `python3 -c "import ast; ast.parse(open('.../autoresearch_helper.py').read())"`
  and a smoke run of `init`/`log`/`evaluate`/`summary`/`status` against a temp
  JSONL succeed.
- Subagent dry-run: give the translated SKILL a scenario, require it to cite the
  section deciding each answer; close every flagged ambiguity.
- `droid plugin marketplace add … && droid plugin install autoresearch@flywheel`
  path validated (or manual frontmatter check).
