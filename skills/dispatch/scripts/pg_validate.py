"""Deterministic LOCAL validation gate for flywheel — no PRs, no network, no LLM.
dispatch runs this on the goal's <base>..<head> local diff before keeping its commit.
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

# Gitignored dependency dirs absent from a fresh checkout. The bug repro-direction
# best-effort symlinks these from the live checkout into the base worktree so a
# test-runner acceptance command (npm test / pytest) has a working environment on base.
DEP_DIRS = ("node_modules", ".venv", "venv", "vendor")


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


def repro_direction(base_exits, head_exits, already_correct, overlaid_tests=None):
    # overlaid_tests: the PR head's changed test files that were copied onto the base
    # checkout before running acceptance. In standard TDD the proving test is ADDED by the
    # fix PR, so it does not exist on base — running the bare base suite can never go red
    # and every good TDD fix would FAIL_CONTRACT. Overlaying the head's tests onto base
    # product code is the canonical red-on-base proof: a real regression test fails there
    # (bug still present) and passes on head (bug fixed). None = no overlay performed.
    overlaid = list(overlaid_tests or [])
    head_all_green = all(x == 0 for x in head_exits)
    base_any_red = any(x != 0 for x in base_exits)
    if not head_all_green:
        return {"name": "repro-direction", "pass": False, "kind": "fixable",
                "evidence": "an acceptance command is still red on the PR head"}
    if base_any_red:
        how = (f"with the PR's {len(overlaid)} test file(s) overlaid onto base, "
               if overlaid else "")
        return {"name": "repro-direction", "pass": True, "kind": "fixable",
                "evidence": f">=1 command red on base {how}all green on head — "
                            "the test reproduces the bug, the fix resolves it (real fix)"}
    # nothing was red on base: the change fixed nothing observable
    if already_correct:
        return {"name": "repro-direction", "pass": True, "kind": "fixable",
                "evidence": "nothing red on base; goal documents code was already correct (locking test)"}
    if overlaid:
        return {"name": "repro-direction", "pass": False, "kind": "contract",
                "evidence": f"the PR's test file(s) {overlaid} were overlaid onto base product "
                            "code and still passed — the test does not reproduce the bug "
                            "(tautology/already-fixed). Write a test that fails on base, or "
                            "document 'already correct' with a locking test."}
    return {"name": "repro-direction", "pass": False, "kind": "contract",
            "evidence": "nothing red on base and the PR adds no recognizable test file, so the "
                        "fix can't be proven to reproduce->resolve a real bug. Add a failing "
                        "regression test (whose command is in acceptance:), or document "
                        "'already correct' with a locking test."}


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


def _git(args, **kw):
    out = subprocess.run(["git", *args], capture_output=True, text=True, **kw)
    return out.returncode, out.stdout, out.stderr


def _changed_paths(base_ref, head_ref="HEAD"):
    rc, out, _ = _git(["diff", "--name-only", f"{base_ref}..{head_ref}"])
    return [p for p in out.splitlines() if p.strip()] if rc == 0 else []


def is_test_path(p):
    """Heuristic test-file detector spanning JS/TS, Python, Go, Ruby, Rust, etc."""
    base = p.rsplit("/", 1)[-1]
    low = p.lower()
    if any(seg in low for seg in
           ("/__tests__/", "/test/", "/tests/", "/spec/", "/specs/", "/e2e/")):
        return True
    if any(t in base for t in (".test.", ".spec.", "_test.", "-test.", ".tests.")):
        return True
    if base.startswith("test_") and base.endswith(".py"):
        return True
    if base.endswith("_test.go") or base.endswith("_spec.rb") or base.endswith("Test.java"):
        return True
    return False


def _changed_test_files(base_ref, head_ref="HEAD"):
    return [p for p in _changed_paths(base_ref, head_ref) if is_test_path(p)]


def _diff_text(base_ref, head_ref="HEAD"):
    rc, out, _ = _git(["diff", f"{base_ref}..{head_ref}"])
    return out if rc == 0 else ""


def _parse_goal(path):
    """Return (type, touches, acceptance_cmds, already_correct_doc)."""
    text = open(path).read() if os.path.exists(path) else ""
    gtype, touches, cmds = "feature", [], []
    if text.startswith("---"):
        parts = text.split("---", 2)
        fm = parts[1] if len(parts) >= 3 else ""
        _collecting = None  # tracks which list field we're accumulating into
        for line in fm.splitlines():
            field = line.split(":", 1)[1].strip() if ":" in line else ""
            ls = line.strip()
            if ls.startswith("type:") and field:
                gtype = field.split()[0]
                _collecting = None
            elif ls.startswith("touches:"):
                _collecting = None
                if field:
                    touches = [t.strip().strip("-\"'[] ") for t in field.split(",") if t.strip()]
                else:
                    touches = []; _collecting = "touches"
            elif ls.startswith("acceptance:"):
                _collecting = None
                if field:
                    cmds = [c.strip().strip("-\"'[] ") for c in field.split(",") if c.strip()]
                else:
                    cmds = []; _collecting = "acceptance"
            elif _collecting and ls.startswith("#"):
                continue  # YAML comment inside the block list — skip, keep collecting
            elif _collecting and ls.startswith("-"):
                item = ls.lstrip("- \t").strip("\"'")
                if _collecting == "acceptance":
                    cmds.append(item)
                elif _collecting == "touches":
                    touches.append(item)
            elif ls and not ls.startswith("-"):
                _collecting = None  # non-list-item line ends collection
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
    # Pure-logic sweep only: skip the subprocess-driven self-test reentry and the
    # local-mode integration tests (test_local_*), which spawn the CLI end-to-end and
    # belong to the pytest run, not the in-process pure-check sweep.
    import test_pg_validate as t
    fns = [g for n, g in sorted(vars(t).items())
           if n.startswith("test_")
           and n != "test_self_test_exits_zero_and_announces"
           and not n.startswith("test_local_")]
    for fn in fns:
        fn()
    print(f"self-test: {len(fns)} pure check cases passed")
    return 0


def run_validation(head, goal_id, base, goal_file, repo_root):
    checks = []
    rc_head, sha_head, err_head = _git(["rev-parse", head]); sha_head = sha_head.strip()
    rc_base, sha_base, err_base = _git(["rev-parse", base]); sha_base = sha_base.strip()
    # Fail loud on unresolved refs: an empty/failed rev-parse must never flow into the
    # diffs and summary as a silent degrade. The v4 gate returns INCONCLUSIVE, never a
    # default PASS, when it cannot establish the SHAs it is validating.
    if rc_head != 0 or not sha_head or rc_base != 0 or not sha_base:
        bad = []
        if rc_head != 0 or not sha_head:
            bad.append(f"head {head!r} ({(err_head or '').strip() or 'empty SHA'})")
        if rc_base != 0 or not sha_base:
            bad.append(f"base {base!r} ({(err_base or '').strip() or 'empty SHA'})")
        evidence = "could not resolve ref(s): " + "; ".join(bad)
        return {
            "verdict": "INCONCLUSIVE",
            "sha_head": sha_head,
            "sha_base": sha_base,
            "checks": [{"name": "resolve-refs", "pass": False, "kind": "inconclusive",
                        "evidence": evidence}],
            "summary": f"INCONCLUSIVE: {evidence}",
        }
    # No PR exists locally: synthesize the structural inputs so one_goal_integrity's
    # branch-name and body-marker sub-checks are satisfied trivially; only the
    # "no docs/goals/ edits" sub-check is meaningful in local mode.
    head_branch = f"goal/{goal_id}"
    body = f"Goal: {goal_id}"
    pr_base = base
    gtype, touches, cmds, already_correct = _resolve_cmds(goal_file, repo_root)
    changed = _changed_paths(sha_base, sha_head)

    checks.append(one_goal_integrity(head_branch, body, pr_base, base, changed, goal_id))
    checks.append(blast_radius(changed, touches))
    checks.append(forbidden_content(_diff_text(sha_base, sha_head)))

    if gtype == "bug":
        # Overlay the head's changed test files onto the base checkout so a TDD test
        # ADDED by the fix can still reproduce the bug on base product code (red-on-base).
        # Without this, every standard TDD fix (test introduced by the fix) is structurally
        # un-provable and FAIL_CONTRACTs. Overlay is monotonic: it only adds tests, never
        # removes the bug, so it can only move base toward red (the PASS direction).
        #
        # A fresh base worktree has NO installed deps (node_modules/.venv are gitignored), so
        # a test-runner acceptance (npm test / pytest) would red on base for ENVIRONMENT
        # reasons, not the bug — and be mistaken for a reproduction (false PASS). Two guards:
        # (a) best-effort symlink the live checkout's dep dirs into the base worktree; and
        # (b) when the proving test is a separate overlaid file, run a BARE-BASE control
        # FIRST (no overlay) — if base can't run the acceptance clean before the proving
        # test exists, the red is environment/pre-existing noise → INCONCLUSIVE, never PASS.
        # (Direct-probe acceptance — no overlaid test file, e.g. `grep` — needs no deps, so
        # the control is skipped and base-red is the legitimate bug signal.)
        test_files = _changed_test_files(sha_base, sha_head)
        bare_base_exits = []
        with tempfile.TemporaryDirectory() as basewt:
            rc_wt, _wt_out, wt_err = _git(["worktree", "add", "--detach", basewt, sha_base])
            if rc_wt != 0:
                # Could not populate the base checkout: acceptance would run in an
                # empty/incomplete dir, go red, and forge a false repro PASS. Return
                # INCONCLUSIVE (never PASS) rather than proceed. The temp dir is cleaned
                # by the context manager; no worktree was registered, so no remove needed.
                evidence = ("could not create base worktree for repro-direction: "
                            + ((wt_err or "").strip() or "git worktree add failed"))
                return {
                    "verdict": "INCONCLUSIVE",
                    "sha_head": sha_head,
                    "sha_base": sha_base,
                    "checks": checks + [{"name": "repro-direction", "pass": False,
                                         "kind": "inconclusive", "evidence": evidence}],
                    "summary": f"INCONCLUSIVE: {evidence}",
                }
            links = []
            try:
                # (a) best-effort: share the live checkout's installed dep dirs. We only ever
                # create/remove the symlink itself — never touch the real target dirs.
                for d in DEP_DIRS:
                    src = os.path.join(repo_root, d)
                    dst = os.path.join(basewt, d)
                    if os.path.isdir(src) and not os.path.exists(dst):
                        try:
                            os.symlink(src, dst)
                            links.append(dst)
                        except OSError:
                            pass
                # (b) control: bare base (only meaningful when a separate proving test is
                # overlaid — otherwise base_exits IS the bare run).
                if test_files:
                    bare_base_exits = _run_cmds(cmds, basewt) if cmds else []
                    _git(["-C", basewt, "checkout", sha_head, "--", *test_files])
                base_exits = _run_cmds(cmds, basewt) if cmds else []
            finally:
                for link in links:
                    try:
                        os.unlink(link)  # remove the symlink, never the target
                    except OSError:
                        pass
                _git(["worktree", "remove", basewt, "--force"])
        # If the bare base (pre-overlay) couldn't run the acceptance clean, the base "red" is
        # environment/setup noise or a pre-existing failure, not a bug reproduction — never
        # let that forge a PASS.
        if test_files and cmds and any(x != 0 for x in bare_base_exits):
            evidence = ("base checkout could not run the acceptance command(s) clean before "
                        "the proving test was overlaid (missing deps/setup in the base "
                        "checkout, a pre-existing base failure, or an acceptance command that "
                        "names a test file added by this fix — scope acceptance at a stable "
                        "runner, not the new file) — cannot prove repro-direction. "
                        "Verify the fix manually.")
            return {
                "verdict": "INCONCLUSIVE",
                "sha_head": sha_head,
                "sha_base": sha_base,
                "checks": checks + [{"name": "repro-direction", "pass": False,
                                     "kind": "inconclusive", "evidence": evidence}],
                "summary": f"INCONCLUSIVE: {evidence}",
            }
        head_exits = _run_cmds(cmds, repo_root) if cmds else []
        checks.append(repro_direction(base_exits, head_exits, already_correct, test_files))
    else:
        head_exits = _run_cmds(cmds, repo_root) if cmds else []
        checks.append(acceptance_green(head_exits))

    verdict = aggregate(checks)
    return {
        "verdict": verdict,
        "sha_head": sha_head,
        "sha_base": sha_base,
        "checks": checks,
        "summary": f"{verdict} @ {sha_head[:12]} (base {sha_base[:12]})",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pg_validate.py")
    ap.add_argument("--head", help="git ref or SHA of the head to validate (default HEAD)", default="HEAD")
    ap.add_argument("--base", required=False)   # now a git ref/SHA, not a remote branch name
    ap.add_argument("--goal"); ap.add_argument("--goal-file")
    ap.add_argument("--worktree-root")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if not (a.head and a.goal and a.base and a.goal_file):
        ap.error("--head, --goal, --base, --goal-file are required")
    repo_root = a.worktree_root or os.getcwd()
    try:
        result = run_validation(a.head, a.goal, a.base, a.goal_file, repo_root)
    except Exception as e:  # environment/infra failure -> INCONCLUSIVE, never default-PASS
        print(json.dumps({"verdict": "INCONCLUSIVE", "checks": [],
                          "summary": f"environment error: {e}"}, indent=2))
        return 4
    print(json.dumps(result, indent=2))
    return EXIT[result["verdict"]]


if __name__ == "__main__":
    import sys
    sys.exit(main())
