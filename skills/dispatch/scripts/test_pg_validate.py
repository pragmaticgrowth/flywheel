import importlib.util, os
_here = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location("pgv", os.path.join(_here, "pg_validate.py"))
pgv = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pgv)

def _res(name, ok, kind="fixable", evidence=""):
    return {"name": name, "pass": ok, "kind": kind, "evidence": evidence}

def test_aggregate_all_pass():
    assert pgv.aggregate([_res("a", True), _res("b", True)]) == "PASS"

def test_aggregate_fixable_fail():
    r = [_res("a", True), _res("b", False, "fixable")]
    assert pgv.aggregate(r) == "FAIL_FIXABLE"

def test_aggregate_contract_beats_fixable():
    r = [_res("a", False, "fixable"), _res("b", False, "contract")]
    assert pgv.aggregate(r) == "FAIL_CONTRACT"

def test_aggregate_contract_beats_inconclusive():
    r = [_res("a", False, "inconclusive"), _res("b", False, "contract")]
    assert pgv.aggregate(r) == "FAIL_CONTRACT"

def test_aggregate_fixable_beats_inconclusive():
    r = [_res("a", False, "inconclusive"), _res("b", False, "fixable")]
    assert pgv.aggregate(r) == "FAIL_FIXABLE"

def test_aggregate_only_inconclusive():
    assert pgv.aggregate([_res("a", False, "inconclusive")]) == "INCONCLUSIVE"

def test_aggregate_empty_is_pass():
    assert pgv.aggregate([]) == "PASS"

def test_blast_radius_clean():
    r = pgv.blast_radius(["apps/orders/main.go", "apps/orders/orders_test.go"], ["apps/orders/*"])
    assert r["pass"] is True

def test_blast_radius_forbidden_path():
    r = pgv.blast_radius([".claude/settings.json"], [])
    assert r["pass"] is False and r["kind"] == "fixable" and ".claude" in r["evidence"]

def test_blast_radius_workflow_forbidden():
    r = pgv.blast_radius([".github/workflows/ci.yml"], [])
    assert r["pass"] is False

def test_blast_radius_lockfile_flagged():
    r = pgv.blast_radius(["package-lock.json"], [])
    assert r["pass"] is False and "lockfile" in r["evidence"]

def test_blast_radius_lockfile_allowlisted():
    r = pgv.blast_radius(["package-lock.json"], ["package-lock.json"])
    assert r["pass"] is True

def test_blast_radius_outside_declared_surfaces():
    r = pgv.blast_radius(["apps/billing/main.go"], ["apps/orders/*"])
    assert r["pass"] is False and "outside declared surfaces" in r["evidence"]

def test_blast_radius_lenient_when_no_touches():
    # no touches → only forbidden/lockfile fire; an ordinary unrelated file is OK
    r = pgv.blast_radius(["some/other/file.go"], [])
    assert r["pass"] is True

def test_forbidden_content_private_key():
    diff = "+-----BEGIN RSA PRIVATE KEY-----\n+MIIE...\n"
    r = pgv.forbidden_content(diff)
    assert r["pass"] is False and "PRIVATE KEY" in r["evidence"]

def test_forbidden_content_aws_key():
    r = pgv.forbidden_content("+AWS_KEY = AKIAIOSFODNN7EXAMPLE\n")
    assert r["pass"] is False

def test_forbidden_content_slack_token():
    r = pgv.forbidden_content("+tok = xoxb-1234567890-abcdef\n")
    assert r["pass"] is False

def test_forbidden_content_github_pat():
    r = pgv.forbidden_content("+GH = ghp_0123456789abcdefghijklmnopqrstuvwxyz\n")
    assert r["pass"] is False

def test_forbidden_content_benign():
    r = pgv.forbidden_content("+const x = computeThing(input)\n+    return x + 1\n")
    assert r["pass"] is True

def test_forbidden_content_skips_removed_lines():
    # removed lines (-) aren't an introduced secret
    r = pgv.forbidden_content("-OLD = AKIAIOSFODNN7EXAMPLE\n")
    assert r["pass"] is True

def test_risk_flagged_auth_path():
    assert pgv.chore_risk_flagged(["internal/auth/login.go"]) is True

def test_risk_flagged_migration():
    assert pgv.chore_risk_flagged(["db/migrations/0028_up.sql"]) is True

def test_risk_flagged_deps():
    assert pgv.chore_risk_flagged(["go.mod"]) is True

def test_risk_flagged_benign_chore():
    assert pgv.chore_risk_flagged(["internal/util/strings.go"]) is False

def test_risk_flagged_many_files():
    paths = [f"pkg/{i}/x.go" for i in range(13)]
    assert pgv.chore_risk_flagged(paths) is True

def test_in_scope_bug_always():
    assert pgv.in_scope("bug", ["x.go"], "risk_based") is True

def test_in_scope_feature_always():
    assert pgv.in_scope("feature", ["x.go"], "risk_based") is True

def test_in_scope_chore_lowrisk_skipped():
    assert pgv.in_scope("chore", ["internal/util/strings.go"], "risk_based") is False

def test_in_scope_chore_riskflagged_required():
    assert pgv.in_scope("chore", ["internal/auth/x.go"], "risk_based") is True

def test_in_scope_off_skips_all():
    assert pgv.in_scope("bug", ["x.go"], "off") is False

def test_in_scope_required_all_types():
    assert pgv.in_scope("chore", ["x.go"], "required") is True

def test_detect_makefile():
    fm = {"Makefile": "build:\n\tgo build ./...\n"}
    assert pgv.detect_gate_command(fm) == "make test"

def test_detect_go_mod():
    assert pgv.detect_gate_command({"go.mod": "module x\n"}) == "go test ./..."

def test_detect_package_json_test():
    fm = {"package.json": '{"scripts":{"test":"vitest"}}'}
    assert pgv.detect_gate_command(fm) == "npm test"

def test_detect_pytest():
    fm = {"pytest.ini": "[pytest]\n"}
    assert pgv.detect_gate_command(fm) == "pytest -q"

def test_detect_none():
    assert pgv.detect_gate_command({"README.md": "hi"}) is None

def test_detect_makefile_beats_others():
    fm = {"Makefile": "x:\n", "go.mod": "module x"}
    assert pgv.detect_gate_command(fm) == "make test"

def test_repro_red_on_base_green_on_head():
    r = pgv.repro_direction([1, 0], [0, 0], already_correct=False)
    assert r["pass"] is True

def test_repro_all_green_on_base_no_doc():
    r = pgv.repro_direction([0, 0], [0, 0], already_correct=False)
    assert r["pass"] is False and r["kind"] == "contract"

def test_repro_all_green_on_base_with_doc():
    r = pgv.repro_direction([0, 0], [0, 0], already_correct=True)
    assert r["pass"] is True and "already correct" in r["evidence"]

def test_repro_red_on_head():
    r = pgv.repro_direction([1], [1], already_correct=False)
    assert r["pass"] is False and r["kind"] == "fixable"

def test_repro_nothing_red_on_base_red_on_head():
    r = pgv.repro_direction([0, 0], [1, 0], already_correct=False)
    assert r["pass"] is False

def test_repro_overlaid_tests_red_on_base_passes():
    # TDD test added by the PR, overlaid onto base -> red there, green on head: real fix.
    r = pgv.repro_direction([1, 0], [0, 0], already_correct=False,
                            overlaid_tests=["a.test.ts"])
    assert r["pass"] is True and "overlaid" in r["evidence"]

def test_repro_overlaid_tests_still_green_is_contract():
    # The PR's tests were overlaid onto base product code and still passed -> tautology.
    r = pgv.repro_direction([0, 0], [0, 0], already_correct=False,
                            overlaid_tests=["a.test.ts"])
    assert r["pass"] is False and r["kind"] == "contract" and "does not reproduce" in r["evidence"]

def test_repro_no_test_file_contract_message():
    r = pgv.repro_direction([0, 0], [0, 0], already_correct=False, overlaid_tests=[])
    assert r["pass"] is False and "no recognizable test file" in r["evidence"]

def test_is_test_path_patterns():
    assert pgv.is_test_path("apps/marketing/lib/blog/format-date.test.ts")
    assert pgv.is_test_path("src/__tests__/foo.ts")
    assert pgv.is_test_path("pkg/thing_test.go")
    assert pgv.is_test_path("tests/test_api.py")
    assert pgv.is_test_path("api/test_views.py")
    assert not pgv.is_test_path("apps/marketing/lib/blog/format-date.ts")
    assert not pgv.is_test_path("src/components/BlogPostHero.tsx")

def test_acceptance_green_all_pass():
    r = pgv.acceptance_green([0, 0, 0])
    assert r["pass"] is True

def test_acceptance_green_one_red():
    r = pgv.acceptance_green([0, 1, 0])
    assert r["pass"] is False and r["kind"] == "fixable"

def test_acceptance_green_empty_is_inconclusive():
    # no acceptance commands discoverable → can't verify
    r = pgv.acceptance_green([])
    assert r["pass"] is False and r["kind"] == "inconclusive"

def test_integrity_ok():
    r = pgv.one_goal_integrity("goal/007-orders", "Goal: 007-orders\n", "main", "main",
                               ["apps/orders/main.go"], "007-orders")
    assert r["pass"] is True

def test_integrity_wrong_branch():
    r = pgv.one_goal_integrity("feature/x", "Goal: 007-orders", "main", "main", [], "007-orders")
    assert r["pass"] is False and "goal/007-orders" in r["evidence"]

def test_integrity_missing_body_marker():
    r = pgv.one_goal_integrity("goal/007-orders", "no marker", "main", "main", [], "007-orders")
    assert r["pass"] is False

def test_integrity_wrong_base():
    r = pgv.one_goal_integrity("goal/007-orders", "Goal: 007-orders", "dev", "main", [], "007-orders")
    assert r["pass"] is False and "base" in r["evidence"]

def test_integrity_edits_queue():
    r = pgv.one_goal_integrity("goal/007-orders", "Goal: 007-orders", "main", "main",
                               ["docs/goals/index.yaml"], "007-orders")
    assert r["pass"] is False and "docs/goals" in r["evidence"]

import subprocess, sys
def test_self_test_exits_zero_and_announces():
    r = subprocess.run([sys.executable, os.path.join(_here, "pg_validate.py"), "--self-test"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "self-test" in r.stdout and "passed" in r.stdout, r.stdout + r.stderr

import os, subprocess, tempfile, json, sys

def _git_local(d, *a):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True)

def _make_repo(tmp):
    _git_local(tmp, "init", "-q"); _git_local(tmp, "config", "user.email", "t@t"); _git_local(tmp, "config", "user.name", "t")
    return tmp

def test_local_chore_acceptance_green_passes(tmp_path=None):
    d = tempfile.mkdtemp()
    _make_repo(d)
    # base commit
    open(os.path.join(d, "app.py"), "w").write("x = 1\n")
    _git_local(d, "add", "app.py"); _git_local(d, "commit", "-qm", "base")
    base = _git_local(d, "rev-parse", "HEAD").stdout.strip()
    # goal file (chore, acceptance always-green)
    gf = os.path.join(d, "goal.md")
    open(gf, "w").write("---\ntype: chore\nacceptance:\n  - \"true\"\n---\nbody\n")
    # head commit (within declared/empty touches => benign)
    open(os.path.join(d, "app.py"), "w").write("x = 2\n")
    _git_local(d, "add", "app.py"); _git_local(d, "commit", "-qm", "work")
    head = _git_local(d, "rev-parse", "HEAD").stdout.strip()
    script = os.path.join(os.path.dirname(__file__), "pg_validate.py")
    out = subprocess.run([sys.executable, script, "--head", head, "--base", base,
                          "--goal", "001", "--goal-file", gf], capture_output=True, text=True, cwd=d)
    payload = json.loads(out.stdout)
    assert payload["verdict"] == "PASS", payload
    assert payload["sha_head"].startswith(head[:12])
    assert out.returncode == 0

def test_local_bug_repro_direction_pass_and_contract():
    import os, subprocess, tempfile, json, sys
    def g(d,*a): return subprocess.run(["git","-C",d,*a],capture_output=True,text=True)
    d = tempfile.mkdtemp(); g(d,"init","-q"); g(d,"config","user.email","t@t"); g(d,"config","user.name","t")
    open(os.path.join(d,"f.txt"),"w").write("BUG\n"); g(d,"add","f.txt"); g(d,"commit","-qm","base")
    base = g(d,"rev-parse","HEAD").stdout.strip()
    gf = os.path.join(d,"goal.md")
    open(gf,"w").write('---\ntype: bug\nacceptance:\n  - "grep -q FIXED f.txt"\n---\nbody\n')
    open(os.path.join(d,"f.txt"),"w").write("FIXED\n"); g(d,"add","f.txt"); g(d,"commit","-qm","fix")
    head = g(d,"rev-parse","HEAD").stdout.strip()
    s = os.path.join(os.path.dirname(__file__),"pg_validate.py")
    out = subprocess.run([sys.executable,s,"--head",head,"--base",base,"--goal","002","--goal-file",gf],
                         capture_output=True,text=True,cwd=d)
    assert json.loads(out.stdout)["verdict"] == "PASS", out.stdout

if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
