**Minor: two new marketplace plugins — `autoresearch` 1.0.0 and `human-writing`
1.0.0**, bringing the `pragmatic-growth` marketplace to four plugins alongside
`flywheel` and `html-artifacts`. Both are adapted from Factory plugins and
translated to be Claude-Code-first while staying CLI-aware, matching the
conventions of the existing plugins.

#### `autoresearch` 1.0.0 — autonomous optimization loop

- **What it does.** Given a measurable metric, a benchmark command, files in
  scope, constraints, and a termination condition, it works an
  `autoresearch/<goal>-<date>` branch: try one hypothesis → run the benchmark →
  keep the change if the primary metric improves and `git`-revert it if not →
  journal what was learned (ASI) → repeat. **MAD-based confidence scoring**
  separates real gains from benchmark noise. On termination it groups the kept
  experiments into independently-mergeable branches for review; the raw
  experiment branch is always preserved.
- **File-based, resumable.** All state lives in the target repo
  (`autoresearch.md` living doc, `autoresearch.sh` benchmark emitting
  `METRIC name=value`, append-only `autoresearch.jsonl`, optional `.checks.sh` /
  `.ideas.md`), so a fresh session with no memory reads them and continues
  exactly where the last one stopped. Ships one stdlib-only helper,
  `scripts/autoresearch_helper.py` (`init`/`log`/`evaluate`/`summary`/`status`).
- **Translated to Claude Code, still CLI-aware.** `.claude-plugin` manifest; the
  helper is resolved via `$CLAUDE_PLUGIN_ROOT`/`$DROID_PLUGIN_ROOT` with a
  cache-glob fallback (the house convention) instead of the source's
  cwd-relative call; the Factory mission-mode spine is replaced with `/loop`
  (Claude Code) or same-session `CronCreate` (Droid) for unattended cadence,
  with an optional Droid-mission note; finalization detects the repo's default
  branch instead of hardcoding `main`; context wording is session-neutral. A
  dry-run review then hardened the port: robust base-branch resolution with a
  guard, and clean `log` snippets (the upstream's mid-command `# --metrics`
  comment had orphaned the trailing `--direction`).
- Adapted from Factory's `autoresearch` plugin (MIT).

#### `human-writing` 1.0.0 — AI-writing cleanup

- **What it does.** Edits AI-sounding text into human prose: scans for the tells
  catalogued in Wikipedia's "Signs of AI writing" — inflated significance,
  promotional language, `-ing` filler, em-dash and rule-of-three overuse, AI
  vocabulary, vague attributions, and chatbot artifacts ("I hope this helps!") —
  rewrites them, and pushes for real voice instead of clean-but-soulless prose.
- **CLI-neutral, minimal port.** Pure writing guidance — one `SKILL.md`, no
  scripts, state, or references — so it needed no runtime translation beyond
  house frontmatter (`name` + `description`, dropped the upstream `version:`) and
  attribution. Extracted from Factory's multi-skill `droid-evolved` plugin as a
  standalone single-skill plugin. Content based on Wikipedia's guide (WikiProject
  AI Cleanup, CC BY-SA).

#### Marketplace

- **Install.** `/plugin install autoresearch@pragmatic-growth` and
  `/plugin install human-writing@pragmatic-growth` (Claude Code), or the
  `@flywheel` equivalents (Droid). `marketplace.json`, `README.md`, the public
  site, and `CLAUDE.md`/`AGENTS.md` all updated to list four plugins. Release
  commit: [`557b933`](https://github.com/pragmaticgrowth/flywheel/commit/557b933).
