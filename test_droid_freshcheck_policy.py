"""Policy tests: the implementer-side Droid lens mechanism stays REMOVED (v14.0.0).

Until v13 the implementer reviewed its own diff — on Droid via sanctioned
`droid exec` lens commands, with an honesty fallback verdict when `droid` was
absent. v14.0.0 moved the whole review to the gate: the orchestrator (a main
session on both harnesses) spawns the single gate-reviewer or the escalated
2–3-lens panel directly, so no implementer-side lens machinery may exist. These
tests guard the REMOVAL — a regression here is the old machinery leaking back.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BRIEF = ROOT / "skills" / "dispatch" / "references" / "implementer-brief.md"
DISPATCH = ROOT / "skills" / "dispatch" / "SKILL.md"
PARALLEL = ROOT / "skills" / "dispatch" / "references" / "parallel-mode.md"


def unwrapped(path: Path) -> str:
    return " ".join(path.read_text().split())


def test_brief_carries_no_droid_lens_machinery():
    text = unwrapped(BRIEF)
    assert "droid exec" not in text
    assert "Fresh-check" not in text
    assert "no fresh-context mechanism available" not in text
    assert "Harness note — nested spawning" not in text


def test_brief_forbids_self_review_and_names_the_gate_review():
    text = unwrapped(BRIEF)
    assert "Do NOT review your own finished diff in a subagent" in text
    assert (
        "the orchestrator runs the independent review over your work regardless"
        in text
    )


def test_gate_panel_replaces_the_single_reviewer_and_is_diff_sized():
    text = unwrapped(DISPATCH)
    assert "Escalate to the 2–3-lens PANEL instead of the single reviewer" in text
    assert "The panel REPLACES the single reviewer, never follows it" in text
    assert (
        "never from the implementer's claims about its own work" in text
    )


def test_parallel_lane_review_is_orchestrator_side_with_no_droid_lens_path():
    text = unwrapped(PARALLEL)
    assert "droid exec" not in text
    assert "single reviewer or the escalated lens panel, sized by the diff" in text
