---
id: 005-plural-publish-paths
title: Ship runs every publish path the repo's docs declare
created: 2026-08-28
type: feature
skills: []
model: heavy
size: S
touches:
  - skills/dispatch/SKILL.md
  - CLAUDE.md
acceptance:
  - uv run --with pytest --python 3.13 pytest -q test_plural_ship_policy.py
---

## Outcome (plain language)

Dispatch's Ship step today runs one path and emits one `shipped:` outcome. After this goal, when the target repo's own docs declare more than one publish path, Ship runs every declared path the diff touched and reports per-service; one shipped and one not is `ship FAILED: partial (<service> unshipped)` under needs-you class `environment failure`. Dispatch still never invents a deploy.

## Context / why

provenance: inbox-drain. Verified 2026-08-28: `skills/dispatch/SKILL.md` Ship step (Phase 0) is singular — "RUN that path now", one `shipped:` / `ship FAILED:` outcome. `/root/nonresidenttax/AGENTS.md` declares both `main` auto-deploy (Vercel product) and per-Worker `pnpm --filter @nt/<app> deploy:production` (auth, edge, web, product-data, mcp, support). Keys strictly off the target repo's docs.

Assumptions: "the diff touched" means the `gate_base..HEAD` (or, at a terminal drain stop, the commits this run produced) intersects a path the declaring doc ties to that publish command; if the docs do not map paths to services, run every declared path. `new file: test_plural_ship_policy.py` is the proving surface named in `acceptance:` — this goal is `type: feature`, so pg_validate's bug-only repro-direction overlay (the path that INCONCLUSIVEs when `acceptance:` names a file added by the fix) does not run.

**Amended 2026-08-28:** implementer stopped CONTRACT_AMBIGUOUS (new-file runner vs existing module, citing goal 004). Settled reading: keep `acceptance:` on `test_plural_ship_policy.py`; 004's INCONCLUSIVE is `gtype == "bug"` only (`skills/dispatch/scripts/pg_validate.py`). provenance: dispatch-self-heal.

## Acceptance criteria

- [ ] `uv run --with pytest --python 3.13 pytest -q test_plural_ship_policy.py` is RED at this goal's base and GREEN after: Ship step text in `skills/dispatch/SKILL.md` and the matching CLAUDE.md restatement require running every declared publish path the diff touched when docs declare >1; `ship FAILED: partial` is a legal outcome; needs-you class `environment failure` still names the partial; "never invents a deploy" remains.
- [ ] `uv run --with pytest --python 3.13 pytest -q` is green (never fewer than the 262 tests passing at authoring).

## Constraints (hard rules)

- Skills-first. Don't add MCP servers, commands, agents, or hooks here without an explicit ask.
- Portability. Skills must not contain user-specific absolute paths (`/Users/...`) for either harness.
- Skill edits are tested. For compliance-critical rules, add a RED baseline against `git show HEAD:<file>`.
- Never push protected branches.

## Out of scope

- Implementing deploys for nonresidenttax in this repo.
- Version bump / CHANGELOG / GitHub release.
