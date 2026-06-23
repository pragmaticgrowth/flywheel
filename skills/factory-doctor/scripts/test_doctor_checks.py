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

if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns: fn(); print("ok ", fn.__name__)
    print(f"\n{len(fns)} passed")
