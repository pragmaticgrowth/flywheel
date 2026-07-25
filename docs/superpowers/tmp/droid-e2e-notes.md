# Droid E2E evidence — v7.0.0 dual-target port (2026-07-25)

All runs against the local `flywheel` marketplace install (`flywheel@flywheel`),
updated to the port commits, in a scratch repo `/tmp/flywheel-e2e-*`.

## Pipeline smokes (live, `droid exec`)

1. **goals-status** (`--auto medium`): rendered the queue verbatim; a goal
   stamped `model: sonnet` displayed as `chore · medium` — the alias
   normalization live on Droid, script resolved via the `~/.factory/plugins/cache`
   fallback.
2. **factory-doctor** (`--auto medium`): full probe ran (14 checks), correct
   WARN on an underspecified goal contract, correct status line. Resolved
   `doctor_checks.py` through the Droid cache fallback.
3. **dispatch** (`--auto high` — Task tool is gated behind high autonomy):
   - First run: implementer produced the change, but the gate returned
     INCONCLUSIVE (goal had prose criteria, no `acceptance:` field) → correctly
     rolled back to `gate_base` and blocked with the exact needs-you fix. The
     gate refusing a silent PASS is the designed behavior.
   - After adding `acceptance: ["grep -q smoke-ok NOTES.md"]` and unblocking:
     claim → implement → gate PASS → squash `feat(goal 001-smoke)` → 
     `chore(goals): complete` → `1/1 done [████████████████████]`. Full commit
     trail verified in the scratch repo log.

## Subagent-driven dry-runs with RED baselines (repo rule)

Three worker subagents each answered scenario questions from the v6.2.0 text
(`git show v6.2.0:<file>`) and then from the new text, citing deciding lines:

1. **Tier stamping**: OLD stamps `opus` / silent on Droid; NEW stamps `heavy` /
   resolves `sonnet`→medium→`complexity: medium` on a `worker` spawn. RED→GREEN
   confirmed.
2. **Escalation ladder**: OLD undecidable for a `medium` stamp (no alias table)
   and had zero Droid mechanics; NEW fires rung 2 explicitly. RED→GREEN
   confirmed.
3. **Scheduling rail**: OLD prescribed an unrunnable `claude -p` on a
   Droid-only machine; NEW prescribes OS scheduler + `droid exec "/dispatch"`,
   CronCreate/automations excluded, blind-cadence on Droid. RED→GREEN confirmed.

## Ambiguities flagged by the dry-runs → fixed in follow-up edits

- Rung-2 heading said "light-stamped" while the body said medium-or-light →
  heading now "cheap-stamped", and the rung states explicitly that omitting the
  tier mapping (inherit the session model) IS the escalation — never pass
  `heavy` instead.
- The Droid `complexity` value set now carries its live-verified marker, and
  "implementers always spawn as `worker` regardless of tier" is stated
  separately from the mapping.
- define-goal's per-run recon override now accepts legacy model names as
  aliases ("run recon on opus" → heavy).
- loop-architect's built-ins exclusion now names CronCreate AND automations
  (local + cloud modes) explicitly.

## Agent allowlist verification

- `tools: Bash, Execute, ...` translated verbatim into the Droid cache; a live
  `gate-reviewer` spawn confirmed it can run shell (`echo probe-ok`) and has NO
  file-editing/creating tools. Read-only preserved on both harnesses.
