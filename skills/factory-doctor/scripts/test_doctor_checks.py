import importlib.util, os
_here = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location("dc", os.path.join(_here, "doctor_checks.py"))
dc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(dc)

def test_version_ge():
    assert dc.version_ge("2.40.0", "2.40")
    assert dc.version_ge("2.40", "2.40.0")        # equal after padding
    assert dc.version_ge("2.50.1", "2.40.0")
    assert not dc.version_ge("2.39.0", "2.40.0")
    assert dc.version_ge("gh version 2.62.0 (2024)", "2.40")  # tolerates prose

def test_validate_queue_ok():
    obj = {"goals": {"001-a": {"status": "not_started"},
                     "002-b": {"status": "not_started", "depends_on": ["001-a"]}}}
    ok, probs = dc.validate_queue(obj); assert ok, probs

def test_validate_queue_dangling_dep():
    obj = {"goals": {"002-b": {"status": "not_started", "depends_on": ["001-missing"]}}}
    ok, probs = dc.validate_queue(obj)
    assert not ok and any("001-missing" in p for p in probs)

def test_validate_queue_status_required():
    obj = {"goals": {"001-a": {"priority": "high"}}}
    ok, probs = dc.validate_queue(obj)
    assert not ok and any("status" in p for p in probs)

import tempfile, subprocess, sys, json
def test_detect_frontend_react():
    with tempfile.TemporaryDirectory() as repo:
        with open(os.path.join(repo, "package.json"), "w") as f:
            json.dump({"dependencies": {"react": "^18", "react-dom": "^18"}}, f)
        assert dc.detect_frontend(repo) is True

def test_detect_frontend_next():
    with tempfile.TemporaryDirectory() as repo:
        with open(os.path.join(repo, "package.json"), "w") as f:
            json.dump({"dependencies": {"next": "14"}}, f)
        assert dc.detect_frontend(repo) is True

def test_detect_frontend_backend_only():
    with tempfile.TemporaryDirectory() as repo:
        with open(os.path.join(repo, "package.json"), "w") as f:
            json.dump({"dependencies": {"express": "^4"}}, f)
        assert dc.detect_frontend(repo) is False

def test_detect_frontend_monorepo_child():
    with tempfile.TemporaryDirectory() as repo:
        os.makedirs(os.path.join(repo, "frontend"))
        with open(os.path.join(repo, "frontend", "package.json"), "w") as f:
            json.dump({"dependencies": {"vue": "^3"}}, f)
        assert dc.detect_frontend(repo) is True

def test_detect_frontend_none():
    with tempfile.TemporaryDirectory() as repo:
        assert dc.detect_frontend(repo) is False

def test_goals_reference_browser_true():
    with tempfile.TemporaryDirectory() as repo:
        g = os.path.join(repo, "docs", "goals"); os.makedirs(g)
        with open(os.path.join(g, "033-screen.md"), "w") as f:
            f.write("---\nid: 033\nskills: [agent-browser]\n---\nbody")
        assert dc.goals_reference_browser(repo) is True

def test_goals_reference_browser_false():
    with tempfile.TemporaryDirectory() as repo:
        g = os.path.join(repo, "docs", "goals"); os.makedirs(g)
        with open(os.path.join(g, "001-api.md"), "w") as f:
            f.write("---\nid: 001\nskills: []\n---\nbody")
        assert dc.goals_reference_browser(repo) is False

def test_has_checkable_done_acceptance():
    assert dc._has_checkable_done("## Acceptance criteria\n- [ ] make test passes\n") is True

def test_has_checkable_done_goal_contract():
    assert dc._has_checkable_done("## Goal contract\n/goal do X verified by Y\n") is True

def test_has_checkable_done_empty_acceptance_section():
    assert dc._has_checkable_done("## Acceptance criteria\n\n## Out of scope\n- nope\n") is False

def test_has_checkable_done_prose_only():
    assert dc._has_checkable_done("## Outcome\nsome prose only, no checks") is False

def test_goal_contract_problems_flags_active_underspecified_only():
    goals = [{"id": "001-a", "status": "not_started", "checkable": False},
             {"id": "002-b", "status": "in_progress", "checkable": True},
             {"id": "003-c", "status": "completed", "checkable": False}]
    probs = dc.goal_contract_problems(goals)
    assert any("001-a" in p for p in probs)
    assert not any("002-b" in p for p in probs)   # checkable
    assert not any("003-c" in p for p in probs)   # completed, not active

def test_stale_claim_flags_claimed_with_no_work_after():
    # v4: an in_progress goal whose claim commit exists but has NO non-chore(goals)
    # commit after it on the current branch is a stale claim / silent-death candidate.
    goals = {"001-a": {"status": "in_progress"},
             "003-c": {"status": "not_started"}}
    claim_info = {"001-a": {"claim_found": True, "work_after": False}}
    probs = dc.stale_claim_problems(goals, claim_info)
    assert any("001-a" in p for p in probs)
    assert not any("003-c" in p for p in probs)   # not in_progress

def test_stale_claim_clean_when_work_commits_after_claim():
    # v4: a healthy in_progress goal that HAS work commits after its claim is NOT stale.
    goals = {"001-a": {"status": "in_progress"}}
    claim_info = {"001-a": {"claim_found": True, "work_after": True}}
    assert dc.stale_claim_problems(goals, claim_info) == []

def test_stale_claim_info_when_claim_commit_not_found():
    # v4: if the claim commit can't be located, treat as cannot-determine (INFO),
    # NOT a stale WARN.
    goals = {"001-a": {"status": "in_progress"}}
    claim_info = {"001-a": {"claim_found": False, "work_after": False}}
    assert dc.stale_claim_problems(goals, claim_info) == []

def test_runner_emits_valid_json_and_exit_code():
    r = subprocess.run([sys.executable, os.path.join(_here, "doctor_checks.py"), "--base", "main"],
                       capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.dirname(os.path.dirname(_here))))
    assert r.returncode in (0, 1, 2), r.stderr
    payload = json.loads(r.stdout)
    assert "checks" in payload and "result" in payload
    assert all({"check", "level"} <= set(c) for c in payload["checks"])

# ---- new local-gate check helpers (TDD) ----

def test_verify_warns_when_absent():
    assert dc.verify_check([], active_goals=2)["level"] == "WARN"

def test_verify_info_when_present():
    r = dc.verify_check(["npm run build", "npm test"], active_goals=2)
    assert r["level"] == "INFO"

def test_working_tree_warn_when_dirty():
    assert dc.working_tree_check(" M file.py\n")["level"] == "WARN"

def test_working_tree_info_when_clean():
    assert dc.working_tree_check("")["level"] == "INFO"

def test_working_branch_info_when_on_base():
    # on config.base is the healthy steady state — dispatch commits there.
    assert dc.working_branch_check("main", "main")["level"] == "INFO"

def test_working_branch_warn_when_off_base():
    # off config.base is the real problem — dispatch hard-STOPS.
    r = dc.working_branch_check("staging", "main")
    assert r["level"] == "WARN" and "checkout main" in r["fix"]

def test_working_branch_info_when_no_explicit_base():
    # no config.base → dispatch defaults base to the checked-out branch, nothing to flag.
    assert dc.working_branch_check("feature/x", None)["level"] == "INFO"

def test_config_drift_warns_on_v3_keys():
    r = dc.config_drift_check({"base": "main", "model": "inherit", "merge": "auto",
                              "wip": 2, "execution": "herdr", "autonomy": "balanced"})
    assert r["level"] == "WARN"
    for k in ("merge", "wip", "execution", "autonomy"):
        assert k in r["detail"]
    assert r["fix"].startswith("FIX:")

def test_config_drift_info_when_clean():
    r = dc.config_drift_check({"base": "main", "model": "inherit", "skills": [], "verify": ["npm test"]})
    assert r["level"] == "INFO"
    assert r["fix"] == ""

def test_config_drift_lists_only_present_keys():
    r = dc.config_drift_check({"base": "main", "wip": 2})
    assert r["level"] == "WARN"
    assert "wip" in r["detail"]
    assert "merge" not in r["detail"]

def test_limit_resilience_not_applicable_without_active_goals():
    # nothing queued → nothing an outage could stall; never warn.
    assert dc.limit_resilience_check(0, 5, False, False)["level"] == "INFO"

def test_limit_resilience_info_before_first_loop():
    # active goals but no heartbeat log = no loop has ever fired here — guidance only,
    # a WARN would nag every attended repo that never runs unattended.
    r = dc.limit_resilience_check(2, 0, False, False)
    assert r["level"] == "INFO"

def test_limit_resilience_warn_when_looping_unprotected():
    # a loop demonstrably fires on this repo (heartbeat lines exist) and nothing survives
    # a usage-limit stop: no external scheduler, no StopFailure signal → WARN with fix.
    r = dc.limit_resilience_check(2, 3, False, False)
    assert r["level"] == "WARN"
    assert "usage-limit" in r["detail"]
    assert r["fix"]

def test_limit_resilience_ok_with_external_scheduler():
    assert dc.limit_resilience_check(2, 3, False, True)["level"] == "INFO"

def test_limit_resilience_ok_with_stopfailure_hook():
    assert dc.limit_resilience_check(2, 3, True, False)["level"] == "INFO"

if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns: fn(); print("ok ", fn.__name__)
    print(f"\n{len(fns)} passed")
