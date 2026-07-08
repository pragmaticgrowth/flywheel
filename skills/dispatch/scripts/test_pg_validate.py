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

def test_queue_untouched_clean():
    r = pgv.queue_untouched(["apps/orders/main.go", "tests/test_orders.py"])
    assert r["pass"] is True

def test_queue_untouched_edits_queue():
    r = pgv.queue_untouched(["apps/orders/main.go", "docs/goals/index.yaml"])
    assert r["pass"] is False and "docs/goals" in r["evidence"]

def test_blast_radius_test_file_outside_touches_exempt():
    # A TDD test in a split-tree layout (tests/) is EXPECTED outside the product-surface
    # globs and must NOT trip the out-of-scope check — else every correct TDD goal blocks.
    r = pgv.blast_radius(["apps/orders/main.go", "tests/test_orders.py"], ["apps/orders/**"])
    assert r["pass"] is True, r
    # a non-test file outside the surfaces still fails
    r2 = pgv.blast_radius(["apps/billing/main.go"], ["apps/orders/**"])
    assert r2["pass"] is False and "outside declared surfaces" in r2["evidence"]

def test_blast_radius_test_file_still_bound_by_forbidden():
    # exemption is only for the generic out-of-scope check; a test path that is also a
    # forbidden path (a workflow file) still fails.
    r = pgv.blast_radius([".github/workflows/test_ci.yml"], ["apps/orders/**"])
    assert r["pass"] is False

def test_parse_goal_already_correct_from_frontmatter(tmp_path=None):
    d = _tf.mkdtemp(); gf = _os.path.join(d, "goal.md")
    open(gf, "w").write("---\ntype: bug\nalready_correct: true\n---\nbody\n")
    _g, _t, _c, ac = pgv._parse_goal(gf)
    assert ac is True

def test_parse_goal_already_correct_ignores_body_prose():
    # The phrase in the body (even negated) must NOT set the flag — only the frontmatter key.
    d = _tf.mkdtemp(); gf = _os.path.join(d, "goal.md")
    open(gf, "w").write("---\ntype: bug\n---\nThe export was not already correct in edge cases.\n")
    _g, _t, _c, ac = pgv._parse_goal(gf)
    assert ac is False

import tempfile as _tf, os as _os
def test_parse_goal_keeps_items_after_inline_comment():
    # A YAML comment line inside the acceptance: block must not terminate list
    # collection — all commands before/between/after the comment are kept.
    d = _tf.mkdtemp()
    gf = _os.path.join(d, "goal.md")
    open(gf, "w").write(
        "---\n"
        "type: bug\n"
        "acceptance:\n"
        "  - \"cmd-one\"\n"
        "  # this is a YAML comment, not a terminator\n"
        "  - \"cmd-two\"\n"
        "  # trailing comment\n"
        "  - \"cmd-three\"\n"
        "---\nbody\n")
    gtype, touches, cmds, ac = pgv._parse_goal(gf)
    assert cmds == ["cmd-one", "cmd-two", "cmd-three"], cmds

def test_parse_goal_keeps_touches_after_inline_comment():
    d = _tf.mkdtemp()
    gf = _os.path.join(d, "goal.md")
    open(gf, "w").write(
        "---\n"
        "type: chore\n"
        "touches:\n"
        "  - \"apps/a/*\"\n"
        "  # comment between surfaces\n"
        "  - \"apps/b/*\"\n"
        "---\nbody\n")
    gtype, touches, cmds, ac = pgv._parse_goal(gf)
    assert touches == ["apps/a/*", "apps/b/*"], touches

def test_run_validation_bug_inconclusive_when_base_worktree_fails(monkeypatch=None):
    # FIX 1: if `git worktree add` for the repro-direction base checkout fails, the
    # bug path must return INCONCLUSIVE (never run acceptance, never default-PASS).
    import os as _o, subprocess as _sp, tempfile as _t, json as _j, sys as _s
    def g(d, *a): return _sp.run(["git", "-C", d, *a], capture_output=True, text=True)
    d = _t.mkdtemp(); g(d, "init", "-q"); g(d, "config", "user.email", "t@t"); g(d, "config", "user.name", "t")
    open(_o.path.join(d, "f.txt"), "w").write("BUG\n"); g(d, "add", "f.txt"); g(d, "commit", "-qm", "base")
    base = g(d, "rev-parse", "HEAD").stdout.strip()
    gf = _o.path.join(d, "goal.md")
    open(gf, "w").write('---\ntype: bug\nacceptance:\n  - "grep -q FIXED f.txt"\n---\nbody\n')
    open(_o.path.join(d, "f.txt"), "w").write("FIXED\n"); g(d, "add", "f.txt"); g(d, "commit", "-qm", "fix")
    head = g(d, "rev-parse", "HEAD").stdout.strip()
    # Force `git worktree add` to fail by stubbing pgv._git for that subcommand only.
    real_git = pgv._git
    def fake_git(args, **kw):
        if args[:2] == ["worktree", "add"]:
            return (1, "", "fatal: could not create work tree dir (simulated)")
        return real_git(args, **kw)
    pgv._git = fake_git
    try:
        cwd0 = _o.getcwd(); _o.chdir(d)
        try:
            res = pgv.run_validation(head, "002", base, gf, d)
        finally:
            _o.chdir(cwd0)
    finally:
        pgv._git = real_git
    assert res["verdict"] == "INCONCLUSIVE", res
    assert any("base worktree" in c.get("evidence", "") for c in res["checks"]), res
    # never a PASS when the base worktree can't be populated
    assert res["verdict"] != "PASS"

def test_resolve_shell_pg_bash_override_wins():
    # Operator override beats every probe — even on Windows, even if which() disagrees.
    p = pgv._resolve_shell(environ={"PG_BASH": "/custom/bin/bash"},
                           which=lambda n: "/usr/bin/bash",
                           isfile=lambda q: True, windows=False)
    assert p == "/custom/bin/bash"

def test_resolve_shell_posix_returns_which_full_path():
    p = pgv._resolve_shell(environ={}, which=lambda n: "/bin/bash" if n == "bash" else None,
                           isfile=lambda q: True, windows=False)
    assert p == "/bin/bash"

def test_resolve_shell_windows_keeps_git_bash_from_path():
    # PATH holds Git Bash (shutil.which honors PATH order); the resolver must return it
    # as a FULL path — a bare-name argv would let CreateProcess pick System32's WSL stub.
    env = {"SystemRoot": "C:\\Windows"}
    p = pgv._resolve_shell(environ=env,
                           which=lambda n: "C:\\Program Files\\Git\\usr\\bin\\bash.exe" if n == "bash" else None,
                           isfile=lambda q: True, windows=True)
    assert p == "C:\\Program Files\\Git\\usr\\bin\\bash.exe"

def test_resolve_shell_windows_rejects_system32_wsl_stub():
    # When PATH itself resolves bash to the WSL launcher under SystemRoot, skip it and
    # probe the standard Git-for-Windows install locations (built from env vars).
    git_bash = "C:\\Program Files\\Git\\usr\\bin\\bash.exe"
    env = {"SystemRoot": "C:\\Windows", "ProgramFiles": "C:\\Program Files"}
    p = pgv._resolve_shell(environ=env,
                           which=lambda n: "C:\\Windows\\System32\\bash.exe" if n == "bash" else None,
                           isfile=lambda q: q == git_bash, windows=True)
    assert p == git_bash

def test_resolve_shell_windows_system_root_case_insensitive():
    # Windows paths are case-insensitive; c:\windows\system32 must still be rejected.
    git_bash = "C:\\Program Files\\Git\\bin\\bash.exe"
    env = {"SystemRoot": "C:\\Windows", "ProgramFiles": "C:\\Program Files"}
    p = pgv._resolve_shell(environ=env,
                           which=lambda n: "c:\\windows\\system32\\bash.exe" if n == "bash" else None,
                           isfile=lambda q: q == git_bash, windows=True)
    assert p == git_bash

def test_resolve_shell_windows_falls_back_to_sh():
    # No usable bash anywhere, but an MSYS sh outside SystemRoot is on PATH -> use it.
    env = {"SystemRoot": "C:\\Windows"}
    p = pgv._resolve_shell(environ=env,
                           which=lambda n: "C:\\msys64\\usr\\bin\\sh.exe" if n == "sh" else None,
                           isfile=lambda q: False, windows=True)
    assert p == "C:\\msys64\\usr\\bin\\sh.exe"

def test_resolve_shell_none_when_no_posix_shell():
    # Nothing found -> None; _run_cmds then uses the platform default shell.
    p = pgv._resolve_shell(environ={"SystemRoot": "C:\\Windows"},
                           which=lambda n: None, isfile=lambda q: False, windows=True)
    assert p is None

def test_local_run_cmds_timeout_reds_instead_of_hanging():
    # A hung acceptance command must red the gate (exit 124) within the bounded
    # timeout, never lock it indefinitely.
    import os as _o, tempfile as _t, time as _time
    d = _t.mkdtemp()
    _o.environ["PG_VALIDATE_TIMEOUT"] = "1"
    try:
        t0 = _time.monotonic()
        exits = pgv._run_cmds(["sleep 30"], d)
        elapsed = _time.monotonic() - t0
    finally:
        del _o.environ["PG_VALIDATE_TIMEOUT"]
    assert exits == [124], exits
    assert elapsed < 15, f"timeout did not bound the run ({elapsed:.1f}s)"

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
    s = os.path.join(os.path.dirname(__file__),"pg_validate.py")
    # --- PASS direction: red on base (BUG), green on head (FIXED) -> real fix.
    d = tempfile.mkdtemp(); g(d,"init","-q"); g(d,"config","user.email","t@t"); g(d,"config","user.name","t")
    open(os.path.join(d,"f.txt"),"w").write("BUG\n"); g(d,"add","f.txt"); g(d,"commit","-qm","base")
    base = g(d,"rev-parse","HEAD").stdout.strip()
    gf = os.path.join(d,"goal.md")
    open(gf,"w").write('---\ntype: bug\nacceptance:\n  - "grep -q FIXED f.txt"\n---\nbody\n')
    open(os.path.join(d,"f.txt"),"w").write("FIXED\n"); g(d,"add","f.txt"); g(d,"commit","-qm","fix")
    head = g(d,"rev-parse","HEAD").stdout.strip()
    out = subprocess.run([sys.executable,s,"--head",head,"--base",base,"--goal","002","--goal-file",gf],
                         capture_output=True,text=True,cwd=d)
    assert json.loads(out.stdout)["verdict"] == "PASS", out.stdout
    # --- FAIL_CONTRACT direction: already green on base (nothing red to fix), trivial head.
    d2 = tempfile.mkdtemp(); g(d2,"init","-q"); g(d2,"config","user.email","t@t"); g(d2,"config","user.name","t")
    open(os.path.join(d2,"f.txt"),"w").write("FIXED\n"); g(d2,"add","f.txt"); g(d2,"commit","-qm","base")
    base2 = g(d2,"rev-parse","HEAD").stdout.strip()
    gf2 = os.path.join(d2,"goal.md")
    open(gf2,"w").write('---\ntype: bug\nacceptance:\n  - "grep -q FIXED f.txt"\n---\nbody\n')
    open(os.path.join(d2,"other.txt"),"w").write("noop\n"); g(d2,"add","other.txt"); g(d2,"commit","-qm","noop")
    head2 = g(d2,"rev-parse","HEAD").stdout.strip()
    out2 = subprocess.run([sys.executable,s,"--head",head2,"--base",base2,"--goal","003","--goal-file",gf2],
                          capture_output=True,text=True,cwd=d2)
    assert json.loads(out2.stdout)["verdict"] == "FAIL_CONTRACT", out2.stdout

def test_local_unresolved_ref_is_inconclusive():
    import os, subprocess, tempfile, json, sys
    def g(d,*a): return subprocess.run(["git","-C",d,*a],capture_output=True,text=True)
    d = tempfile.mkdtemp(); g(d,"init","-q"); g(d,"config","user.email","t@t"); g(d,"config","user.name","t")
    open(os.path.join(d,"f.txt"),"w").write("x\n"); g(d,"add","f.txt"); g(d,"commit","-qm","base")
    base = g(d,"rev-parse","HEAD").stdout.strip()
    gf = os.path.join(d,"goal.md")
    open(gf,"w").write('---\ntype: chore\nacceptance:\n  - "true"\n---\nbody\n')
    s = os.path.join(os.path.dirname(__file__),"pg_validate.py")
    # bogus head ref must fail loud, never silently pass with an empty SHA
    out = subprocess.run([sys.executable,s,"--head","does-not-exist","--base",base,
                          "--goal","004","--goal-file",gf], capture_output=True,text=True,cwd=d)
    payload = json.loads(out.stdout)
    assert payload["verdict"] == "INCONCLUSIVE", out.stdout
    assert "could not resolve" in payload["summary"], out.stdout
    assert out.returncode == 4, out.returncode

def test_local_bug_repro_inconclusive_on_env_red_base():
    # A test-runner bug goal whose base run reds for an ENVIRONMENT reason (a gitignored
    # artifact present only in the live checkout, absent from the fresh base worktree) must
    # be INCONCLUSIVE, never a forged PASS. The bare-base control catches it.
    import os, subprocess, tempfile, json, sys
    def g(d,*a): return subprocess.run(["git","-C",d,*a],capture_output=True,text=True)
    d = tempfile.mkdtemp(); g(d,"init","-q"); g(d,"config","user.email","t@t"); g(d,"config","user.name","t")
    open(os.path.join(d,".gitignore"),"w").write("generated.bin\n")
    open(os.path.join(d,"runner.sh"),"w").write("test -f generated.bin\n")  # needs a gitignored artifact
    gf = os.path.join(d,"goal.md")
    open(gf,"w").write('---\ntype: bug\nacceptance:\n  - "bash runner.sh"\n---\nbody\n')
    g(d,"add",".gitignore","runner.sh"); g(d,"commit","-qm","base")
    base = g(d,"rev-parse","HEAD").stdout.strip()
    open(os.path.join(d,"new.test.sh"),"w").write("true\n")  # head adds a test file -> overlay/control path
    g(d,"add","new.test.sh"); g(d,"commit","-qm","add test")
    head = g(d,"rev-parse","HEAD").stdout.strip()
    open(os.path.join(d,"generated.bin"),"w").write("x\n")  # present only in the live checkout (untracked)
    s = os.path.join(os.path.dirname(__file__),"pg_validate.py")
    out = subprocess.run([sys.executable,s,"--head",head,"--base",base,"--goal","010","--goal-file",gf],
                         capture_output=True,text=True,cwd=d)
    payload = json.loads(out.stdout)
    assert payload["verdict"] == "INCONCLUSIVE", out.stdout
    assert out.returncode == 4, out.returncode


def test_local_bug_repro_pass_with_control():
    # Genuine repro with a separate proving test: bare base is green (no test yet), the
    # overlaid test reds base product code, head is green -> PASS (control does not block).
    import os, subprocess, tempfile, json, sys
    def g(d,*a): return subprocess.run(["git","-C",d,*a],capture_output=True,text=True)
    d = tempfile.mkdtemp(); g(d,"init","-q"); g(d,"config","user.email","t@t"); g(d,"config","user.name","t")
    # runner executes any *.test.sh present; green (exit 0) when none exist (the bare base).
    open(os.path.join(d,"run-tests.sh"),"w").write(
        'for t in *.test.sh; do [ -e "$t" ] || continue; bash "$t" || exit 1; done\nexit 0\n')
    open(os.path.join(d,"product.txt"),"w").write("BUG\n")
    gf = os.path.join(d,"goal.md")
    open(gf,"w").write('---\ntype: bug\nacceptance:\n  - "bash run-tests.sh"\n---\nbody\n')
    g(d,"add","run-tests.sh","product.txt"); g(d,"commit","-qm","base")
    base = g(d,"rev-parse","HEAD").stdout.strip()
    open(os.path.join(d,"check.test.sh"),"w").write("grep -q FIXED product.txt\n")  # proving test (added by fix)
    open(os.path.join(d,"product.txt"),"w").write("FIXED\n")
    g(d,"add","check.test.sh","product.txt"); g(d,"commit","-qm","fix + test")
    head = g(d,"rev-parse","HEAD").stdout.strip()
    s = os.path.join(os.path.dirname(__file__),"pg_validate.py")
    out = subprocess.run([sys.executable,s,"--head",head,"--base",base,"--goal","011","--goal-file",gf],
                         capture_output=True,text=True,cwd=d)
    assert json.loads(out.stdout)["verdict"] == "PASS", out.stdout


def test_local_bug_repro_symlink_preserves_live_deps():
    # The base run shares the live checkout's dep dir via symlink; removing the worktree must
    # NOT delete the live dir (we unlink the symlink, never the target).
    import os, subprocess, tempfile, json, sys
    def g(d,*a): return subprocess.run(["git","-C",d,*a],capture_output=True,text=True)
    d = tempfile.mkdtemp(); g(d,"init","-q"); g(d,"config","user.email","t@t"); g(d,"config","user.name","t")
    open(os.path.join(d,".gitignore"),"w").write("node_modules/\n")
    open(os.path.join(d,"run-tests.sh"),"w").write(
        'for t in *.test.sh; do [ -e "$t" ] || continue; bash "$t" || exit 1; done\nexit 0\n')
    open(os.path.join(d,"product.txt"),"w").write("BUG\n")
    gf = os.path.join(d,"goal.md")
    open(gf,"w").write('---\ntype: bug\nacceptance:\n  - "bash run-tests.sh"\n---\nbody\n')
    g(d,"add",".gitignore","run-tests.sh","product.txt"); g(d,"commit","-qm","base")
    base = g(d,"rev-parse","HEAD").stdout.strip()
    # proving test exercises the symlinked dep dir before checking the fix
    open(os.path.join(d,"check.test.sh"),"w").write("test -f node_modules/marker && grep -q FIXED product.txt\n")
    open(os.path.join(d,"product.txt"),"w").write("FIXED\n")
    g(d,"add","check.test.sh","product.txt"); g(d,"commit","-qm","fix + test")
    head = g(d,"rev-parse","HEAD").stdout.strip()
    os.makedirs(os.path.join(d,"node_modules"))  # live (gitignored) dep dir
    marker = os.path.join(d,"node_modules","marker"); open(marker,"w").write("dep\n")
    s = os.path.join(os.path.dirname(__file__),"pg_validate.py")
    out = subprocess.run([sys.executable,s,"--head",head,"--base",base,"--goal","012","--goal-file",gf],
                         capture_output=True,text=True,cwd=d)
    assert json.loads(out.stdout)["verdict"] == "PASS", out.stdout
    assert os.path.exists(marker), "live node_modules/marker was destroyed by worktree cleanup"


if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
