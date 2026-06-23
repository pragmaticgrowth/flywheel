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


import re

# Only scan ADDED lines (start with '+' but not '+++').
_SECRET_PATTERNS = (
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}"),
    re.compile(r"sk-[0-9A-Za-z]{20,}"),  # OpenAI-style keys
)


def forbidden_content(diff_text):
    for line in (diff_text or "").splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for pat in _SECRET_PATTERNS:
            if pat.search(line):
                return {"name": "forbidden-content", "pass": False, "kind": "fixable",
                        "evidence": f"secret-shaped string in added line: {pat.pattern}"}
    return {"name": "forbidden-content", "pass": True, "kind": "fixable",
            "evidence": "no secret-shaped strings in added lines"}


_RISK_PATH_KEYWORDS = ("auth", "billing", "payment", "migration", "deploy",
                       "prod", "secret", "credential", "password")
_RISK_FILENAMES = ("go.mod", "go.sum", "package.json", "package-lock.json",
                   "requirements.txt", "Cargo.toml", "Gemfile")
_FILE_THRESHOLD = 12


def chore_risk_flagged(changed_paths):
    if len(changed_paths) > _FILE_THRESHOLD:
        return True
    for p in changed_paths:
        low = p.lower()
        name = p.rsplit("/", 1)[-1]
        if any(k in low for k in _RISK_PATH_KEYWORDS):
            return True
        if name in _RISK_FILENAMES:
            return True
    return False


def in_scope(goal_type, changed_paths, mode):
    if mode == "off":
        return False
    if mode == "required":
        return True
    # risk_based (default)
    if goal_type in ("bug", "feature"):
        return True
    if goal_type == "chore":
        return chore_risk_flagged(changed_paths)
    return True  # unknown type → validate to be safe
