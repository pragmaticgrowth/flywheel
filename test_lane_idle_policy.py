"""Parallel-mode idle-notification drain placement tests (goal 007).

Claude Code parallel-lane teammate `idle_notification` pings pile up across
continuation sessions and can open the closing turn. After this goal, the
parallel-mode report/handoff step drains or dismisses pending teammate
messages before the closing turn. Droid has no teammate surface; the
instruction is Claude-Code-only.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the
orchestrator's gate reviewer.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PARALLEL = "skills/dispatch/references/parallel-mode.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrap(text: str) -> str:
    return " ".join(text.split())


def report_handoff_step() -> str:
    """Lane-lifecycle step 6 (report/handoff/settle) up to Failure rulings."""
    text = read(PARALLEL)
    start = text.index("6. Report line")
    end = text.index("**Failure rulings", start)
    span = text[start:end]
    assert 2 <= span.count("\n") <= 20, (
        f"report/handoff step span is {span.count(chr(10))} lines"
    )
    return unwrap(span)


def test_report_handoff_consumes_or_dismisses_pending_idle_notification_before_closing_turn():
    step = report_handoff_step()
    assert "idle_notification" in step
    assert "consume or dismiss" in step
    assert "pending" in step
    assert "teammate" in step
    assert "before the closing turn" in step


def test_idle_drain_is_named_claude_code_only():
    step = report_handoff_step()
    assert "Claude-Code-only" in step


def test_idle_drain_skips_droid():
    step = report_handoff_step()
    assert "Droid has no teammate surface" in step
