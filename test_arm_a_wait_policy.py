"""Arm A wait policy tests (v14.3.0 — the 2026-09-01 stalled-run forensics).

Placement guards for the rules that keep the gate's background command reachable:
Arm A runs as ONE tracked background task (never detached), "finished" is read from
its output file's sentinel (never the process table — `pgrep -f` matches the probing
shell itself), Arm A's checks are read rather than adjudicated, and the same
liveness rule reaches the parallel-mode reference and the implementer brief.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the subagent
dry-runs recorded in the v14.3.0 release (RED baseline against the v14.2.0 text).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"
BRIEF = "skills/dispatch/references/implementer-brief.md"
PARALLEL = "skills/dispatch/references/parallel-mode.md"
REPORT = "skills/factory-report/SKILL.md"
REPORT_PY = "skills/factory-report/scripts/factory_report.py"
PGV = "skills/dispatch/scripts/pg_validate.py"


def unwrapped(path: str) -> str:
    return " ".join((ROOT / path).read_text().split())


# ---- Arm A is a tracked task ----------------------------------------------------

def test_arm_a_is_one_tracked_background_task_never_detached():
    text = unwrapped(DISPATCH)
    assert "Arm A — the gate commands, started FIRST, as ONE tracked background task" in text
    assert "never `… &`, `nohup`, or `setsid` on Claude Code" in text
    assert "a detached command has no task and no completion notification" in text


def test_arm_a_script_shape_carries_timeouts_and_the_sentinel():
    text = unwrapped(DISPATCH)
    assert "timeout 60m python3 \"$PGVALIDATE\"" in text
    assert 'echo "=== ARM A COMPLETE ==="' in text
    assert "exit 124 = wedged" in text


# ---- finished is read from the file, never the process table --------------------

def test_join_reads_finished_from_the_sentinel_and_bans_process_probes():
    text = unwrapped(DISPATCH)
    assert "FINISHED is read from that file" in text
    for probe in ("`pgrep -f <script>`", "`ps | grep <script>`", "`kill -0`"):
        assert probe in text
    assert "the probing shell's own command line carries the pattern and matches itself" in text


def test_join_names_the_detached_command_recovery():
    text = unwrapped(DISPATCH)
    assert "confirm a tracked task exists for it" in text
    assert "Read the log now, it has probably finished" in text


def test_hard_rules_extend_the_wait_rule_to_background_commands():
    text = unwrapped(DISPATCH)
    assert "A background COMMAND is waited on the same way" in text
    assert "`pgrep -f <pattern>` matches the probing shell's own command line and answers RUNNING forever" in text


# ---- Arm A's checks are read, not adjudicated ---------------------------------

def test_arm_a_checks_are_read_not_adjudicated():
    text = unwrapped(DISPATCH)
    assert "Arm A's checks are read, not adjudicated" in text
    assert "`blast-radius` above all" in text
    assert "gate-defect: <check>" in text
    assert "never a silent override, and never for a check that measures the work" in text


def test_report_line_documents_the_gate_defect_field():
    text = unwrapped(DISPATCH)
    assert "appends `, gate-defect: <check>`" in text


# ---- the rule reaches the lane reference and the brief --------------------------

def test_parallel_mode_scopes_detach_to_droid_and_bans_pgrep_liveness():
    text = unwrapped(PARALLEL)
    assert "Long in-lane commands must be detached, then waited on ONCE — Droid ONLY" in text
    assert "On Claude Code NEVER detach" in text
    assert "never `pgrep -f <script>` as the liveness check" in text


def test_parallel_mode_names_the_primary_checkout_report_path():
    text = unwrapped(PARALLEL)
    assert "resolves the report directory from the PRIMARY checkout" in text


def test_brief_bans_pgrep_liveness_for_implementers():
    text = unwrapped(BRIEF)
    assert "Never test whether a process is still running with `pgrep -f <name>`" in text


# ---- pg_validate resolves the slug from the primary checkout -------------------

def test_pg_validate_report_path_uses_the_primary_checkout():
    text = unwrapped(PGV)
    assert "def _main_checkout_root(repo_root)" in text
    assert "--git-common-dir" in text
    assert "PG_DISPATCH_SLUG" in text


# ---- factory-report carries the fourth signal ----------------------------------

def test_factory_report_documents_the_stalled_signal():
    assert "four execution failure signals (runaway, hung, stalled, oversized)" in unwrapped(REPORT)
    assert "| **Stalled** |" in unwrapped(REPORT)
    assert "def stalled_runs(rows, now)" in unwrapped(REPORT_PY)
