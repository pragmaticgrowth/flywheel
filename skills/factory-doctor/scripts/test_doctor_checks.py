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
    # dev checkout / no version dir → unchanged (literal)
    assert dc._durable_merge_path(
        "/home/u/pg-plugin/skills/dispatch/scripts/pg_safe_merge.py"
    ) == "/home/u/pg-plugin/skills/dispatch/scripts/pg_safe_merge.py"

import subprocess, sys, json
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
