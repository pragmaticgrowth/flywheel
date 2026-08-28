"""Capture-bar default + earning-token policy tests (goal 012-capture-bar-default).

Forensic grounding (goal Context, verified 2026-08-28): the v11.6.0 capture bar
in dispatch's Settle triage listed Capture before Report-only with no default
disposition named, and the inbox-line template carried no earning-condition
field — settle-time captures kept landing (field inbox at 647 lines, capture
claimed 580; measured 2026-08-13/16: ~1.5-2.5 inbox lines per completed goal
pre-bar, over half keep-grade nits at triage). The fix: Report-only is the
DEFAULT disposition, and every captured line names its earning condition (live
defect / genuinely new work / owner decision) in the line itself.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning (see test_subjective_criteria_policy).
Meaning is verified by the subagent dry-runs recorded with the goal.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DISPATCH = "skills/dispatch/SKILL.md"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrapped(path: str) -> str:
    return " ".join(read(path).split())


def settle_triage() -> str:
    """The Settle triage section, whitespace-collapsed (wrap-tolerant)."""
    text = read(DISPATCH)
    start = text.index("## Settle triage")
    end = text.index("\n## ", start)
    return " ".join(text[start:end].split())


def capture_item() -> str:
    section = settle_triage()
    start = section.index("3. **Capture**")
    end = section.index("4. **Report-only**")
    return section[start:end]


def report_only_item() -> str:
    section = settle_triage()
    start = section.index("4. **Report-only**")
    end = section.index("A goal does NOT settle")
    return section[start:end]


def inbox_template() -> str:
    item = capture_item()
    start = item.index("`- [ ]")
    end = item.index("`", start + 1)
    return item[start + 1 : end]


# ---- band 1: Report-only is the DEFAULT disposition --------------------------


def test_unsure_routes_to_report_only_adjacent_to_the_dispositions():
    section = settle_triage()
    list_intro = section.index("exactly ONE of these four dispositions")
    unsure = section.index("unsure → Report-only")
    first_item = section.index("1. **Repair now**")
    assert list_intro < unsure < first_item


def test_report_only_is_named_the_default_in_intro_and_heading():
    assert "Report-only is the DEFAULT" in settle_triage()
    assert "(the DEFAULT — unsure lands here)" in report_only_item()


def test_the_default_names_the_underbar_condition():
    assert (
        "an item that does not clearly meet one of the capture bar's three "
        "earning shapes is under the bar" in settle_triage()
    )


# ---- band 2: Capture is legal only with an earning token ----------------------


def test_capture_is_legal_only_when_the_line_carries_its_earning_token():
    assert (
        "Capture is legal ONLY when the appended line carries its earning token"
        in capture_item()
    )


def test_no_honest_shape_routes_to_report_only():
    assert (
        "If you cannot honestly name one shape, the item is not over the bar → "
        "Report-only" in capture_item()
    )


def test_an_untokened_line_is_not_a_capture():
    item = capture_item()
    assert (
        "inbox line without its earning token is a capture that did not happen"
        in item
    )
    assert "never append it" in item


# ---- band 3: the template names the earning condition in the line ------------


def test_template_requires_the_earning_token():
    assert "(earn: live-defect|new-work|owner-decision)" in inbox_template()


def test_the_token_sits_in_the_line_itself_before_the_evidence():
    template = inbox_template()
    assert template.index("(earn:") < template.index("(evidence:")


def test_the_bar_shapes_map_to_their_tokens():
    # Pairing, not mere presence: each earning token must sit adjacent to its
    # own shape's text, so a crossed mapping (a LIVE defect tagged `new-work`)
    # fails here (gate-reviewer Minor finding on the prior sitting, fixed).
    item = capture_item()
    assert "a LIVE defect (`live-defect`)" in item
    assert "NEW work (`new-work`)" in item
    assert "an OWNER decision (`owner-decision`)" in item
