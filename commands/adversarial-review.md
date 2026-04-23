---
description: Adversarial review that challenges design choices — not just code quality
argument-hint: '[--base <ref>] [focus area...]'
allowed-tools: Bash(git:*), mcp__mcp-do__do_audit
---

Run an adversarial review via `do_audit` (GPT-5.4 via Codex). Challenges the chosen implementation, design choices, tradeoffs, and assumptions — not just code defects. Returns a typed verdict: pass / concerns / blockers.

**Raw arguments:** `$ARGUMENTS`

## Context Gathering

1. Run `git diff --stat` and `git diff --cached --stat` to see what changed
2. If there are no changes, check `git diff --stat main...HEAD` (or the base ref) for branch changes
3. If still no changes, tell the user there's nothing to review and stop
4. Run the appropriate `git diff` to get the full diff

## Scope

- Default: all staged + unstaged changes
- If the user specified `--base <ref>`, use `git diff <ref>...HEAD`
- If `$ARGUMENTS` contains paths (non-flag text that looks like paths), limit the diff to them

## Focus Text

Any non-flag text in `$ARGUMENTS` that is NOT a path is adversarial focus — areas to pressure-test. Examples:
- "challenge whether this was the right caching design"
- "look for race conditions and question the chosen approach"
- "focus on rollback safety and data loss scenarios"

## Execution

Call `mcp__mcp-do__do_audit` with:

- `context`: the focus text from `$ARGUMENTS`, or the generic adversarial prompt below if none was given:
  > Challenge the design, tradeoffs, and assumptions — not just code defects. Question whether this was the right approach at all. Pressure-test rollback safety, failure modes, and hidden costs.
- `diff`: the full git diff output
- `reasoning_effort`: `"high"` (default is already high; don't override)

**Return the result verbatim.**

Do NOT fix issues. Do NOT apply patches. Do NOT add commentary. Review only.
