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
    # --skip-verify-run is REQUIRED here: this repo's own config.verify is
    # `python3 -m pytest -q`, so a probe that executes the gate would spawn the whole
    # suite (including this test) recursively.
    r = subprocess.run([sys.executable, os.path.join(_here, "doctor_checks.py"),
                        "--base", "main", "--skip-verify-run"],
                       capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.dirname(os.path.dirname(_here))))
    assert r.returncode in (0, 1, 2), r.stderr
    payload = json.loads(r.stdout)
    assert "checks" in payload and "result" in payload
    assert all({"check", "level"} <= set(c) for c in payload["checks"])
    assert any(c["check"] == "verify-run" for c in payload["checks"]), payload["checks"]

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

def test_limit_resilience_fix_recommends_attended_drain_not_headless():
    # owner decision 2026-07-28: the recommended rail is a window-timed attended drain,
    # never cron/launchd firing headless `claude -p` sessions.
    fix = dc.limit_resilience_check(2, 3, False, False)["fix"]
    assert "--unlimited" in fix and "resets_at" in fix
    assert "claude -p" not in fix and "cron" not in fix

def test_limit_resilience_ok_with_external_scheduler():
    assert dc.limit_resilience_check(2, 3, False, True)["level"] == "INFO"

def test_limit_resilience_ok_with_stopfailure_hook():
    assert dc.limit_resilience_check(2, 3, True, False)["level"] == "INFO"

def test_scheduler_evidence_matches_droid_exec(monkeypatch):
    # a crontab firing fresh droid sessions is limit-proof evidence, same as claude -p.
    # (uses a -f prompt-file form deliberately NOT containing "/dispatch", so only the
    # "droid exec" pattern itself can match)
    monkeypatch.setattr(dc, "_run",
                        lambda cmd: (0, '0 * * * * droid exec -f /etc/goal-prompt.md', ""))
    assert dc._external_scheduler_evidence()

def test_scheduler_evidence_still_ignores_unrelated_crontab(monkeypatch):
    monkeypatch.setattr(dc, "_run", lambda cmd: (0, "0 * * * * /usr/bin/backup.sh", ""))
    monkeypatch.setattr(dc.glob, "glob", lambda g: [])
    assert not dc._external_scheduler_evidence()

def test_scheduler_evidence_bare_dispatch_path_is_not_evidence(monkeypatch):
    # the false positive this tightening fixes: a cron line whose PATH just happens
    # to contain the substring "/dispatch" but never mentions claude or droid at all.
    monkeypatch.setattr(dc, "_run",
                        lambda cmd: (0, "0 3 * * * /opt/app/dispatch/cleanup.sh", ""))
    monkeypatch.setattr(dc.glob, "glob", lambda g: [])
    assert not dc._external_scheduler_evidence()

def test_scheduler_evidence_claude_and_dispatch_same_line_matches_via_regex(tmp_path, monkeypatch):
    # covers the combined regex path specifically — not one of the three exact
    # substrings ("claude -p" / "claude --print" / "droid exec") — a claude-named
    # wrapper script invoking /dispatch on the SAME line is still real evidence.
    unit = tmp_path / "flywheel.plist"
    unit.write_text("ExecStart=/usr/local/bin/claude_wrapper.sh --do /dispatch\n")
    monkeypatch.setattr(dc, "_run", lambda cmd: (1, "", ""))
    monkeypatch.setattr(dc.glob, "glob",
                        lambda g: [str(unit)] if "LaunchAgents" in g else [])
    assert dc._external_scheduler_evidence()

def test_scheduler_evidence_dispatch_and_claude_on_different_lines_does_not_match(tmp_path, monkeypatch):
    # the two mentions must share a line — "/dispatch" on one line and "claude" on a
    # completely unrelated line elsewhere in the same file is not evidence of a rail.
    unit = tmp_path / "other.plist"
    unit.write_text("claude desktop app config\nExecStart=/opt/app/dispatch/run.sh\n")
    monkeypatch.setattr(dc, "_run", lambda cmd: (1, "", ""))
    monkeypatch.setattr(dc.glob, "glob",
                        lambda g: [str(unit)] if "LaunchAgents" in g else [])
    assert not dc._external_scheduler_evidence()

def test_stop_failure_hook_found_in_factory_settings(monkeypatch):
    with tempfile.TemporaryDirectory() as repo:
        proj = os.path.join(repo, ".factory")
        os.makedirs(proj)
        with open(os.path.join(proj, "settings.json"), "w") as f:
            f.write('{"hooks": {"StopFailure": [{"matcher": "rate_limit"}]}}')
        monkeypatch.setenv("HOME", os.path.join(repo, "nohome"))
        assert dc._has_stop_failure_hook(repo)

def test_stop_failure_hook_found_in_user_factory_settings(monkeypatch):
    with tempfile.TemporaryDirectory() as home:
        user = os.path.join(home, ".factory")
        os.makedirs(user)
        with open(os.path.join(user, "settings.json"), "w") as f:
            f.write('{"hooks": {"StopFailure": [{"matcher": "rate_limit"}]}}')
        monkeypatch.setenv("HOME", home)
        with tempfile.TemporaryDirectory() as repo:
            assert dc._has_stop_failure_hook(repo)

def test_symlink_capability_warn_on_windows_without_privilege():
    # Windows default (Developer Mode off, non-elevated): os.symlink raises
    # WinError 1314, so bug-goal base worktrees can't link deps and every type: bug
    # goal gates INCONCLUSIVE. The doctor must surface it with the actionable fix.
    r = dc.symlink_capability_check(can_symlink=False, windows=True)
    assert r["level"] == "WARN"
    assert "bug" in r["detail"]
    assert "Developer Mode" in r["fix"]

def test_symlink_capability_info_when_available_on_windows():
    r = dc.symlink_capability_check(can_symlink=True, windows=True)
    assert r["level"] == "INFO"

def test_symlink_capability_not_reported_on_posix():
    assert dc.symlink_capability_check(can_symlink=True, windows=False) is None

# ---- verify-run: does the DECLARED local gate actually run? (TDD) ----

def test_verify_run_info_when_every_command_exits_zero():
    r = dc.verify_run_check(["npm run build", "npm test"],
                            [("npm run build", 0), ("npm test", 0)])
    assert r["check"] == "verify-run"
    assert r["level"] == "INFO"
    assert "2" in r["detail"]
    assert set(r) == {"check", "level", "detail", "fix"}

def test_verify_run_blocker_when_a_command_fails():
    # the declared gate is red: name the command verbatim + its exit code, and hand
    # back the exact command to reproduce it. REPORT-only — never auto-fixed.
    r = dc.verify_run_check(["npm run build", "npm test"],
                            [("npm run build", 0), ("npm test", 1)])
    assert r["check"] == "verify-run"
    assert r["level"] == "BLOCKER"
    assert "npm test" in r["detail"]
    assert "1" in r["detail"]
    assert "npm test" in r["fix"]

def test_verify_run_blocker_when_a_command_is_unresolvable():
    # exit 127 = shell couldn't resolve it — the classic renamed-script gate rot.
    r = dc.verify_run_check(["pnpm test"], [("pnpm test", 127)])
    assert r["level"] == "BLOCKER"
    assert "pnpm test" in r["detail"]
    assert "127" in r["detail"]
    assert r["fix"]

def test_verify_run_warns_on_timeout_when_nothing_else_failed():
    r = dc.verify_run_check(["npm test"], [("npm test", 124)])
    assert r["level"] == "WARN"
    assert "npm test" in r["detail"]
    assert "124" in r["detail"]

def test_verify_run_blocker_outranks_timeout():
    # a real failure alongside a timeout is still a red gate, not a WARN.
    r = dc.verify_run_check(["a", "b"], [("a", 124), ("b", 2)])
    assert r["level"] == "BLOCKER"
    assert "b" in r["detail"]
    assert "2" in r["detail"]

def test_verify_run_info_when_skipped():
    r = dc.verify_run_check(["npm test"], None, skipped=True)
    assert r["check"] == "verify-run"
    assert r["level"] == "INFO"
    assert "not run" in r["detail"]

def test_verify_run_info_when_no_commands_configured():
    # nothing declared → nothing to execute; the `verify` check owns that WARN.
    r = dc.verify_run_check([], None)
    assert r["check"] == "verify-run"
    assert r["level"] == "INFO"

def test_verify_run_resolve_shell_pg_bash_override_wins():
    p = dc._resolve_shell(environ={"PG_BASH": "/custom/bin/bash"},
                          which=lambda n: "/usr/bin/bash",
                          isfile=lambda q: True, windows=False)
    assert p == "/custom/bin/bash"

def test_verify_run_resolve_shell_posix_returns_full_path():
    p = dc._resolve_shell(environ={}, which=lambda n: "/bin/bash" if n == "bash" else None,
                          isfile=lambda q: True, windows=False)
    assert p == "/bin/bash"

def test_verify_run_resolve_shell_windows_rejects_system32_wsl_stub():
    git_bash = "C:\\Program Files\\Git\\usr\\bin\\bash.exe"
    p = dc._resolve_shell(environ={"SystemRoot": "C:\\Windows", "ProgramFiles": "C:\\Program Files"},
                          which=lambda n: "C:\\Windows\\System32\\bash.exe" if n == "bash" else None,
                          isfile=lambda q: q == git_bash, windows=True)
    assert p == git_bash

def test_verify_run_resolve_shell_none_when_no_posix_shell():
    p = dc._resolve_shell(environ={"SystemRoot": "C:\\Windows"},
                          which=lambda n: None, isfile=lambda q: False, windows=True)
    assert p is None

def test_run_verify_cmds_runs_every_command_without_short_circuiting():
    # a failing first command must NOT hide the rest — the gate's full shape matters.
    with tempfile.TemporaryDirectory() as d:
        assert dc._run_verify_cmds(["exit 3", "exit 0", "exit 1"], d) == [3, 0, 1]

def test_run_verify_cmds_uses_shell_and_repo_root_cwd():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "marker.txt"), "w").close()
        # shell syntax (&&) and cwd both have to work for a real config.verify string
        assert dc._run_verify_cmds(["test -f marker.txt && true"], d) == [0]

def test_run_verify_cmds_reports_127_for_an_unresolvable_command():
    with tempfile.TemporaryDirectory() as d:
        assert dc._run_verify_cmds(["pg-doctor-no-such-command-xyz"], d) == [127]

def test_run_verify_cmds_times_out_to_124(monkeypatch):
    import time as _time
    monkeypatch.setenv("PG_DOCTOR_VERIFY_TIMEOUT", "1")
    with tempfile.TemporaryDirectory() as d:
        t0 = _time.monotonic()
        exits = dc._run_verify_cmds(["sleep 30"], d)
        elapsed = _time.monotonic() - t0
    assert exits == [124], exits
    assert elapsed < 15, f"timeout did not bound the run ({elapsed:.1f}s)"

def test_run_checks_skip_flag_suppresses_execution(monkeypatch):
    calls = []
    monkeypatch.setattr(dc, "_run_verify_cmds", lambda cmds, cwd: calls.append(cmds) or [0])
    checks, _ = dc.run_checks("main", skip_verify_run=True)
    vr = [c for c in checks if c["check"] == "verify-run"]
    assert len(vr) == 1, checks
    assert vr[0]["level"] == "INFO" and "not run" in vr[0]["detail"]
    assert calls == [], calls

def test_run_checks_attempts_no_execution_when_no_commands_configured(monkeypatch, tmp_path):
    # empty config.verify -> INFO and the executor is never reached (an empty command
    # list must not even resolve a shell). The `verify` check owns the missing-gate WARN.
    (tmp_path / "docs" / "goals").mkdir(parents=True)
    (tmp_path / "docs" / "goals" / "index.yaml").write_text(
        "config:\n  base: main\ngoals:\n  001-x: {status: not_started}\n")
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setattr(dc, "_run_verify_cmds", lambda cmds, cwd: calls.append(cmds) or [])
    monkeypatch.setattr(dc, "_run", lambda cmd: (1, "", ""))  # no git repo here
    checks, _ = dc.run_checks("main")
    vr = [c for c in checks if c["check"] == "verify-run"]
    assert len(vr) == 1 and vr[0]["level"] == "INFO", checks
    assert calls == [], calls

def test_run_checks_executes_the_gate_by_default(monkeypatch):
    calls = []

    def fake(cmds, cwd):
        calls.append((cmds, cwd))
        return [0] * len(cmds)

    monkeypatch.setattr(dc, "_run_verify_cmds", fake)
    checks, _ = dc.run_checks("main")
    vr = [c for c in checks if c["check"] == "verify-run"]
    assert len(vr) == 1, checks
    assert vr[0]["level"] == "INFO"
    assert calls, "default run must execute the declared config.verify commands"

if __name__ == "__main__":
    fns = [g for n, g in sorted(globals().items()) if n.startswith("test_")]
    for fn in fns: fn(); print("ok ", fn.__name__)
    print(f"\n{len(fns)} passed")


# --- lane-hygiene (v9 parallel lane model) ---

def test_lane_hygiene_no_lanes_is_info():
    r = dc.lane_hygiene_check([], [], ["001-a"], [])
    assert r["level"] == "INFO" and "no parallel lanes" in r["detail"]

def test_lane_hygiene_consistent_lane_is_info():
    r = dc.lane_hygiene_check(["001-a"], ["001-a"], ["001-a"], ["001-a"])
    assert r["level"] == "INFO" and "consistent" in r["detail"]

def test_lane_hygiene_orphan_branch_warns_with_fix():
    r = dc.lane_hygiene_check(["009-old"], ["009-old"], [], ["009-old"])
    assert r["level"] == "WARN"
    assert "orphan" in r["detail"] and "009-old" in r["detail"]
    assert "git worktree remove" in r["fix"]

def test_lane_hygiene_missing_worktree_named_recreatable():
    r = dc.lane_hygiene_check(["001-a"], [], ["001-a"], [])
    assert r["level"] == "WARN"
    assert "without a registered worktree" in r["detail"] and "recreates" in r["detail"]

def test_lane_hygiene_stray_dir_warns():
    r = dc.lane_hygiene_check([], [], ["001-a"], ["junk-dir"])
    assert r["level"] == "WARN" and "stray" in r["detail"] and "junk-dir" in r["detail"]

# --- event log (v13.0.0+) ------------------------------------------------------

def test_event_log_off_is_info_with_the_opt_in_command():
    r = dc.event_log_check(False, 0, None, None)
    assert r["level"] == "INFO" and "off" in r["detail"]
    assert "mkdir -p ~/.local/state/pg-factory" in r["fix"]

def test_event_log_just_enabled_and_empty_is_not_a_finding():
    # Enabling it 10 minutes ago and seeing nothing yet is expected, not a fault.
    r = dc.event_log_check(True, 0, None, 0.17)
    assert r["level"] == "INFO" and "nothing recorded yet" in r["detail"]

def test_event_log_enabled_long_ago_but_empty_warns_about_the_silent_failure():
    # The whole point of the check: a hook whose path does not resolve fails with no
    # visible error, so an empty log is the only symptom.
    r = dc.event_log_check(True, 0, None, 9.0)
    assert r["level"] == "WARN"
    assert "NOTHING has been recorded" in r["detail"]
    assert "restart" in r["fix"] and "async" in r["fix"]

def test_event_log_stale_events_warn_with_age_in_days():
    # size_bytes replaces the old exact line count (v13.3.0: the probe no longer
    # scans the whole file) — the detail text now carries a human-readable size.
    r = dc.event_log_check(True, 4200, 300.0, 900.0)
    assert r["level"] == "WARN" and "12 days old" in r["detail"]
    assert "KB" in r["detail"] or "logged" in r["detail"]

def test_event_log_healthy_is_info_with_the_size():
    r = dc.event_log_check(True, 4200, 0.3, 900.0)
    assert r["level"] == "INFO" and "logged" in r["detail"] and "just now" in r["detail"]
    assert "4200 events" not in r["detail"]     # the old exact-count phrasing is gone

def test_event_log_probe_never_raises_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    enabled, n, newest, age = dc._event_log_state()
    assert enabled is False and n == 0 and newest is None

# ---- inbox-debt (v13.3.0 — a heavy docs/goals/inbox.md pile-up factory-doctor can see) --

def test_inbox_debt_no_check_when_absent_or_empty():
    assert dc.inbox_debt_check([]) is None

def test_inbox_debt_lines_reads_open_lines_and_leading_dates(tmp_path):
    g = tmp_path / "docs" / "goals"; g.mkdir(parents=True)
    (g / "inbox.md").write_text(
        "# Inbox\n\n"
        "- [ ] 2026-08-01 fix the flaky login test (earn: live-defect)\n"
        "- [x] already triaged\n"
        "- [ ] no leading date on this one\n")
    lines = dc._inbox_debt_lines(str(g))
    assert lines == ["2026-08-01", None]

def test_inbox_debt_lines_empty_when_file_absent(tmp_path):
    assert dc._inbox_debt_lines(str(tmp_path)) == []

def test_inbox_debt_info_for_small_undated_backlog():
    r = dc.inbox_debt_check([None] * 5)
    assert r["level"] == "INFO" and "5 open" in r["detail"]
    assert r["fix"] == ""

def test_inbox_debt_warns_at_count_threshold():
    r = dc.inbox_debt_check([None] * 10)
    assert r["level"] == "WARN" and "10 open" in r["detail"]
    assert "/process-inbox" in r["fix"]

def test_inbox_debt_warns_on_stale_oldest_line_even_under_count_threshold():
    import datetime
    now = datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc)
    r = dc.inbox_debt_check(["2026-08-10", None], now=now)   # 22 days old, only 2 items
    assert r["level"] == "WARN"
    assert "22d old" in r["detail"]

def test_inbox_debt_info_when_dated_but_not_stale_enough():
    import datetime
    now = datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc)
    r = dc.inbox_debt_check(["2026-08-25"], now=now)   # 7 days old, well under 14
    assert r["level"] == "INFO"

def test_inbox_debt_runs_alongside_other_queue_checks(tmp_path, monkeypatch):
    # end-to-end through run_checks: a heavy inbox must surface without needing an
    # index.yaml at all (a repo can pile up an inbox with nothing queued).
    g = tmp_path / "docs" / "goals"; g.mkdir(parents=True)
    (g / "inbox.md").write_text("\n".join(f"- [ ] item {i}" for i in range(12)) + "\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dc, "_run", lambda cmd: (1, "", ""))   # no real git repo here
    checks, _ = dc.run_checks("main", skip_verify_run=True)
    ib = [c for c in checks if c["check"] == "inbox-debt"]
    assert len(ib) == 1 and ib[0]["level"] == "WARN", checks

# ---- event-log jq dependency (v13.3.0 — the "async" diagnosis can never see this) --

def test_event_log_blocker_when_jq_missing_outranks_everything_else():
    # even with plenty of healthy-looking data, a currently-missing jq means the
    # hook has been failing silently since — this must win over the INFO verdict.
    r = dc.event_log_check(True, 4200, 0.3, 900.0, jq_missing=True)
    assert r["level"] == "BLOCKER"
    assert "jq" in r["detail"]
    assert "brew install jq" in r["fix"] and "apt-get install -y jq" in r["fix"]

def test_event_log_blocker_when_jq_missing_outranks_just_enabled_info():
    r = dc.event_log_check(True, 0, None, 0.2, jq_missing=True)
    assert r["level"] == "BLOCKER"

def test_event_log_off_ignores_jq_missing():
    # the on/off switch still wins first — jq status is irrelevant when the log
    # directory doesn't even exist.
    r = dc.event_log_check(False, 0, None, None, jq_missing=True)
    assert r["level"] == "INFO" and "off" in r["detail"]

def test_event_log_jq_present_keeps_old_verdicts_unchanged():
    # default jq_missing=False must reproduce the exact pre-v13.3.0 verdicts —
    # callers that never pass the new kwarg see no behavior change.
    r = dc.event_log_check(True, 0, None, 9.0)
    assert r["level"] == "WARN" and "NOTHING has been recorded" in r["detail"]

def test_jq_missing_true_when_jq_not_on_path(monkeypatch, tmp_path):
    monkeypatch.setattr(dc.shutil, "which", lambda name: None)
    assert dc._jq_missing(str(tmp_path)) is True

def test_jq_missing_true_when_marker_present_even_if_jq_now_found(tmp_path, monkeypatch):
    monkeypatch.setattr(dc.shutil, "which", lambda name: "/usr/bin/jq")
    (tmp_path / "jq-missing").write_text("")
    assert dc._jq_missing(str(tmp_path)) is True

def test_jq_missing_false_when_jq_present_and_no_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(dc.shutil, "which", lambda name: "/usr/bin/jq")
    assert dc._jq_missing(str(tmp_path)) is False

# ---- _event_log_state: tail-only read, no full scan (v13.3.0) -----------------

def test_event_log_state_reads_size_via_stat_not_a_full_scan(tmp_path, monkeypatch):
    d = tmp_path / ".local" / "state" / "pg-factory"
    d.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    log = d / "events.ndjson"
    lines = [f'{{"ts":"2026-08-20T00:00:0{i % 10}Z","ev":"PostToolUse"}}' for i in range(400)]
    log.write_text("\n".join(lines) + "\n")
    enabled, size, newest, age = dc._event_log_state()
    assert enabled is True
    assert size == os.path.getsize(log)         # size comes straight from stat
    assert newest is not None                    # newest timestamp still recovered

def test_event_log_state_finds_newest_line_in_large_file_tail(tmp_path, monkeypatch):
    import datetime as _dt
    d = tmp_path / ".local" / "state" / "pg-factory"
    d.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    log = d / "events.ndjson"
    old_lines = ['{"ts":"2020-01-01T00:00:00Z","ev":"PostToolUse"}'] * 2000  # >> 8KB
    now_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    newest_line = '{"ts":"%s","ev":"Stop"}' % now_ts
    log.write_text("\n".join(old_lines + [newest_line]) + "\n")
    assert os.path.getsize(log) > 8192            # actually exercises the tail-seek path
    enabled, size, newest, age = dc._event_log_state()
    assert enabled is True
    assert newest is not None and newest < 0.1     # newest_line is right now -> ~0h age

def test_event_log_state_ignores_trailing_partial_line(tmp_path, monkeypatch):
    # a write in progress (or the tail seek landing mid-line) must not be parsed as
    # the newest event — fall back to the last COMPLETE line before it.
    import datetime as _dt
    d = tmp_path / ".local" / "state" / "pg-factory"
    d.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    log = d / "events.ndjson"
    now_ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    good_line = '{"ts":"%s","ev":"Stop"}' % now_ts
    padding = "x" * 9000   # push the file past the 8KB tail window
    log.write_text(padding + "\n" + good_line + '\n{"ts":"2026-08-31T99:99:99Z"')  # truncated tail
    enabled, size, newest, age = dc._event_log_state()
    assert enabled is True
    assert newest is not None and newest < 0.1      # recovered from good_line, not the garbage tail
