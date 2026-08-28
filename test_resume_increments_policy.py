"""Resume-from-increments policy tests (goal 009).

DEATH NEEDS EVIDENCE (v11.6.0) detects a dead implementer but nothing recovered
the work already committed: the committing-working-increments mandate means a
worker that dies mid-sitting has usually landed commits, yet Phase 1's
work-commits-present path gated whatever it found and a FAIL ended in
`git reset --hard <gate_base>` — destroying landed increments — and the
escalation ladder had no rung keyed to a missing `STATUS:` block (verified
2026-08-28, provenance inbox-drain). After this goal: a returned implementer
with no `STATUS:` block triggers the resume-from-increments rung — read
`gate_base..HEAD`, re-brief ONE fresh worker with what already landed — and
Phase 1's work-commits-present path routes there instead of gate-then-reset.
Goal 004's report-file gate is untouched: its check runs only once a
`STATUS: DONE` (or a regenerated stub) exists.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the
orchestrator's gate reviewer.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"
ESCALATION = "skills/dispatch/references/escalation-and-repair.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped_text(text: str) -> str:
    return " ".join(text.split())


def phase1_work_commits_step() -> str:
    """Phase 1 bullet 1 (work commits present) up to bullet 2 (no work commits)."""
    text = read(DISPATCH)
    start = text.index("1. **Work commits present")
    end = text.index("2. **No work commits", start)
    span = text[start:end]
    assert 5 <= span.count("\n") <= 40, (
        f"work-commits step span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


def ladder() -> str:
    """The escalation ladder section (to end of file)."""
    text = read(ESCALATION)
    span = text[text.index("## Escalation ladder"):]
    assert 15 <= span.count("\n") <= 70, (
        f"ladder span is {span.count(chr(10))} lines"
    )
    return unwrapped_text(span)


# ---- escalation ladder: the resume-from-increments rung -----------------------

def test_ladder_names_a_resume_from_increments_rung():
    span = ladder()
    assert "resume from increments" in span
    assert "4. **No `STATUS:` block — resume from increments.**" in span


def test_missing_status_block_on_a_returned_implementer_is_a_trigger():
    span = ladder()
    assert (
        "A missing `STATUS:` block on a returned implementer is itself a trigger"
        in span
    )
    assert "EVEN when work commits exist" in span


def test_rung_reads_gate_base_to_head_log_and_diff():
    span = ladder()
    assert "read `gate_base..HEAD`" in span
    assert "git log gate_base..HEAD" in span
    assert "plus the diff" in span


def test_rung_rebriefs_one_fresh_worker_with_what_already_landed():
    span = ladder()
    assert "re-brief ONE fresh worker" in span
    assert "what already landed" in span
    assert "`Landed so far`" in span


def test_rung_is_not_a_same_model_unchanged_respawn():
    span = ladder()
    assert "not a same-model-unchanged respawn" in span


def test_rung_never_gates_then_resets_landed_increments():
    span = ladder()
    assert "gate-then-reset" in span
    assert "destroys landed increments" in span


# ---- dispatch Phase 1: the work-commits-present path --------------------------

def test_phase1_no_status_block_resumes_from_increments():
    span = phase1_work_commits_step()
    assert (
        "No `STATUS:` block at all → resume from increments, never gate-then-reset"
        in span
    )


def test_phase1_resume_precedes_the_gate():
    span = phase1_work_commits_step()
    assert span.index("resume from increments") < span.index("Then run the gate")


def test_phase1_names_the_rung_and_missing_status_trigger():
    span = phase1_work_commits_step()
    assert "resume-from-increments rung" in span
    assert "a missing `STATUS:` block on a returned implementer" in span
    assert "escalation-and-repair.md" in span


def test_phase1_report_check_runs_only_after_status_done_or_stub():
    span = phase1_work_commits_step()
    assert (
        "runs only once a `STATUS: DONE` (or a regenerated stub) exists" in span
    )
    assert "regenerate a stub report" in span


def test_phase1_gate_path_survives_for_completion_shaped_status():
    span = phase1_work_commits_step()
    assert "Completion-shaped `STATUS:` present" in span
    assert "`git reset --hard <gate_base>`" in span
    assert "Then run the gate" in span
