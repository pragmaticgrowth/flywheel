"""Deterministic PR validation gate for pg-plugin (Phase 1, no LLM).
Dispatch Integration runs this on a fresh checkout BEFORE pg_safe_merge.
Emits a SHA-bound {PASS|FAIL_FIXABLE|FAIL_CONTRACT|INCONCLUSIVE} verdict.
Never edits, pushes, or merges — read-only + runs the goal's own commands."""

VERDICTS = ("PASS", "FAIL_FIXABLE", "FAIL_CONTRACT", "INCONCLUSIVE")


def aggregate(results):
    """Combine per-check results into one verdict. Precedence:
    contract-fail > fixable-fail > inconclusive > pass."""
    kinds = [r["kind"] for r in results if not r["pass"]]
    if any(k == "contract" for k in kinds):
        return "FAIL_CONTRACT"
    if any(k == "fixable" for k in kinds):
        return "FAIL_FIXABLE"
    if any(k == "inconclusive" for k in kinds):
        return "INCONCLUSIVE"
    return "PASS"


import fnmatch

# fnmatch '*' spans '/', so '.claude/*' matches nested paths too.
FORBIDDEN_PATHS = (".claude/*", ".github/workflows/*", "*/deploy*.sh", "deploy*.sh")
LOCKFILES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum",
             "Gemfile.lock", "poetry.lock", "Cargo.lock", "composer.lock")


def _any_match(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def blast_radius(changed_paths, touches):
    for p in changed_paths:
        name = p.rsplit("/", 1)[-1]
        if _any_match(p, FORBIDDEN_PATHS) and not _any_match(p, touches):
            return {"name": "blast-radius", "pass": False, "kind": "fixable",
                    "evidence": f"forbidden path changed: {p}"}
        if name in LOCKFILES and not _any_match(p, touches):
            return {"name": "blast-radius", "pass": False, "kind": "fixable",
                    "evidence": f"lockfile/dep churn not in declared surfaces: {p}"}
        if touches and not _any_match(p, touches):
            return {"name": "blast-radius", "pass": False, "kind": "fixable",
                    "evidence": f"changed path outside declared surfaces: {p}"}
    return {"name": "blast-radius", "pass": True, "kind": "fixable",
            "evidence": f"{len(changed_paths)} path(s), all in scope"}
