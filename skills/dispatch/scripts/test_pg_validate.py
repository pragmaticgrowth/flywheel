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

if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
