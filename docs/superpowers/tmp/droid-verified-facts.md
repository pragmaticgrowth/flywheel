# Droid live-verified facts — dual-target port (2026-07-25)

Verified in a live Factory Droid environment (darwin, droid CLI current as of
2026-07-25) against this repo at commit `48a37b8`. These answer the three open
questions from the plan's "Still to verify" list, plus incidental findings.

## (a) Marketplace add + install of this Claude-layout repo

- `droid plugin marketplace add /Users/serkan/flywheel` → registered as
  marketplace **`flywheel`** (the FOLDER name, not marketplace.json's
  `pragmatic-growth`). Install id is therefore `flywheel@flywheel` for the
  local-path dev flow. Evidence: `Successfully added marketplace: flywheel`;
  `install flywheel@pragmatic-growth` → `Marketplace "pragmatic-growth" not found`.
  - Consequence for docs: the GitHub-URL add (Task 13 / README) must be
    re-checked for its marketplace name; do not assume `pragmatic-growth`.
- `droid plugin install flywheel@flywheel --scope user` → installed at
  `~/.factory/plugins/cache/flywheel/flywheel/<commit12>/` — the WHOLE repo
  tree is copied (skills/, droids/, plugins/, docs/, .git/ …).
- The Claude layout translated automatically: root `agents/*.md` → `droids/*.md`
  in the cache; `.claude-plugin/plugin.json` → `.factory-plugin/plugin.json`
  (JSON content preserved, unicode-escaped).
- **Hot-loading works**: the plugin's droids were spawnable via the Task tool in
  the ALREADY-RUNNING session that performed the install, and the six skills
  registered under their bare names (`define-goal`, `dispatch`, …) in a fresh
  `droid exec` session.

## (b) Plugin-droid spawn naming

- Spawn by **bare name**: `subagent_type: "gate-reviewer"` worked. There is no
  `flywheel:` namespace prefix on Droid (that prefix is Claude Code's
  convention). Skills' mapping blocks must say: Claude Code
  `flywheel:gate-reviewer`, Droid `gate-reviewer`.

## (c) `tools: Bash` translation — THE critical finding

- The `tools: Bash, Read, Grep, Glob, ToolSearch, SendMessage` frontmatter line
  survives translation **verbatim** — no Bash→Execute mapping.
- Live spawn of `gate-reviewer` reported its available tools as:
  `Read, Grep, Glob, ExitSpecMode, TodoWrite, Skill` — **no shell tool**.
  Unknown names (`Bash`, `ToolSearch`, `SendMessage`) are silently dropped, and
  some session basics (TodoWrite, Skill) are added regardless.
- Consequence (Task 10): allowlists must become
  `tools: Bash, Execute, Read, Grep, Glob, ToolSearch, SendMessage` — each
  harness silently ignores the other's shell tool name; read-only is preserved
  on both (no Edit/Write/Create/ApplyPatch/Task in the list). Re-verify after
  the edit by re-spawning and asking the agent to run `echo probe-ok`.

## Incidental findings

- `droid exec` autonomy gates the Task tool: `--auto low|medium` → Task
  **blocked**; `--auto high` → allowed. Any skill text that has a Droid
  headless run spawning subagents (dispatch cycles) must say `--auto high`.
  (`Execute` is allowed at medium; low is read-only-ish.)
- `droid exec --list-tools` for Opus 5 shows Droid's canonical tool names:
  `Execute` (shell), `Create`/`Edit`/`ApplyPatch` (writes), `Task`, `Skill`,
  `ToolSearch`, `TodoWrite`, `FetchUrl`, `WebSearch`, `Read/Grep/Glob/LS`.
  No `Bash`, no `Write`.
- Deviation from plan Task 1 Step 5: the local install is KEPT (not
  uninstalled) — Tasks 8/10/13 re-verify against it via `droid plugin update`,
  which re-copies from the local path. Swap to the GitHub marketplace happens
  in Task 13.
