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

TOKEN = "python3 /x/pg_safe_merge.py"
def perm(allow=None, deny=None):
    p = {}
    if allow is not None: p["allow"] = allow
    if deny is not None: p["deny"] = deny
    return {"permissions": p}

def test_permission_found_in_allow():
    s = [("local", perm(allow=[f"Bash({TOKEN}:*)"]))]
    assert dc.find_merge_permission(s, TOKEN) == ("local", None)

def test_permission_absent():
    s = [("project", perm(allow=["Bash(ls:*)"]))]
    assert dc.find_merge_permission(s, TOKEN) == (None, None)

def test_deny_beats_allow():
    s = [("project", perm(allow=[f"Bash({TOKEN}:*)"])), ("user", perm(deny=[f"Bash({TOKEN}:*)"]))]
    allowed, denied = dc.find_merge_permission(s, TOKEN)
    assert denied == "user"

def test_parse_gh_scopes():
    txt = "  - Token scopes: 'repo', 'workflow', 'read:org'\n"
    assert dc.parse_gh_scopes(txt) == ["repo", "workflow", "read:org"]

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

def test_safemerge_token_resolves_to_existing_wrapper():
    # must derive from the plugin INSTALL (this script's siblings), not the target repo —
    # and must point at a real pg_safe_merge.py so the allow-rule matches what dispatch invokes
    tok = dc._safemerge_token()
    assert tok.startswith("python3 "), tok
    path = tok[len("python3 "):]
    assert path.endswith(os.path.join("dispatch", "scripts", "pg_safe_merge.py")), path
    assert os.path.exists(path), f"wrapper path does not exist: {path}"

def test_durable_merge_path_wildcards_version():
    # a versioned plugin-cache path → version segment wildcarded so the allow-rule survives updates
    assert dc._durable_merge_path(
        "/x/.claude/plugins/cache/mp/pg-plugin/2.8.5/skills/dispatch/scripts/pg_safe_merge.py"
    ) == "/x/.claude/plugins/cache/mp/pg-plugin/*/skills/dispatch/scripts/pg_safe_merge.py"
    # Droid plugin-cache path → same wildcarding
    assert dc._durable_merge_path(
        "/x/.factory/plugins/cache/mp/pg-plugin/2.8.5/skills/dispatch/scripts/pg_safe_merge.py"
    ) == "/x/.factory/plugins/cache/mp/pg-plugin/*/skills/dispatch/scripts/pg_safe_merge.py"
    # dev checkout / no version dir → unchanged (literal)
    assert dc._durable_merge_path(
        "/home/u/pg-plugin/skills/dispatch/scripts/pg_safe_merge.py"
    ) == "/home/u/pg-plugin/skills/dispatch/scripts/pg_safe_merge.py"

import tempfile, subprocess, sys, json
def test_settings_sources_checks_both_clis():
    # Both .claude/ and .factory/ settings should be discovered
    with tempfile.TemporaryDirectory() as repo:
        claude_dir = os.path.join(repo, ".claude")
        factory_dir = os.path.join(repo, ".factory")
        os.makedirs(claude_dir); os.makedirs(factory_dir)
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            json.dump({"permissions": {"allow": ["Bash(ls:*)"]}}, f)
        with open(os.path.join(factory_dir, "settings.local.json"), "w") as f:
            json.dump({"permissions": {"allow": ["Bash(git:*)"]}}, f)
        sources = dict(dc._settings_sources(repo))
        assert "local" in sources and "local-droid" in sources
        assert sources["local"].get("permissions", {}).get("allow") == ["Bash(ls:*)"]
        assert sources["local-droid"].get("permissions", {}).get("allow") == ["Bash(git:*)"]
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

def test_state_branch_skip_when_equals_base():
    assert dc.state_branch_check("main", "main", True, False) is None

def test_state_branch_missing():
    r = dc.state_branch_check("goals-state", "main", False, False)
    assert r["name"] == "state-branch" and r["level"] == "WARN"
    assert "missing" in r["detail"] and r["fix"].startswith("FIX:")

def test_state_branch_protected():
    r = dc.state_branch_check("goals-state", "main", True, True)
    assert r["level"] == "BLOCKER" and "protected" in r["detail"]

def test_state_branch_pushable():
    r = dc.state_branch_check("goals-state", "main", True, False)
    assert r["level"] == "INFO" and "pushable" in r["detail"]

def test_validation_gate_skipped_under_pr():
    assert dc.validation_gate_check("pr", "risk_based", True) is None

def test_validation_gate_off_under_auto_warns():
    r = dc.validation_gate_check("auto", "off", True)
    assert r["check"] == "validation-gate" and r["level"] == "WARN" and "off" in r["detail"]

def test_validation_gate_missing_script_warns():
    r = dc.validation_gate_check("auto", "risk_based", False)
    assert r["level"] == "WARN" and "pg_validate" in r["detail"]

def test_validation_gate_wired_info():
    r = dc.validation_gate_check("auto", "required", True)
    assert r["level"] == "INFO" and "required" in r["detail"]

def test_validation_gate_default_mode_treated_as_risk_based():
    r = dc.validation_gate_check("auto", "", True)
    assert r["level"] == "INFO" and "risk_based" in r["detail"]

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

def test_stale_claim_flags_in_progress_no_branch_no_pr():
    goals = {"001-a": {"status": "in_progress"},
             "002-b": {"status": "in_progress", "pr": 12},
             "003-c": {"status": "not_started"}}
    probs = dc.stale_claim_problems(goals, {"001-a": False, "002-b": False, "003-c": False})
    assert any("001-a" in p for p in probs)
    assert not any("002-b" in p for p in probs)   # has a PR → shepherd-able
    assert not any("003-c" in p for p in probs)   # not in_progress

def test_stale_claim_clean_when_branch_present():
    assert dc.stale_claim_problems({"001-a": {"status": "in_progress"}}, {"001-a": True}) == []

def test_runner_emits_valid_json_and_exit_code():
    r = subprocess.run([sys.executable, os.path.join(_here, "doctor_checks.py"), "--merge", "pr"],
                       capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.dirname(os.path.dirname(_here))))
    assert r.returncode in (0, 1, 2), r.stderr
    payload = json.loads(r.stdout)
    assert "checks" in payload and "result" in payload
    assert all({"check", "level"} <= set(c) for c in payload["checks"])

if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns: fn(); print("ok ", fn.__name__)
    print(f"\n{len(fns)} passed")
