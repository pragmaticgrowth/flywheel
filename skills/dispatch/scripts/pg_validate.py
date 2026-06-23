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


def detect_gate_command(file_map):
    # Preference order: Makefile > go.mod > package.json(with test script) > pytest.
    if "Makefile" in file_map:
        return "make test"
    if "go.mod" in file_map:
        return "go test ./..."
    if "package.json" in file_map and '"test"' in (file_map.get("package.json") or ""):
        return "npm test"
    if "pytest.ini" in file_map or "pyproject.toml" in file_map:
        return "pytest -q"
    return None


def repro_direction(base_exits, head_exits, already_correct):
    head_all_green = all(x == 0 for x in head_exits)
    base_any_red = any(x != 0 for x in base_exits)
    if not head_all_green:
        return {"name": "repro-direction", "pass": False, "kind": "fixable",
                "evidence": "an acceptance command is still red on the PR head"}
    if base_any_red:
        return {"name": "repro-direction", "pass": True, "kind": "fixable",
                "evidence": ">=1 command red on base, all green on head — real fix"}
    # nothing was red on base: the change fixed nothing observable
    if already_correct:
        return {"name": "repro-direction", "pass": True, "kind": "fixable",
                "evidence": "nothing red on base; goal documents code was already correct (locking test)"}
    return {"name": "repro-direction", "pass": False, "kind": "contract",
            "evidence": "nothing red on base — the bug 'fixed' nothing (tautology/already-fixed); "
                        "document 'already correct' with a locking test if so"}


def acceptance_green(head_exits):
    if not head_exits:
        return {"name": "acceptance-green", "pass": False, "kind": "inconclusive",
                "evidence": "no acceptance command could be resolved for this goal"}
    if all(x == 0 for x in head_exits):
        return {"name": "acceptance-green", "pass": True, "kind": "fixable",
                "evidence": f"all {len(head_exits)} acceptance command(s) green on a fresh head checkout"}
    red = [i for i, x in enumerate(head_exits) if x != 0]
    return {"name": "acceptance-green", "pass": False, "kind": "fixable",
            "evidence": f"acceptance command(s) red on fresh head checkout: index {red}"}


def one_goal_integrity(head_branch, body, pr_base, base, changed_paths, goal_id):
    if head_branch != f"goal/{goal_id}":
        return {"name": "one-goal-integrity", "pass": False, "kind": "fixable",
                "evidence": f"head branch {head_branch!r} is not goal/{goal_id}"}
    if f"Goal: {goal_id}" not in (body or ""):
        return {"name": "one-goal-integrity", "pass": False, "kind": "fixable",
                "evidence": f"PR body missing the 'Goal: {goal_id}' marker"}
    if pr_base != base:
        return {"name": "one-goal-integrity", "pass": False, "kind": "fixable",
                "evidence": f"PR base {pr_base!r} != configured base {base!r}"}
    for p in changed_paths:
        if p.startswith("docs/goals/"):
            return {"name": "one-goal-integrity", "pass": False, "kind": "fixable",
                    "evidence": f"PR edits queue file {p!r}; implementers must never touch docs/goals/"}
    return {"name": "one-goal-integrity", "pass": True, "kind": "fixable",
            "evidence": "single-goal PR, correct base, no queue edits"}


import argparse, json, os, subprocess, tempfile
EXIT = {"PASS": 0, "FAIL_FIXABLE": 3, "FAIL_CONTRACT": 3, "INCONCLUSIVE": 4}


def _run(cmd, **kw):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, **kw)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "not found"


def _gh_json(args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "gh failed")
    return json.loads(out.stdout or "null")


def _git(args, **kw):
    out = subprocess.run(["git", *args], capture_output=True, text=True, **kw)
    return out.returncode, out.stdout, out.stderr


def _changed_paths(base):
    rc, out, _ = _git(["diff", "--name-only", f"origin/{base}..HEAD"])
    return [p for p in out.splitlines() if p.strip()] if rc == 0 else []


def _diff_text(base):
    rc, out, _ = _git(["diff", f"origin/{base}..HEAD"])
    return out if rc == 0 else ""


def _parse_goal(path):
    """Return (type, touches, acceptance_cmds, already_correct_doc)."""
    text = open(path).read() if os.path.exists(path) else ""
    gtype, touches, cmds = "feature", [], []
    if text.startswith("---"):
        parts = text.split("---", 2)
        fm = parts[1] if len(parts) >= 3 else ""
        for line in fm.splitlines():
            field = line.split(":", 1)[1].strip() if ":" in line else ""
            ls = line.strip()
            if ls.startswith("type:") and field:
                gtype = field.split()[0]
            elif ls.startswith("touches:") and field:
                touches = [t.strip().strip("-\"'[] ") for t in field.split(",") if t.strip()]
            elif ls.startswith("acceptance:") and field:
                cmds = [c.strip().strip("-\"'[] ") for c in field.split(",") if c.strip()]
    already_correct = "already correct" in text.lower() or "already-correct" in text.lower()
    return gtype, touches, cmds, already_correct


def _resolve_cmds(goal_file, repo_root):
    gtype, touches, goal_cmds, ac = _parse_goal(goal_file)
    if goal_cmds:
        return gtype, touches, goal_cmds, ac
    fm = {}
    for name in ("Makefile", "go.mod", "package.json", "pytest.ini", "pyproject.toml"):
        p = os.path.join(repo_root, name)
        if os.path.exists(p):
            try:
                fm[name] = open(p).read()
            except OSError:
                pass
    det = detect_gate_command(fm)
    return gtype, touches, ([det] if det else []), ac


def _run_cmds(cmds, cwd):
    return [subprocess.run(["bash", "-lc", c], capture_output=True, text=True, cwd=cwd).returncode
            for c in cmds]


def _self_test():
    import test_pg_validate as t
    fns = [g for n, g in sorted(vars(t).items())
           if n.startswith("test_") and n != "test_self_test_exits_zero_and_announces"]
    for fn in fns:
        fn()
    print(f"self-test: {len(fns)} pure check cases passed")
    return 0


def run_validation(pr, goal_id, base, goal_file, repo_root):
    checks = []
    pr_meta = _gh_json(["pr", "view", pr, "--json", "headRefName,baseRefName,body,headRefOid"])
    _, head_sha, _ = _git(["rev-parse", "HEAD"])
    _, base_sha, _ = _git(["rev-parse", f"origin/{base}"])
    sha_head, sha_base = head_sha.strip(), base_sha.strip()
    changed = _changed_paths(base)
    gtype, touches, cmds, already_correct = _resolve_cmds(goal_file, repo_root)

    checks.append(one_goal_integrity(pr_meta["headRefName"], pr_meta["body"],
                                     pr_meta["baseRefName"], base, changed, goal_id))
    checks.append(blast_radius(changed, touches))
    checks.append(forbidden_content(_diff_text(base)))

    if gtype == "bug":
        with tempfile.TemporaryDirectory() as basewt:
            _git(["worktree", "add", "--detach", basewt, f"origin/{base}"])
            base_exits = _run_cmds(cmds, basewt) if cmds else []
            _git(["worktree", "remove", basewt, "--force"])
        head_exits = _run_cmds(cmds, repo_root) if cmds else []
        checks.append(repro_direction(base_exits, head_exits, already_correct))
    else:
        head_exits = _run_cmds(cmds, repo_root) if cmds else []
        checks.append(acceptance_green(head_exits))

    verdict = aggregate(checks)
    return {"verdict": verdict, "sha_head": sha_head, "sha_base": sha_base,
            "checks": checks, "summary": f"{verdict} @ {sha_head[:12]} (base {sha_base[:12]})"}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pg_validate.py")
    ap.add_argument("--pr"); ap.add_argument("--goal"); ap.add_argument("--base")
    ap.add_argument("--goal-file"); ap.add_argument("--worktree-root")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if not (a.pr and a.goal and a.base and a.goal_file):
        ap.error("--pr, --goal, --base and --goal-file are required")
    repo_root = a.worktree_root or os.getcwd()
    try:
        result = run_validation(a.pr, a.goal, a.base, a.goal_file, repo_root)
    except Exception as e:  # environment/infra failure -> INCONCLUSIVE, never default-PASS
        print(json.dumps({"verdict": "INCONCLUSIVE", "checks": [],
                          "summary": f"environment error: {e}"}, indent=2))
        return 4
    print(json.dumps(result, indent=2))
    return EXIT[result["verdict"]]


if __name__ == "__main__":
    import sys
    sys.exit(main())
