"""Inbox unrunnable PRODUCTION-CHECK P-line placement tests (goal 006).

process-inbox step 3 used to send an unrunnable PRODUCTION-CHECK to "the
report's needs-you list", but step 7's hard envelope only allowed the counts
line, dispatch's line, and OWNER lines — so a compliant report could count
`<P>` and print none of the queries. After this goal, unrunnable checks print
as P-lines (query + why), `<P>` equals those lines, and the red flag matches.

SCOPE — placement guards against regression and accidental deletion only; a
text-presence test cannot verify meaning. Meaning is verified by the
orchestrator's gate reviewer.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INBOX = "skills/process-inbox/SKILL.md"

OLD_NEEDS_YOU_DESTINATION = "goes to the report's needs-you list"


def read(path: str) -> str:
    return (ROOT / path).read_text()


def unwrap(text: str) -> str:
    return " ".join(text.split())


def unwrapped(path: str) -> str:
    return unwrap(read(path))


def production_check_bullet() -> str:
    """The step-3 PRODUCTION-CHECK bucket, up to the next bucket."""
    text = read(INBOX)
    start = text.index("- **PRODUCTION-CHECK**")
    end = text.index("- **KEEP**", start)
    span = text[start:end]
    assert 2 <= span.count("\n") <= 20, (
        f"PRODUCTION-CHECK bullet span is {span.count(chr(10))} lines"
    )
    return unwrap(span)


def report_section() -> str:
    """`### 7. Report` up to `## Red flags`."""
    text = read(INBOX)
    start = text.index("### 7. Report")
    end = text.index("## Red flags", start)
    span = text[start:end]
    assert 3 <= span.count("\n") <= 40, (
        f"Report section span is {span.count(chr(10))} lines"
    )
    return unwrap(span)


def envelope_red_flag() -> str:
    """The red-flag bullet that names the hard envelope."""
    text = read(INBOX)
    start = text.index("## Red flags")
    end = text.index("## Related skills", start)
    flags = text[start:end]
    bullets = [
        unwrap(part)
        for part in flags.split("\n- ")
        if "the envelope is hard" in part
    ]
    assert len(bullets) == 1, (
        f"expected 1 envelope red-flag bullet, found {len(bullets)}"
    )
    return bullets[0]


def test_step_3_sends_unrunnable_prodchecks_to_p_lines_not_needs_you():
    bullet = production_check_bullet()
    assert "P-line" in bullet
    assert "query + why" in bullet
    assert OLD_NEEDS_YOU_DESTINATION not in bullet
    # Runnable checks still re-triage and do not print as P-lines.
    assert "re-triage" in bullet
    assert "do not print as P-lines" in bullet


def test_step_3_p_lines_are_not_owner_lines():
    bullet = production_check_bullet()
    assert "not OWNER lines" in bullet


def test_step_7_permits_p_lines_in_the_hard_envelope():
    section = report_section()
    assert "P-line" in section
    assert "query + why" in section
    # Fourth permitted component, listed with the other three.
    assert "the P-lines" in section
    assert "counts line" in section
    assert "dispatch's line" in section
    assert "OWNER item" in section


def test_p_count_equals_p_lines_printed_mirroring_o():
    section = report_section()
    assert "`<P>` must EQUAL the number of P-lines printed, mirroring `<O>`" in section
    # OWNER equality stays; P-lines mirror it, they do not replace it.
    assert "EQUAL the number of OWNER lines" in section


def test_hard_envelope_red_flag_includes_p_lines():
    flag = envelope_red_flag()
    assert "P-lines" in flag
    assert "counts line" in flag
    assert "dispatch's line" in flag
    assert "OWNER lines" in flag


def test_p_lines_are_not_owner_lines():
    text = unwrapped(INBOX)
    assert "P-lines are not OWNER lines" in text
