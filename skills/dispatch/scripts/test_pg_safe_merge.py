import importlib.util, os
_here = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location("psm", os.path.join(_here, "pg_safe_merge.py"))
psm = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(psm)

def good_pr():
    return {
        "headRefName": "goal/007-orders",
        "baseRefName": "staging",
        "body": "Goal: 007-orders\n\nPlain-language summary.\n",
        "statusCheckRollup": [{"name": "ci", "conclusion": "SUCCESS"}],
        "mergeStateStatus": "CLEAN",
        "files": [{"path": "apps/product/src/orders.ts"}],
        "headRefOid": "abc123",
    }

def v(pr, **kw):
    args = dict(goal="007-orders", base="staging", expected_head="abc123",
                expected_base="base000", current_base_sha="base000")
    args.update(kw)
    return psm.verify_pr(pr, **args)

def test_good_pr_passes():
    ok, reasons = v(good_pr())
    assert ok, reasons

def test_wrong_branch_refused():
    pr = good_pr(); pr["headRefName"] = "feature/x"
    ok, reasons = v(pr); assert not ok and any("goal/007-orders" in r for r in reasons)

def test_missing_body_marker_refused():
    pr = good_pr(); pr["body"] = "no marker here"
    ok, reasons = v(pr); assert not ok and any("Goal: 007-orders" in r for r in reasons)

def test_wrong_base_refused():
    pr = good_pr(); pr["baseRefName"] = "main"
    ok, reasons = v(pr); assert not ok and any("base" in r.lower() for r in reasons)

def test_red_check_refused():
    pr = good_pr(); pr["statusCheckRollup"] = [{"name": "ci", "conclusion": "FAILURE"}]
    ok, reasons = v(pr); assert not ok and any("ci" in r for r in reasons)

def test_blocked_merge_state_refused():
    pr = good_pr(); pr["mergeStateStatus"] = "BLOCKED"
    ok, reasons = v(pr); assert not ok and any("BLOCKED" in r for r in reasons)

def test_queue_edit_refused():
    pr = good_pr(); pr["files"] = [{"path": "docs/goals/007-orders.md"}]
    ok, reasons = v(pr); assert not ok and any("docs/goals/" in r for r in reasons)

def test_head_drift_refused():
    pr = good_pr(); pr["headRefOid"] = "deadbeef"
    ok, reasons = v(pr); assert not ok and any("head SHA" in r for r in reasons)

def test_base_moved_refused():
    ok, reasons = v(good_pr(), current_base_sha="moved999")
    assert not ok and any("base moved" in r for r in reasons)

if __name__ == "__main__":
    import sys
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
